import os
import json
import logging

DB_FILE = "opportunities.json"

def initialize_db():
    """Ensures the JSON file database exists and is properly formatted as a list."""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logging.info(f"Initialized empty file database at {DB_FILE}")

def save_opportunity(opportunity_data):
    """
    Appends a new discovered corporate opportunity into the JSON file.
    Deduplicates by comparing the detected_signal text — if 80%+ of
    the words overlap with an existing entry, it's considered a duplicate.
    This avoids the old problem where generic entity names like 'Indian Students'
    would block completely different leads.
    """
    initialize_db()
    
    try:
        with open(DB_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            
            # Extract comparison fields
            new_signal = opportunity_data.get("detected_signal", "").strip().lower()
            new_entity = opportunity_data.get("company_or_entity", "").strip().lower()
            if not new_entity:
                return False
            
            # Check for duplicates using signal word overlap
            new_words = set(new_signal.split())
            
            for item in data:
                existing_entity = item.get("company_or_entity", "").strip().lower()
                existing_signal = item.get("detected_signal", "").strip().lower()
                
                # Exact entity match — always a duplicate
                if new_entity == existing_entity:
                    logging.info(f"Exact duplicate entity '{opportunity_data.get('company_or_entity')}'. Skipping.")
                    return False
                
                # Signal word overlap check — if 80%+ words match, it's the same event
                if new_words and existing_signal:
                    existing_words = set(existing_signal.split())
                    overlap = new_words & existing_words
                    smaller_set = min(len(new_words), len(existing_words))
                    if smaller_set > 0 and (len(overlap) / smaller_set) >= 0.80:
                        logging.info(f"Signal overlap detected for '{opportunity_data.get('company_or_entity')}' vs '{item.get('company_or_entity')}'. Skipping.")
                        return False
            
            data.append(opportunity_data)
            
            # Rewind file pointer to overwrite cleanly
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
            
            logging.info(f"Successfully saved new opportunity for: {opportunity_data.get('company_or_entity')}")
            return True
    except Exception as e:
        logging.error(f"Failed to write to file database: {str(e)}")
        return False

def get_all_opportunities():
    """Reads and returns all entries within our local JSON file database."""
    initialize_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to read file database: {str(e)}")
        return []