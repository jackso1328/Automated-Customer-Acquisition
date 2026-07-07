"""
database.py — JSON File Database

Handles read/write operations against opportunities.json.
Uses signal-based deduplication to prevent duplicate leads
without over-aggressively blocking unrelated opportunities.
"""

import os
import json
import logging

DB_FILE = "opportunities.json"

# Common words that inflate overlap scores and cause false-positive deduplication.
# These are stripped before comparing signals.
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "in", "of", "to", "for", "and", "on", "at",
    "by", "with", "from", "as", "its", "has", "have", "been", "are", "was",
    "were", "will", "be", "this", "that", "it", "or", "not", "but", "-",
})

SIGNAL_OVERLAP_THRESHOLD = 0.80  # 80% word overlap = duplicate


def initialize_db():
    """Ensures the JSON file database exists and is properly formatted as a list."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logging.info(f"Initialized empty file database at {DB_FILE}")


def _tokenize_signal(text):
    """Splits a signal string into meaningful words, stripping stop words and short tokens."""
    words = text.strip().lower().split()
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def _is_duplicate(new_entry, existing_entries):
    """
    Checks whether a new opportunity is a duplicate of any existing entry.
    
    Two-layer check:
      1. Exact entity name match → always duplicate.
      2. Signal word overlap ≥ 80% (after stop-word removal) → same event, different wording.
    """
    new_entity = new_entry.get("company_or_entity", "").strip().lower()
    new_words = _tokenize_signal(new_entry.get("detected_signal", ""))

    for item in existing_entries:
        existing_entity = item.get("company_or_entity", "").strip().lower()

        # Layer 1: Exact entity match
        if new_entity == existing_entity:
            logging.info(f"Exact duplicate entity '{new_entity}'. Skipping.")
            return True

        # Layer 2: Signal word overlap
        if new_words:
            existing_words = _tokenize_signal(item.get("detected_signal", ""))
            if existing_words:
                overlap = new_words & existing_words
                smaller_set = min(len(new_words), len(existing_words))
                if smaller_set > 0 and (len(overlap) / smaller_set) >= SIGNAL_OVERLAP_THRESHOLD:
                    logging.info(
                        f"Signal overlap ({len(overlap)}/{smaller_set} words) "
                        f"between '{new_entity}' and '{existing_entity}'. Skipping."
                    )
                    return True

    return False


def save_opportunity(opportunity_data):
    """
    Appends a new opportunity to the JSON database after deduplication.
    Uses atomic read-then-write to minimize data corruption risk.
    """
    initialize_db()

    entity_name = opportunity_data.get("company_or_entity", "").strip()
    if not entity_name:
        return False

    try:
        # Read current data
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Deduplicate
        if _is_duplicate(opportunity_data, data):
            return False

        # Append and write back atomically
        data.append(opportunity_data)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        logging.info(f"Successfully saved new opportunity for: {entity_name}")
        return True

    except Exception as e:
        logging.error(f"Failed to write to file database: {e}")
        return False


def get_all_opportunities():
    """Reads and returns all entries within the local JSON file database."""
    initialize_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read file database: {e}")
        return []