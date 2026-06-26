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
    Prevents duplicate entries based on the company name.
    """
    initialize_db()
    
    try:
        with open(DB_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            
            # Simple deduplication check
            company_name = opportunity_data.get("company_or_entity", "").strip().lower()
            duplicate_exists = any(item.get("company_or_entity", "").strip().lower() == company_name for item in data)
            
            if duplicate_exists:
                logging.info(f"Opportunity for '{opportunity_data.get('company_or_entity')}' already exists. Skipping entry.")
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
