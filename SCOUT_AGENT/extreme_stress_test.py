import sys
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.engine import analyze_signal_with_llm

logging.basicConfig(level=logging.INFO)

EXTREME_CASES = [
    {
        "name": "Sarcasm & Bankruptcy Risk",
        "text": "Startup 'CashBurners Inc' is absolutely thrilled to announce they just burned through their last $10M of VC funding. They are throwing a massive yacht party to celebrate their impending bankruptcy and are 'urgently looking for naive banks' to issue them new corporate credit cards."
    },
    {
        "name": "Regulatory Red Flag (Double Negatives)",
        "text": "ABC Logistics, despite not being completely banned from applying for credit, has decided that under no circumstances will they not avoid seeking traditional banking partners. However, it should be noted the RBI recently flagged their directors for severe financial fraud and money laundering."
    },
    {
        "name": "Competitor Lock-in",
        "text": "HDFC Bank has just successfully disbursed a massive Rs. 500 Crore term loan to L&T for their new infrastructure project. The deal is fully closed and locked in for the next 10 years with severe prepayment penalties."
    },
    {
        "name": "Data Overload & Distraction",
        "text": "Apple just announced a $1 Billion dividend for its shareholders. In other news, a small local manufacturer 'Pune Auto Parts' is urgently seeking a Rs. 50 Lakh working capital loan to fulfill a sudden surge in orders. Meanwhile, Microsoft released a new update for Windows 11 that changes the taskbar color."
    }
]

def run_extreme_test():
    print("\n" + "="*50)
    print("INITIATING EXTREME AI STRESS TEST")
    print("="*50)
    
    results = []
    for i, case in enumerate(EXTREME_CASES):
        print(f"\n[{i+1}/4] Testing: {case['name']}")
        print(f"Signal: {case['text']}")
        try:
            parsed = analyze_signal_with_llm(case['text'], trust_score=0.9)
            if parsed:
                tier = parsed.get('priority_tier', 'UNKNOWN')
                ltv = parsed.get('score_ltv', 0)
                prop = parsed.get('score_propensity', 0)
                xai = parsed.get('xai_reasoning', '')
                
                print(f"ENGINE SCORED -> Tier: {tier} | LTV: {ltv} | Propensity: {prop}")
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
        
    print("\nEXTREME TEST COMPLETE. Data appended to opportunities.json")

if __name__ == "__main__":
    run_extreme_test()
