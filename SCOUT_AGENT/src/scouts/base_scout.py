"""
base_scout.py — Abstract Base for All Web Scouts (LangGraph Edition)

Provides shared infrastructure for all scout implementations, delegating
the heavy lifting of anti-bot scraping and validation to the graph orchestrator.
"""

import logging
from src.database import save_opportunity
from src.scouts.graph_orchestrator import run_graph_for_phrase

class BaseScout:
    """
    Abstract scout that all domain-specific scouts inherit from.
    
    Subclasses only need to define:
      - self.scout_name:      Human-readable label for logs.
      - self.search_phrases:  List of search queries.
      - self.results_per_phrase: How many results to process per phrase (default 3).
    """

    def __init__(self):
        self.scout_name = "BaseScout"
        self.search_phrases = []
        self.results_per_phrase = 3

    def scan_for_opportunities(self):
        """
        Executes the LangGraph state machine for each search phrase and 
        saves validated, hallucination-free opportunities to the database.
        """
        logging.info(f"{self.scout_name} starting LangGraph scan cycle...")

        for phrase in self.search_phrases:
            try:
                logging.info(f"[{self.scout_name}] Orchestrating graph for phrase: {phrase}")
                
                # The graph handles DDG search -> Anti-Bot Fetch -> Extract -> Critique
                validated_opportunities = run_graph_for_phrase(phrase, self.results_per_phrase)
                
                for opp in validated_opportunities:
                    # Save to JSON database
                    save_opportunity(opp)
                    logging.info(f"[{self.scout_name}] Successfully saved validated opportunity!")

            except Exception as e:
                logging.error(f"{self.scout_name} error executing graph on '{phrase}': {e}")