import os
import json
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
        "CRITICAL BUSINESS RULES:\n"
        "- If the text mentions 'merit list', 'counselling', 'admission', or 'exam results', this means students urgently need funds to secure college seats. YOU MUST SCORE THIS >= 0.85 and recommend 'SBI Education Loan' or 'SBI Scholar Loan'.\n"
        "- If the text mentions 'visa', 'studying abroad', or 'foreign universities', students need international funding. YOU MUST SCORE THIS >= 0.90 and recommend 'SBI Global Ed-Vantage Scheme'.\n\n"
        "- If a company wins a 'government tender' or 'contract', they immediately need financial backing. YOU MUST SCORE THIS >= 0.90 and recommend 'SBI Bank Guarantee' or 'Project Finance'.\n"
        "- If a company announces a 'plant expansion', 'new factory', or 'data center', they need capital. YOU MUST SCORE THIS >= 0.85 and recommend 'SBI Corporate Term Loan'.\n"
        "Respond ONLY with a valid JSON object matching this exact schema layout. Do not include markdown wraps or trailing commentary:\n"
        "{\n"
        '  "company_or_entity": "Name of the exam, board, or institution",\n'
        '  "detected_signal": "Brief summary of what they are doing",\n'
        '  "sbi_product_fit": "The exact SBI product they need",\n'
        '  "confidence_score": 0.00 to 1.00,\n'
        '  "justification": "Why this specific situation requires this specific financial product"\n'
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

    try:
        print(f"[ENGINE DEBUG] Connecting to OpenRouter Auto-Router...")
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=(5, 15))
        
        print(f"[ENGINE DEBUG] Received Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            content_text = response_json['choices'][0]['message']['content'].strip()
            
            if content_text.startswith("```json"):
                content_text = content_text.replace("```json", "").replace("```", "").strip()
            elif content_text.startswith("```"):
                content_text = content_text.replace("```", "").strip()
                
            parsed_data = json.loads(content_text)
            return parsed_data
        else:
            print(f"[ENGINE DEBUG] API Error Content: {response.text}")
            logging.error(f"OpenRouter API returned an error status: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("[ENGINE DEBUG] Request timed out globally.")
        return None
    except json.JSONDecodeError as je:
        print(f"[ENGINE DEBUG] JSON Parsing Failed. Raw text was: {content_text}")
        return None
    except Exception as e:
        print(f"[ENGINE DEBUG] Fatal local exception thrown: {str(e)}")
        return None
