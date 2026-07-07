"""
ad_generator.py — Campaign Asset Generator

Takes a scored financial opportunity and generates:
  1. Personalized ad copy (headline, body, CTA) in the target language.
  2. A photorealistic image prompt for AI image generation.
  3. A recommended distribution platform with strategic reasoning.
  4. A live Pollinations.ai URL for instant visual preview.
"""

import urllib.parse
import logging
from src.llm_client import llm_request

CAMPAIGN_SYSTEM_PROMPT = (
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

# Pollinations.ai image dimensions for ad-format output
IMAGE_WIDTH = 1024
IMAGE_HEIGHT = 512


def generate_campaign_assets(opportunity):
    """
    Takes an opportunity dictionary and returns a complete campaign asset
    package (ad copy + image URL + distributor recommendation).
    """
    import json
    opportunity_str = json.dumps(opportunity, indent=2)

    parsed_data = llm_request(
        system_prompt=CAMPAIGN_SYSTEM_PROMPT,
        user_message=f"Generate a campaign for this opportunity:\n\n{opportunity_str}",
        caller="AdGenerator"
    )

    if not parsed_data:
        return None

    # Generate the Pollinations.ai image URL for instant visual preview
    image_prompt = parsed_data.get("image_prompt", "")
    if image_prompt:
        encoded_prompt = urllib.parse.quote(image_prompt)
        parsed_data["generated_image_url"] = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}&nologo=true"
        )

    logging.info(f"Successfully generated campaign for: {opportunity.get('company_or_entity')}")
    return parsed_data
