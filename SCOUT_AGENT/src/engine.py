import os
import json
import time
import re
import requests
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# The ultimate hackathon safety net. Automatically routes to the fastest, un-congested free model.
MODEL_NAME = "openrouter/free"

# ──────────────────────────────────────────────────────────────
# Weighted Scoring Configuration
# These weights reflect real banking business priorities:
#   Revenue matters most  — a bank's core purpose is lending capital.
#   SBI Advantage is the qualifier — no point chasing leads you can't serve.
#   Urgency drives conversion — time-sensitive leads close faster.
#   Scale is context — useful but least decisive on its own.
# ──────────────────────────────────────────────────────────────
DIMENSION_WEIGHTS = {
    "score_scale":         0.15,
    "score_urgency":       0.25,
    "score_revenue":       0.35,
    "score_sbi_advantage": 0.25,
}

# If ANY single dimension falls at or below this threshold,
# the entire score is penalized — a critical weakness in one area
# means the lead is fundamentally risky regardless of other strengths.
WEAKNESS_THRESHOLD = 2
WEAKNESS_PENALTY   = 0.60  # Multiplier: drops score by 40%

# Priority tier boundaries (applied to the final 0–100 score)
TIER_THRESHOLDS = [
    (85, "P1"),   # 85-100: Immediate action
    (70, "P2"),   # 70-84:  High priority
    (50, "P3"),   # 50-69:  Monitor
    (0,  "P4"),   # 0-49:   Archive
]


def _sanitize_score(raw_value, field_name):
    """
    Converts an LLM-provided score into a clean integer 0–10.
    Handles edge cases: "8/10", "7.5", "eight", trailing text, etc.
    """
    s = str(raw_value).strip()
    
    # Strip common LLM formatting artifacts
    s = s.replace('/10', '').replace(' out of 10', '').strip()
    
    # Try direct integer parse
    try:
        val = int(s)
        return max(0, min(10, val))
    except ValueError:
        pass
    
    # Try float parse (LLM might say "7.5")
    try:
        val = int(round(float(s)))
        return max(0, min(10, val))
    except ValueError:
        pass
    
    # Try to extract first number from messy text like "8 (high)"
    match = re.search(r'(\d+)', s)
    if match:
        val = int(match.group(1))
        return max(0, min(10, val))
    
    logging.warning(f"[SCORING] Could not parse '{raw_value}' for {field_name}. Defaulting to 5.")
    return 5


def calculate_match_score(parsed_data):
    """
    The Deterministic Match Scoring Algorithm.
    
    Architecture:
        1. Extract and sanitize 4 dimension scores from LLM output.
        2. Compute a weighted sum (not a naive average).
        3. Apply a penalty multiplier if any dimension is critically weak.
        4. Assign a human-readable Priority Tier (P1–P4).
    
    The formula:
        weighted_raw = Σ (dimension_score × dimension_weight)
        base_score   = weighted_raw / 10.0   (normalize to 0.0–1.0)
        penalty      = 0.60 if min(all_dimensions) ≤ 2, else 1.0
        final_score  = base_score × penalty
    """
    # Step 1: Extract and sanitize each dimension
    scale     = _sanitize_score(parsed_data.get("score_scale", 5), "score_scale")
    urgency   = _sanitize_score(parsed_data.get("score_urgency", 5), "score_urgency")
    revenue   = _sanitize_score(parsed_data.get("score_revenue", 5), "score_revenue")
    advantage = _sanitize_score(parsed_data.get("score_sbi_advantage", 5), "score_sbi_advantage")
    
    # Step 2: Weighted sum
    weighted_raw = (
        scale     * DIMENSION_WEIGHTS["score_scale"] +
        urgency   * DIMENSION_WEIGHTS["score_urgency"] +
        revenue   * DIMENSION_WEIGHTS["score_revenue"] +
        advantage * DIMENSION_WEIGHTS["score_sbi_advantage"]
    )
    base_score = weighted_raw / 10.0  # Normalize: max weighted_raw is 10.0
    
    # Step 3: Penalty for critical weakness
    min_dimension = min(scale, urgency, revenue, advantage)
    penalty = WEAKNESS_PENALTY if min_dimension <= WEAKNESS_THRESHOLD else 1.0
    
    final_score = round(base_score * penalty, 2)
    final_score = max(0.0, min(1.0, final_score))  # Clamp to [0, 1]
    
    # Step 4: Priority tier assignment
    percentage = int(final_score * 100)
    priority_tier = "P4"
    for threshold, tier in TIER_THRESHOLDS:
        if percentage >= threshold:
            priority_tier = tier
            break
    
    # Write back clean values
    parsed_data["score_scale"] = scale
    parsed_data["score_urgency"] = urgency
    parsed_data["score_revenue"] = revenue
    parsed_data["score_sbi_advantage"] = advantage
    parsed_data["confidence_score"] = final_score
    parsed_data["priority_tier"] = priority_tier
    parsed_data["penalty_applied"] = (penalty < 1.0)
    
    logging.info(
        f"[SCORING] Scale:{scale} Urg:{urgency} Rev:{revenue} Adv:{advantage} "
        f"| Weighted:{weighted_raw:.2f} Penalty:{'YES' if penalty < 1.0 else 'NO'} "
        f"| Final:{percentage}% Tier:{priority_tier}"
    )
    
    return parsed_data


def analyze_signal_with_llm(raw_scraped_text):
    if not OPENROUTER_API_KEY:
        print("[ENGINE DEBUG] ERROR: OPENROUTER_API_KEY is completely empty or missing!")
        logging.error("Missing OpenRouter API Key in environment.")
        return None

    # ──────────────────────────────────────────────────────────
    # ANCHORED RUBRIC PROMPT
    # Each dimension has concrete definitions so the LLM produces
    # consistent, repeatable scores — not hallucinated guesses.
    # ──────────────────────────────────────────────────────────
    system_prompt = (
        "You are an expert corporate banking lead evaluator for State Bank of India (SBI).\n"
        "Your job is to read news headlines or text and find hidden financial opportunities.\n\n"
        "CRITICAL LOGIC RULES (PREVENT HALLUCINATIONS):\n"
        "- If a B2B company or Fintech (like Skydo or Razorpay) is expanding, they need Corporate/SME loans, NOT Education Loans.\n"
        "- If an EdTech startup is raising funds, the STARTUP needs Corporate funding, the students do not.\n"
        "- Only recommend Education Loans if the article is about admissions, counselling, exam merit lists, or students directly needing funds.\n\n"
        "SCORING RUBRIC — use these anchors strictly, do NOT guess:\n\n"
        "score_scale (How many people/entities are affected?):\n"
        "  1-2: Hyper-local (single company, <100 people)\n"
        "  3-4: City-level (one city, hundreds of people)\n"
        "  5-6: State-level (one state, thousands)\n"
        "  7-8: Multi-state or sector-wide (lakhs of people)\n"
        "  9-10: National event (JEE/NEET results, Union Budget, nationwide scheme)\n\n"
        "score_urgency (How soon do they need the money?):\n"
        "  1-2: No deadline, general trend or speculation\n"
        "  3-4: Within 6 months\n"
        "  5-6: Within 2-3 months\n"
        "  7-8: Within 30-45 days (fee deadlines, enrollment windows)\n"
        "  9-10: Within 7-14 days or already overdue\n\n"
        "score_revenue (What is the loan/account value PER lead?):\n"
        "  1-2: Micro (<Rs.50K per account — street vendor, zero balance)\n"
        "  3-4: Small (Rs.50K-Rs.5L — personal loan, KCC)\n"
        "  5-6: Medium (Rs.5L-Rs.25L — education loan, auto loan)\n"
        "  7-8: Large (Rs.25L-Rs.5Cr — home loan, SME term loan)\n"
        "  9-10: Mega (Rs.5Cr+ — corporate project finance, infrastructure)\n\n"
        "score_sbi_advantage (Does SBI have a strong product for this?):\n"
        "  1-2: SBI has no relevant product or is at a disadvantage\n"
        "  3-4: SBI has a generic product, competitors are equally strong\n"
        "  5-6: SBI has a good product with moderate differentiation\n"
        "  7-8: SBI has a well-known, competitive product (Scholar Loan, KCC, YONO)\n"
        "  9-10: SBI is the designated/nodal bank or has a monopoly advantage\n\n"
        "Respond ONLY with a valid JSON object matching this exact schema. Do not include markdown wraps or trailing commentary:\n"
        "{\n"
        '  "company_or_entity": "Name of the entity",\n'
        '  "entity_type": "Classify as: B2B Corporation, EdTech Startup, Government, or Retail/Student",\n'
        '  "who_needs_funding": "Who actually requires the capital in this specific news event?",\n'
        '  "detected_signal": "A short 1-sentence summary of the news or event that triggered this opportunity",\n'
        '  "sbi_product_fit": "The exact SBI product they need based strictly on the entity_type",\n'
        '  "score_scale": integer 0-10,\n'
        '  "score_urgency": integer 0-10,\n'
        '  "score_revenue": integer 0-10,\n'
        '  "score_sbi_advantage": integer 0-10,\n'
        '  "justification": "Why this product fits the entity type"\n'
        "}"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this text data:\n\n{raw_scraped_text}"}
        ]
    }

    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        try:
            print(f"[ENGINE DEBUG] Connecting to OpenRouter Auto-Router... (Attempt {attempt + 1}/{max_retries})")
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=(5, 15))
            
            print(f"[ENGINE DEBUG] Received Response Status Code: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                content_text = response_json['choices'][0]['message']['content'].strip()
                
                # Robust JSON extraction
                match = re.search(r'\{.*\}', content_text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    parsed_data = json.loads(json_str)
                    
                    # Run the deterministic scoring algorithm
                    parsed_data = calculate_match_score(parsed_data)
                    
                    return parsed_data
                else:
                    print(f"[ENGINE DEBUG] Could not find JSON in response: {content_text}")
                    return None
            elif response.status_code == 429:
                print(f"[ENGINE DEBUG] Rate limited. Retrying...")
            else:
                print(f"[ENGINE DEBUG] API Error Content: {response.text}")
                logging.error(f"OpenRouter API returned an error status: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print("[ENGINE DEBUG] Request timed out globally.")
        except json.JSONDecodeError as je:
            print(f"[ENGINE DEBUG] JSON Parsing Failed. Raw text was: {content_text}")
            return None
        except Exception as e:
            print(f"[ENGINE DEBUG] Fatal local exception thrown: {str(e)}")
            return None
            
        # Exponential backoff
        if attempt < max_retries - 1:
            time.sleep(base_delay * (2 ** attempt))

    print("[ENGINE DEBUG] Max retries reached. Failing gracefully.")
    return None

