"""
database.py — Entity Graph Database

Handles read/write operations against opportunities.json.
Upgraded to act as an Entity Graph:
1. Normalizes companies to prevent duplicates.
2. Aggregates multiple signals into a single entity profile.
3. Applies mathematical temporal decay to old leads.
"""

import os
import json
import logging
import time
import math

DB_FILE = "opportunities.json"

# Mathematical Decay: 0.05 decay_rate means half-life of ~14 days.
DECAY_RATE = 0.05 

def initialize_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        logging.info(f"Initialized empty Entity Graph at {DB_FILE}")

def save_opportunity(new_data):
    """
    Saves a signal by either creating a new entity or aggregating into an existing one.
    """
    initialize_db()

    # The LLM now provides a normalized name (e.g. 'Reliance Industries' instead of 'RIL')
    entity_name = new_data.get("normalized_company_name") or new_data.get("company_or_entity", "")
    entity_name = entity_name.strip()
    
    if not entity_name:
        return False

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            graph_nodes = json.load(f)

        # Look for existing entity
        target_entity = None
        for node in graph_nodes:
            if node.get("normalized_company_name", node.get("company_or_entity", "")).lower() == entity_name.lower():
                target_entity = node
                break

        now = time.time()

        if target_entity:
            # ── AGGREGATE EXISTING ENTITY ──
            logging.info(f"Aggregating new signal for existing entity: {entity_name}")
            
            # Maintain a history of signals
            history = target_entity.get("signal_history", [target_entity.get("detected_signal", "")])
            history.append(new_data.get("detected_signal", ""))
            target_entity["signal_history"] = list(set(history)) # Deduplicate exact strings
            
            # Update the primary signal to the freshest one
            target_entity["detected_signal"] = new_data.get("detected_signal", "")
            target_entity["xai_reasoning"] = new_data.get("xai_reasoning", "")
            
            # Aggregate scores (Take the maximum across all signals)
            target_entity["score_ltv"] = max(target_entity.get("score_ltv", 0), new_data.get("score_ltv", 0))
            target_entity["score_propensity"] = max(target_entity.get("score_propensity", 0), new_data.get("score_propensity", 0))
            target_entity["confidence_score"] = max(target_entity.get("confidence_score", 0), new_data.get("confidence_score", 0))
            
            # Update freshness
            target_entity["last_updated_timestamp"] = now
            target_entity["is_existing_client"] = new_data.get("is_existing_client", False)
            
        else:
            # ── CREATE NEW ENTITY ──
            logging.info(f"Creating new entity node for: {entity_name}")
            new_data["normalized_company_name"] = entity_name
            new_data["signal_history"] = [new_data.get("detected_signal", "")]
            new_data["last_updated_timestamp"] = now
            graph_nodes.append(new_data)

        # Write back to graph
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(graph_nodes, f, indent=4)

        return True

    except Exception as e:
        logging.error(f"Failed to update Entity Graph: {e}")
        return False


def get_all_opportunities():
    """
    Reads the Entity Graph and applies Temporal Decay dynamically 
    before returning data to the Dashboard.
    """
    initialize_db()
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            graph_nodes = json.load(f)
            
        now = time.time()
        
        for entity in graph_nodes:
            # 1. Calculate Age
            timestamp = entity.get("last_updated_timestamp", now)
            days_old = max(0, (now - timestamp) / (24 * 3600))
            
            # 2. Apply Mathematical Decay
            base_score = entity.get("confidence_score", 0)
            decay_factor = math.exp(-DECAY_RATE * days_old)
            decayed_score = round(base_score * decay_factor, 2)
            
            entity["decayed_confidence_score"] = decayed_score
            entity["days_since_last_signal"] = int(days_old)
            
            # 3. Dynamically re-assign tier based on DECAYED score
            percentage = int(decayed_score * 100)
            
            # Ensure compliance flagged entities stay P4
            if entity.get("compliance_risk_flag", False):
                tier = "P4"
            else:
                if percentage >= 85: tier = "P1"
                elif percentage >= 70: tier = "P2"
                elif percentage >= 50: tier = "P3"
                else: tier = "P4"
                
            entity["priority_tier"] = tier
            
        # Sort so P1 is always at the top before returning
        def get_tier_rank(tier):
            ranks = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
            return ranks.get(tier, 99)
            
        graph_nodes.sort(key=lambda x: (get_tier_rank(x.get("priority_tier", "P4")), -x.get("decayed_confidence_score", 0)))
            
        return graph_nodes
        
    except Exception as e:
        logging.error(f"Failed to read Entity Graph: {e}")
        return []