import os
import json
import requests
import logging
from dotenv import load_dotenv

# Load key from .env file
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Using a popular, highly-capable free tier model on OpenRouter
MODEL_NAME = "meta-llama/llama-3-8b-instruct:free"

def analyze_signal_with_llm(raw_scraped_text):
    """
    Sends raw web text data to OpenRouter to parse, evaluate, 
    and output a strictly formatted banking product match.
    """
    if not OPENROUTER_API_KEY:
        logging.error("Missing OpenRouter API Key in environment.")
        return None

    # Strict system prompt ensuring clean JSON outputs without text summaries or explanations
    system_prompt = (
        "You are an expert corporate banking lead evaluator for State Bank of India (SBI).\n"
        "Analyze the provided text snippet and determine if there is a realistic business opportunity to offer a banking product.\n"
        "Respond ONLY with a valid JSON object matching this exact schema layout. Do not include markdown wraps or trailing commentary:\n"
        "{\n"
        '  "company_or_entity": "Exact name of the company or institution",\n'
        '  "detected_signal": "Brief summary of what they are doing (e.g., expanding, winning a tender)",\n'
        '  "sbi_product_fit": "The exact SBI product they need (e.g., Project Finance, KCC, Letter of Credit, Salary Accounts)",\n'
        '  "confidence_score": 0.00 to 1.00,\n'
        '  "justification": "Why this specific business requires this specific financial product"\n'
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
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            response_json = response.json()
            content_text = response_json['choices'][0]['message']['content'].strip()
            
            # Parse the text string directly back into a python dictionary
            parsed_data = json.loads(content_text)
            return parsed_data
        else:
            logging.error(f"OpenRouter API returned an error status: {response.status_code} - {response.text}")
            return None
    except json.JSONDecodeError:
        logging.error("Failed to parse raw model response string into structural JSON format.")
        return None
    except Exception as e:
        logging.error(f"Exception during LLM analysis execution: {str(e)}")
        return None
