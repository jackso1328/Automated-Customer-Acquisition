import os
import json
import time
import re
import requests
import urllib.parse
import logging
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openrouter/free"

def generate_campaign_assets(opportunity):
    """
    Takes an opportunity dictionary, generates personalized Ad Copy and an Image Prompt 
    using the LLM, and creates a live image generation URL using Pollinations.ai.
    """
    if not OPENROUTER_API_KEY:
        logging.error("Missing OpenRouter API Key in environment.")
        return None

    opportunity_str = json.dumps(opportunity, indent=2)

    system_prompt = (
        "You are an expert marketing copywriter for State Bank of India (SBI).\n"
        "Your job is to generate a highly personalized, empathetic ad campaign based on a discovered opportunity.\n\n"
        "RULES:\n"
        "1. Write the Ad Copy in the most appropriate language for the target (e.g., Hindi for UP/Bihar, Marathi for Maharashtra, English for Corporates).\n"
        "2. Focus on building trust. Never sound demanding or corporate-dry.\n"
        "3. The image prompt MUST be in English and describe a photorealistic, emotional scene.\n"
        "4. You must select the single best digital advertising platform to distribute this ad on.\n\n"
        "Respond ONLY with a valid JSON object matching this exact schema. Do not include markdown wraps or trailing commentary:\n"
        "{\n"
        '  "target_language": "The best language for this target (e.g. Hindi, English, Tamil)",\n'
        '  "customer_persona": "A brief 2-sentence description of who we are targeting and their current emotional state",\n'
        '  "headline": "A catchy, empathetic headline in the target_language. Keep it under 10 words.",\n'
        '  "body_copy": "3-4 bullet points in the target_language highlighting how the SBI product solves their immediate need.",\n'
        '  "call_to_action": "A clear, low-friction CTA (e.g. \'Check Eligibility in 2 Mins\')",\n'
        '  "image_prompt": "A detailed, English-language prompt for an AI image generator. Describe a photorealistic scene. Must include \'SBI blue color palette\' and \'photorealistic ad style\'. Keep under 50 words.",\n'
        '  "recommended_distributor": "The single best platform to show this ad (e.g., \'Google Search Ads\', \'Instagram Feed\', \'LinkedIn Ads\', \'YouTube Pre-roll\')",\n'
        '  "distributor_reasoning": "A 1-sentence explanation of why this platform is best for this specific target audience."\n'
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
            {"role": "user", "content": f"Generate a campaign for this opportunity:\n\n{opportunity_str}"}
        ]
    }

    logging.info(f"Generating campaign assets for: {opportunity.get('company_or_entity')}")

    max_retries = 3
    base_delay = 2

    for attempt in range(max_retries):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=(5, 15))
            
            if response.status_code == 200:
                response_json = response.json()
                content_text = response_json['choices'][0]['message']['content'].strip()
                
                # Robust JSON extraction
                match = re.search(r'\{.*\}', content_text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    parsed_data = json.loads(json_str)
                    
                    # Generate the Pollinations.ai image URL
                    image_prompt = parsed_data.get("image_prompt", "")
                    if image_prompt:
                        encoded_prompt = urllib.parse.quote(image_prompt)
                        # We use pollinations.ai for free, instant image generation
                        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=512&nologo=true"
                        parsed_data["generated_image_url"] = image_url
                    
                    logging.info("Successfully generated campaign assets.")
                    return parsed_data
                else:
                    logging.error(f"Could not find JSON in response: {content_text}")
                    return None
            elif response.status_code == 429:
                logging.warning("Rate limited by OpenRouter. Retrying...")
            else:
                logging.error(f"API Error Content: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logging.warning("Request timed out.")
        except json.JSONDecodeError as je:
            logging.error(f"JSON Parsing Failed.")
            return None
        except Exception as e:
            logging.error(f"Fatal error: {str(e)}")
            return None
            
        if attempt < max_retries - 1:
            time.sleep(base_delay * (2 ** attempt))

    return None
