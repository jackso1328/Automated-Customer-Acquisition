import sys
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.engine import analyze_signal_with_llm

logging.basicConfig(level=logging.INFO)

SUPER_EXTREME_CASES = [
    {
        "name": "The Hidden Gem (Negative Surface, Massive Need)",
        "text": "TechGiant Industries announced today that they are shutting down three major manufacturing plants across India and laying off 2,000 workers due to severe margin compression. The stock plummeted 15%. However, buried in page 42 of the regulatory filing, the CFO noted this restructuring will free up $200M in immediate cash to partially fund a hostile takeover of rival firm DataCorp. The remaining $300M required for the acquisition needs to be secured by this Friday to close the deal, but their primary overseas lender just backed out unexpectedly."
    },
    {
        "name": "The Mirage (Massive Scale, Zero Propensity)",
        "text": "Global HyperSpace is committing to a staggering $2 Billion infrastructure mega-project in Mumbai, promising to create 50,000 jobs over the next year. They are aggressively expanding operations and hiring top talent. In a press conference, the founders proudly declared that their entire treasury is held in decentralized cryptocurrencies and the project is fully underwritten by an anonymous foreign Sovereign Wealth Fund. They explicitly stated they bypass the 'archaic and greedy traditional banking system' entirely, relying on blockchain smart contracts for all vendor payouts."
    }
]

def run_super_extreme_test():
    print("\n" + "="*60)
    print("INITIATING SUPER EXTREME AI STRESS TEST")
    print("="*60)
    
    results = []
    for i, case in enumerate(SUPER_EXTREME_CASES):
        print(f"\n[{i+1}/2] Testing: {case['name']}")
        print(f"Signal: {case['text']}")
        try:
            parsed = analyze_signal_with_llm(case['text'], trust_score=0.9)
            if parsed:
                tier = parsed.get('priority_tier', 'UNKNOWN')
                ltv = parsed.get('score_ltv', 0)
                prop = parsed.get('score_propensity', 0)
                scale = parsed.get('score_scale', 0)
                urgency = parsed.get('score_urgency', 0)
                xai = parsed.get('xai_reasoning', '')
                
                print(f"ENGINE SCORED -> Tier: {tier} | Scale: {scale} | Urgency: {urgency} | LTV: {ltv} | Propensity: {prop}")
                print(f"XAI REASONING: {xai}")
                results.append(parsed)
            else:
                print("ENGINE FAILED TO PARSE (Null Return)")
        except Exception as e:
            print(f"ENGINE CRASHED: {e}")

    # Save to JSON for UI inspection
    db_path = "opportunities.json"
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
        
    data.extend(results)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        
    print("\nSUPER EXTREME TEST COMPLETE.")

if __name__ == "__main__":
    run_super_extreme_test()
