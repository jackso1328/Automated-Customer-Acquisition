"""
llm_client.py — Centralized OpenRouter API Client

Single point of contact for all LLM communication. This avoids
duplicating retry logic, header construction, JSON extraction,
and error handling across engine.py and ad_generator.py.
"""

import os
import json
import re
import time
import requests
import logging
from dotenv import load_dotenv

# Resolve .env relative to the project root (SCOUT_AGENT/), not the CWD.
# This prevents breakage when server.py changes the working directory.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "openrouter/free"

MAX_RETRIES = 3
BASE_DELAY = 2  # seconds, doubles each retry (exponential backoff)


def llm_request(system_prompt, user_message, caller="LLM"):
    """
    Sends a structured prompt to the OpenRouter API and returns parsed JSON.
    
    Args:
        system_prompt: The system-level instruction for the LLM.
        user_message:  The user-level content (scraped text, opportunity data, etc.)
        caller:        Label for log messages (e.g., "Engine", "AdGenerator").
    
    Returns:
        A parsed dict if the LLM returns valid JSON, otherwise None.
    """
    if not OPENROUTER_API_KEY:
        logging.error(f"[{caller}] OPENROUTER_API_KEY is missing from environment.")
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                OPENROUTER_URL, headers=headers, json=payload,
                timeout=(5, 30)  # 5s connect, 30s read
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                return _extract_json(content, caller)

            if response.status_code == 429:
                logging.warning(f"[{caller}] Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). Backing off...")
            else:
                logging.error(f"[{caller}] API returned {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.Timeout:
            logging.warning(f"[{caller}] Request timed out (attempt {attempt + 1}/{MAX_RETRIES}).")
        except json.JSONDecodeError:
            logging.error(f"[{caller}] Failed to parse JSON from LLM response.")
            return None
        except Exception as e:
            logging.error(f"[{caller}] Unexpected error: {e}")
            return None

        # Exponential backoff before next retry
        if attempt < MAX_RETRIES - 1:
            time.sleep(BASE_DELAY * (2 ** attempt))

    logging.error(f"[{caller}] All {MAX_RETRIES} retries exhausted.")
    return None


def _extract_json(text, caller):
    """
    Extracts and parses the first JSON object found in an LLM response.
    Handles common LLM formatting issues like markdown code fences.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        logging.warning(f"[{caller}] No JSON object found in LLM output.")
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        logging.error(f"[{caller}] Extracted text is not valid JSON.")
        return None
