import sys
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.engine import analyze_signal_with_llm

logging.basicConfig(level=logging.INFO)

GAUNTLET_CASES = [
    {
        "id": "T1",
        "name": "Alias Duplication - Part 1",
        "text": "RIL announced a massive $1B expansion into green energy today, seeking syndicated loans from top Indian banks."
    },
    {
        "id": "T2",
        "name": "Alias Duplication - Part 2",
        "text": "Reliance Industries is urgently looking to raise $500M to fund their solar panel manufacturing plant."
        # Flaw: Currently creates two separate companies instead of merging RIL + Reliance.
    },
    {
        "id": "T3",
        "name": "Temporal Decay Test",
        "text": "In a major announcement back in August 2021, L&T secured a $2B metro rail project."
        # Flaw: System scores this as P1 today because it doesn't decay old news.
    },
    {
        "id": "T4",
        "name": "Subsidiary Confusion",
        "text": "Tata Motors reported a devastating $400M loss this quarter, shutting down 3 plants. Meanwhile, Tata Consultancy Services (TCS) just signed a massive $1B cloud transformation deal."
        # Flaw: Engine blends the sentiment, penalizing the good TCS lead because of Tata Motors.
    },
    {
        "id": "T5",
        "name": "The Soft-Regulatory Probe",
        "text": "SEBI has asked for 'routine accounting clarifications' from Adani Green regarding their Mauritius subsidiaries. No formal charges have been filed."
        # Flaw: Engine might ignore it because 'fraud' isn't explicitly used, missing a huge KYC risk.
    },
    {
        "id": "T6",
        "name": "The Syndicate Loan Paradox",
        "text": "Air India is raising an astronomical $10 Billion to buy 500 new jets. Global banks like Citi and JP Morgan are leading."
        # Flaw: Huge scale, but SBI's actual cut is tiny. Engine scores it 10/10 scale and revenue.
    },
    {
        "id": "T7",
        "name": "Cannibalization (Existing Client)",
        "text": "SBI's largest existing client, Indian Oil Corp, needs a Rs 5,000 Cr working capital limit extension."
        # Flaw: Engine treats this as a 'new acquisition' lead rather than an 'upsell/retention' lead.
    },
    {
        "id": "T8",
        "name": "Micro-Cap Disguise",
        "text": "Ramesh Vada Pav stall, heavily praised as 'The Apple of Indian Street Food', is expanding to 3 new carts and needs ₹5 Lakhs urgently to revolutionize the culinary sector."
        # Flaw: Engine gets hyped by 'Apple' and 'revolutionize' and over-scores it.
    },
    {
        "id": "T9",
        "name": "Geographic Mismatch",
        "text": "Infosys is raising $50M exclusively through US regional banks to fund their new campus in Silicon Valley."
        # Flaw: SBI (India) has no advantage here, but engine sees big tech company and scores high.
    },
    {
        "id": "T10",
        "name": "Too Big To Fail Paradox",
        "text": "The government is orchestrating a Rs 15,000 Cr bailout for the bankrupt Vodafone Idea. The finance minister has requested PSU banks to syndicate the debt."
        # Flaw: It's bankrupt (bad), but sovereign backed (good).
    },
    {
        "id": "T11",
        "name": "The Sentiment Reversal",
        "text": "Byju's has completely collapsed and defaulted on their $1.2B Term Loan B. However, an anonymous UAE royal just injected $2B equity to completely clear all debt and restart operations."
        # Flaw: Engine gets stuck on 'collapsed and defaulted' and marks it P4, missing the $2B revival.
    },
    {
        "id": "T12",
        "name": "The Stealth Mode Unicorn",
        "text": "A stealth startup founded by 3 ex-Stripe executives just raised $50M in seed funding from Sequoia, operating out of a tiny garage in Bengaluru. They are setting up their banking infrastructure today."
        # Flaw: "Tiny garage" makes the engine think it's a micro-business, ignoring the $50M Sequoia funding.
    }
]

def run_gauntlet():
    print("\n" + "="*60)
    print("INITIATING THE 12-TEST ULTIMATE GAUNTLET")
    print("="*60)
    
    results = []
    
    # We will clear the existing opportunities.json to strictly observe this test
    db_path = "opportunities.json"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    for i, case in enumerate(GAUNTLET_CASES):
        print(f"\n[{i+1}/12] Testing: {case['name']}")
        try:
            parsed = analyze_signal_with_llm(case['text'], trust_score=0.9)
            if parsed:
                # Add test ID to trace it later
                parsed["test_id"] = case["id"]
                tier = parsed.get('priority_tier', 'UNKNOWN')
                print(f"SCORED -> Tier: {tier} | Company: {parsed.get('company_or_entity')}")
                results.append(parsed)
            else:
                print("FAILED TO PARSE")
        except Exception as e:
            print(f"CRASHED: {e}")

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
        
    print("\nGAUNTLET COMPLETE. Data saved to opportunities.json")
    print("Observe the flaws: Duplicates exist, no temporal decay, subsidiary blending.")

if __name__ == "__main__":
    run_gauntlet()
