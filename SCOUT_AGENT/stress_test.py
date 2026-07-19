import sys
import os
import json
import logging
from dotenv import load_dotenv

# Load the API key from the workspace root
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.engine import analyze_signal_with_llm

logging.basicConfig(level=logging.INFO)

# Difficult Test Cases
TEST_CASES = [
    {
        "name": "False Positive EdTech",
        "text": "An emerging EdTech startup just launched a completely free coding course for students. They are not charging any fees and are currently completely bootstrapped by the two founders without any external funding."
    },
    {
        "name": "Micro-Business Expansion",
        "text": "A local paan shop owner in Dharavi, Mumbai is looking to expand and open a second small stall across the street. He needs roughly Rs. 15,000 to buy the new cart and inventory."
    },
    {
        "name": "Ambiguous Corporate News",
        "text": "Reliance Industries mentioned they are generally looking into renewable energy over the next decade, but no specific projects, timelines, or capital allocations have been finalized or announced."
    }
]

def run_stress_test():
    print("--- STARTING STRESS TEST ---")
    results = []
    for case in TEST_CASES:
        print(f"\nEvaluating Case: {case['name']}")
        print(f"Signal: {case['text']}")
        try:
            # We assume a moderate trust score of 0.8 for these simulated news texts
            parsed = analyze_signal_with_llm(case['text'], trust_score=0.8)
            if parsed:
                results.append(parsed)
                print(f"Scored! LTV: {parsed.get('score_ltv')}, Propensity: {parsed.get('score_propensity')}")
            else:
                print("LLM rejected or failed to parse.")
        except Exception as e:
            print(f"Error: {e}")

    # Append to existing opportunities.json so we can see it in the UI
    db_path = "opportunities.json"
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
        
    data.extend(results)
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print("\n--- STRESS TEST COMPLETE, SAVED TO DB ---")

if __name__ == "__main__":
    run_stress_test()
