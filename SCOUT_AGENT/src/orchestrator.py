import logging
from src.scouts.edu_scout import EduScout
from src.scouts.corp_scout import CorpScout

class ScoutOrchestrator:
    def __init__(self):
        # The swarm is growing. It will run Edu first, then Corp immediately after.
        self.scouts = [
            EduScout(),
            CorpScout()
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
