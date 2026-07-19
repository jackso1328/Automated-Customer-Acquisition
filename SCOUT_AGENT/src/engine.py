"""
engine.py — Core Intelligence Engine

Handles two responsibilities:
  1. Sending scraped signals to the LLM for structured financial analysis.
  2. Running the Deterministic Match Scoring Algorithm on the LLM output.

The scoring algorithm uses weighted dimensions, penalty-aware logic,
and priority tiering to produce consistent, repeatable lead scores.
"""

import os
import json
import re
import logging
from src.llm_client import llm_request

# ──────────────────────────────────────────────────────────────
# Weighted Scoring Configuration (Next-Gen)
# Rebalanced to prioritize Lifetime Value (LTV) and Propensity
# alongside traditional revenue metrics.
# ──────────────────────────────────────────────────────────────
DIMENSION_WEIGHTS = {
    "score_scale":         0.10,
    "score_urgency":       0.15,
    "score_revenue":       0.20,
    "score_sbi_advantage": 0.15,
    "score_ltv":           0.20,
    "score_propensity":    0.20,
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

# ──────────────────────────────────────────────────────────────
# ANCHORED RUBRIC PROMPT
# Each dimension has concrete definitions so the LLM produces
# consistent, repeatable scores — not hallucinated guesses.
# ──────────────────────────────────────────────────────────────
ANALYSIS_SYSTEM_PROMPT = """You are an expert corporate banking lead evaluator and Risk/Compliance Officer for State Bank of India (SBI).
Your job is to read news headlines or text and find hidden financial opportunities while strictly enforcing KYC/AML rules.

CRITICAL LOGIC RULES (PREVENT HALLUCINATIONS):
- If a B2B company or Fintech is expanding, they need Corporate/SME loans, NOT Education Loans.
- If an EdTech startup is raising funds, the STARTUP needs Corporate funding, the students do not.
- Only recommend Education Loans if the article is about admissions, counselling, exam merit lists, or students directly needing funds.

SCORING RUBRIC — use these anchors strictly, do NOT guess:

score_scale (How many people/entities are affected?):
  1-2: Hyper-local (single company, <100 people)
  9-10: National event (JEE/NEET results, Union Budget, nationwide scheme)

score_urgency (How soon do they need the money?):
  1-2: No deadline, general trend or speculation
  9-10: Within 7-14 days or already overdue

score_revenue (What is the loan/account value PER lead?):
  1-2: Micro (<Rs.50K per account)
  9-10: Mega (Rs.5Cr+)

score_sbi_advantage (Does SBI have a strong product for this?):
  1-2: SBI has no relevant product or is at a disadvantage
  9-10: SBI is the designated/nodal bank or has a monopoly advantage

score_ltv (Predictive Lifetime Value trajectory):
  1-2: Very low future needs (e.g. one-off micro loans, bankruptcy)
  9-10: High exponential lifetime value

score_propensity (Likelihood to convert digitally/immediately):
  1-2: Vague curiosity, locked by competitor, or regulatory block
  9-10: Urgent and specific need, highly likely to convert autonomously

Output valid JSON matching this schema:
{
    "company_or_entity": "Name of the target company/entity as written in the text",
    "normalized_company_name": "Standardized canonical name (e.g. map 'RIL' and 'Jio' to 'Reliance Industries', 'TCS' to 'Tata Consultancy Services')",
    "is_existing_client": boolean (true ONLY if the text explicitly mentions they bank with SBI),
    "detected_signal": "1-2 sentences summarizing why they need banking services right now",
    "sbi_product_fit": "e.g., Corporate Term Loan, Working Capital, Forex Services",
    "score_scale": 1-10,
    "score_urgency": 1-10,
    "score_revenue": 1-10,
    "score_sbi_advantage": 1-10,
    "score_ltv": 1-10,
    "score_propensity": 1-10,
    "compliance_risk_flag": boolean (true ONLY if there are fraud, money laundering, bankruptcy, or regulatory bans),
    "xai_reasoning": "1-2 sentences mathematically justifying the LTV and Propensity scores"
}
"""


def _sanitize_score(raw_value, field_name):
    """
    Converts an LLM-provided score into a clean integer 0–10.
    Handles edge cases: "8/10", "7.5", "eight", trailing text, etc.
    """
    s = str(raw_value).strip().replace('/10', '').replace(' out of 10', '').strip()
    
    # Try direct integer, then float, then regex extraction
    for parser in [int, lambda x: int(round(float(x)))]:
        try:
            return max(0, min(10, parser(s)))
        except (ValueError, TypeError):
            continue
    
    match = re.search(r'(\d+)', s)
    if match:
        return max(0, min(10, int(match.group(1))))
    
    logging.warning(f"[SCORING] Could not parse '{raw_value}' for {field_name}. Defaulting to 5.")
    return 5


def calculate_match_score(parsed_data, trust_score=1.0):
    """
    The Deterministic Match Scoring Algorithm.
    
    Architecture:
        1. Extract and sanitize 4 dimension scores from LLM output.
        2. Compute a weighted sum (not a naive average).
        3. Apply a penalty multiplier if any dimension is critically weak.
        4. Apply a Veracity Penalty if the trust_score (source credibility) is low.
        5. Assign a human-readable Priority Tier (P1–P4).
    """
    dimensions = {
        key: _sanitize_score(parsed_data.get(key, 5), key) 
        for key in DIMENSION_WEIGHTS
    }
    
    # Weighted sum → normalize to 0.0–1.0
    weighted_raw = sum(dimensions[k] * w for k, w in DIMENSION_WEIGHTS.items())
    base_score = weighted_raw / 10.0
    
    # Penalty for critical weakness
    min_dimension = min(dimensions.values())
    penalty = WEAKNESS_PENALTY if min_dimension <= WEAKNESS_THRESHOLD else 1.0
    
    # Veracity penalty
    veracity_penalty = 1.0 if trust_score >= 0.5 else 0.5
    
    final_score = round(max(0.0, min(1.0, base_score * penalty * veracity_penalty)), 2)
    
    # Priority tier assignment
    percentage = int(final_score * 100)
    priority_tier = next(
        (tier for threshold, tier in TIER_THRESHOLDS if percentage >= threshold),
        "P4"
    )
    
    # ── RISK & COMPLIANCE HARD OVERRIDE ──
    if parsed_data.get("compliance_risk_flag", False):
        final_score = 0.0
        percentage = 0
        priority_tier = "P4"
        parsed_data["score_propensity"] = 1  # Force propensity low so it sinks in sorting
    
    # Write back clean values
    parsed_data.update(dimensions)
    parsed_data["confidence_score"] = final_score
    parsed_data["priority_tier"] = priority_tier
    parsed_data["penalty_applied"] = (penalty < 1.0)
    parsed_data["veracity_score"] = int(trust_score * 100)
    
    logging.info(
        f"[SCORING] Scale:{dimensions['score_scale']} Urg:{dimensions['score_urgency']} "
        f"Rev:{dimensions['score_revenue']} Adv:{dimensions['score_sbi_advantage']} "
        f"| Veracity:{parsed_data['veracity_score']} "
        f"| Final:{percentage}% Tier:{priority_tier}"
    )
    
    return parsed_data


def analyze_signal_with_llm(raw_scraped_text, trust_score=1.0):
    """
    Sends raw scraped text to the LLM for structured financial analysis,
    then runs the deterministic scoring algorithm on the result.
    """
    parsed_data = llm_request(
        system_prompt=ANALYSIS_SYSTEM_PROMPT,
        user_message=f"Analyze this text data:\n\n{raw_scraped_text}",
        caller="Engine"
    )
    
    if parsed_data:
        return calculate_match_score(parsed_data, trust_score)
    return None
