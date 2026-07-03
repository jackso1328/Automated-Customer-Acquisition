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

def analyze_signal_with_llm(raw_scraped_text):
    if not OPENROUTER_API_KEY:
        print("[ENGINE DEBUG] ERROR: OPENROUTER_API_KEY is completely empty or missing!")
        logging.error("Missing OpenRouter API Key in environment.")
        return None

    # ENHANCED PROMPT: We are now teaching the AI the hidden financial logic behind the news
    system_prompt = (
        "You are an expert corporate banking lead evaluator for State Bank of India (SBI).\n"
        "Your job is to read news headlines or text and find hidden financial opportunities.\n\n"
        "CRITICAL LOGIC RULES (PREVENT HALLUCINATIONS):\n"
        "- If a B2B company or Fintech (like Skydo or Razorpay) is expanding, they need Corporate/SME loans, NOT Education Loans.\n"
        "- If an EdTech startup is raising funds, the STARTUP needs Corporate funding, the students do not.\n"
        "- Only recommend Education Loans if the article is about admissions, counselling, exam merit lists, or students directly needing funds.\n\n"
        "Respond ONLY with a valid JSON object matching this exact schema layout. Do not include markdown wraps or trailing commentary:\n"
        "{\n"
        '  "company_or_entity": "Name of the entity",\n'
        '  "entity_type": "Classify as: B2B Corporation, EdTech Startup, Government, or Retail/Student",\n'
        '  "who_needs_funding": "Who actually requires the capital in this specific news event?",\n'
        '  "detected_signal": "A short 1-sentence summary of the news or event that triggered this opportunity",\n'
        '  "sbi_product_fit": "The exact SBI product they need based strictly on the entity_type",\n'
        '  "score_scale": "An integer from 0 to 10 rating the scale/reach of the opportunity",\n'
        '  "score_urgency": "An integer from 0 to 10 rating how soon they need the money",\n'
        '  "score_revenue": "An integer from 0 to 10 rating the loan size or revenue potential",\n'
        '  "score_sbi_advantage": "An integer from 0 to 10 rating how strong SBI\'s product is for this",\n'
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
                    
                    # Deterministic Match Score Calculation
                    try:
                        scale = int(str(parsed_data.get("score_scale", 0)).replace('/10','').strip())
                        urgency = int(str(parsed_data.get("score_urgency", 0)).replace('/10','').strip())
                        revenue = int(str(parsed_data.get("score_revenue", 0)).replace('/10','').strip())
                        advantage = int(str(parsed_data.get("score_sbi_advantage", 0)).replace('/10','').strip())
                        
                        confidence = (scale + urgency + revenue + advantage) / 40.0
                        parsed_data["confidence_score"] = round(confidence, 2)
                        parsed_data["score_scale"] = scale
                        parsed_data["score_urgency"] = urgency
                        parsed_data["score_revenue"] = revenue
                        parsed_data["score_sbi_advantage"] = advantage
                    except ValueError as ve:
                        print(f"[ENGINE DEBUG] Math error formatting score: {ve}. Defaulting score.")
                        parsed_data["confidence_score"] = 0.50
                        
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
