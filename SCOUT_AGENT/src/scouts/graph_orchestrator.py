"""
graph_orchestrator.py — LangGraph State Machine for Zero-Hallucination Scouting
"""

import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from src.scouts.fetcher import search_web_ddg, fetch_page_text_antibot
from src.scouts.trust_validator import calculate_trust_score
from src.llm_client import llm_request
from src.engine import analyze_signal_with_llm

# Define the state passed between nodes
class ScoutState(TypedDict):
    query: str
    results_per_phrase: int
    search_results: List[Dict[str, str]]
    current_index: int
    current_url: str
    current_title: str
    current_text: str
    extracted_data: Optional[Dict[str, Any]]
    trust_score: float
    is_hallucinated: bool
    retries: int
    final_opportunities: List[Dict[str, Any]]

# --- Nodes ---

def search_node(state: ScoutState):
    """Searches the web for the query and gets initial links."""
    logging.info(f"[Graph] Searching for: {state['query']}")
    if not state.get("search_results"):
        results = search_web_ddg(state["query"], state["results_per_phrase"])
        state["search_results"] = results
    return state

def select_next_url(state: ScoutState):
    """Selects the next URL from the search results to process."""
    idx = state["current_index"]
    results = state["search_results"]
    
    if idx >= len(results):
        state["current_url"] = ""
        return state
        
    target = results[idx]
    state["current_url"] = target["link"]
    state["current_title"] = target["title"]
    state["current_index"] = idx + 1
    state["retries"] = 0
    state["is_hallucinated"] = False
    state["extracted_data"] = None
    
    # Calculate trust score early
    state["trust_score"] = calculate_trust_score(state["current_url"])
    logging.info(f"[Graph] Selected URL: {state['current_url']} (Trust: {state['trust_score']})")
    
    return state

def fetch_and_distill_node(state: ScoutState):
    """Fetches the webpage using cloudscraper to bypass bots, and distills HTML."""
    if not state["current_url"]:
        return state
        
    logging.info(f"[Graph] Anti-bot fetching: {state['current_url']}")
    text = fetch_page_text_antibot(state["current_url"])
    
    if not text or len(text) < 300:
        logging.info("[Graph] Content too short, falling back to title snippet.")
        state["current_text"] = state["current_title"]
    else:
        state["current_text"] = text
        
    return state

def extract_node(state: ScoutState):
    """Uses LLM to extract financial opportunity signals from the text."""
    if not state["current_text"]:
        return state
        
    logging.info("[Graph] Extracting structured data...")
    # Using existing engine logic to extract
    result = analyze_signal_with_llm(state["current_text"])
    
    if result:
        # Add veracity score tracking
        result["veracity_score"] = state["trust_score"] * 100.0
        result["source_url"] = state["current_url"]
        state["extracted_data"] = result
    else:
        state["extracted_data"] = None
        
    return state

def critique_node(state: ScoutState):
    """
    CRAG Pattern: Critique the extraction. Ensure no hallucinations by cross-checking
    the extracted JSON against the original text.
    """
    data = state.get("extracted_data")
    if not data or data.get("priority_tier") == "P4":
        state["is_hallucinated"] = False
        return state
        
    logging.info("[Graph] Critiquing extracted data for hallucinations...")
    
    prompt = "You are a strict fact-checker. Compare the Extracted JSON to the Original Text. If the JSON contains numbers, dates, or claims not found in the original text, output {\"is_hallucinated\": true, \"reason\": \"...\"}. Otherwise output {\"is_hallucinated\": false}."
    
    user_msg = f"Original Text:\n{state['current_text'][:2000]}\n\nExtracted JSON:\n{data}"
    
    critique_result = llm_request(prompt, user_msg, caller="Critic")
    
    if critique_result and critique_result.get("is_hallucinated"):
        logging.warning(f"[Graph] Hallucination detected! Reason: {critique_result.get('reason')}")
        state["is_hallucinated"] = True
        state["retries"] += 1
        # Penalize veracity score due to hallucinations
        if state["extracted_data"]:
             state["extracted_data"]["veracity_score"] *= 0.5
    else:
        logging.info("[Graph] Validation passed: Zero hallucinations.")
        state["is_hallucinated"] = False
        
    return state

def aggregate_node(state: ScoutState):
    """Adds validated opportunity to the final list."""
    data = state.get("extracted_data")
    if data and data.get("priority_tier") != "P4" and not state["is_hallucinated"]:
        state["final_opportunities"].append(data)
    return state

# --- Routing logic ---

def route_after_search(state: ScoutState):
    if not state["search_results"]:
        return "end"
    return "select"

def route_after_select(state: ScoutState):
    if not state["current_url"]:
        return "end"
    if state["trust_score"] < 0.3:
        logging.info("[Graph] Skipping URL due to low trust score.")
        return "select" # Skip bad domains entirely
    return "fetch"

def route_after_critique(state: ScoutState):
    if state["is_hallucinated"] and state["retries"] < 2:
        logging.info("[Graph] Retrying extraction to fix hallucination...")
        return "extract"
    return "aggregate"

# --- Graph Assembly ---

def build_scout_graph():
    workflow = StateGraph(ScoutState)
    
    workflow.add_node("search", search_node)
    workflow.add_node("select", select_next_url)
    workflow.add_node("fetch", fetch_and_distill_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("aggregate", aggregate_node)
    
    workflow.set_entry_point("search")
    
    workflow.add_conditional_edges("search", route_after_search, {"select": "select", "end": END})
    workflow.add_conditional_edges("select", route_after_select, {"fetch": "fetch", "select": "select", "end": END})
    workflow.add_edge("fetch", "extract")
    workflow.add_edge("extract", "critique")
    workflow.add_conditional_edges("critique", route_after_critique, {"extract": "extract", "aggregate": "aggregate"})
    workflow.add_edge("aggregate", "select") # Loop back to next URL
    
    return workflow.compile()

def run_graph_for_phrase(phrase: str, results_per_phrase: int) -> List[Dict]:
    """Entry point for base_scout to execute the graph."""
    graph = build_scout_graph()
    initial_state = {
        "query": phrase,
        "results_per_phrase": results_per_phrase,
        "search_results": [],
        "current_index": 0,
        "current_url": "",
        "current_title": "",
        "current_text": "",
        "extracted_data": None,
        "trust_score": 0.0,
        "is_hallucinated": False,
        "retries": 0,
        "final_opportunities": []
    }
    
    # LangGraph execute
    final_state = graph.invoke(initial_state)
    return final_state["final_opportunities"]
