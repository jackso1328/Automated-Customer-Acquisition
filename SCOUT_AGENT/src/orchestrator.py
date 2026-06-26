import logging
from src.scouts.edu_scout import EduScout

class ScoutOrchestrator:
    def __init__(self):
        # We start with the EduScout; we will append agri and corp scouts here next
        self.scouts = [
            EduScout()
        ]

    def execute_dynamic_search(self):
        """
        Runs through all active scouts sequentially to sweep the internet 
        for financial signals without any user intervention.
        """
        logging.info("Orchestrator cycling through deployed web scouts...")
        for scout in self.scouts:
            try:
                scout.scan_for_opportunities()
            except Exception as e:
                logging.error(f"Failed executing scout cycle: {str(e)}")
