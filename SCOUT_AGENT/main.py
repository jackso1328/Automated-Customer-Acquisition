import time
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from src.orchestrator import ScoutOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def run_autonomous_scout_cycle():
    """
    This function acts as the automated trigger. 
    No human interaction is needed to fire this.
    """
    logging.info("--- Starting Autonomous Opportunity Discovery Cycle ---")
    try:
        # Initialize the brain
        orchestrator = ScoutOrchestrator()
        
        # Execute the discovery loop across random or sequential sectors
        orchestrator.execute_dynamic_search()
        
    except Exception as e:
        logging.error(f"Error encountered during autonomous execution: {str(e)}")
    
    logging.info("--- Cycle Completed. Agent entering standby mode. ---")

if __name__ == "__main__":
    logging.info("Initializing SBI Opportunity Scout Agent Daemon...")
    
    # Setup the background scheduler
    scheduler = BackgroundScheduler()
    
    # Schedule the agent to wake up and run every 4 hours automatically
    scheduler.add_job(run_autonomous_scout_cycle, 'interval', hours=4, next_run_time=datetime.now())
    scheduler.start()
    
    logging.info("Agent is actively monitoring the internet. Press Ctrl+C to terminate.")
    
    # Keep the main process alive while the background thread executes on schedule
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Shutting down Scout Agent gracefully...")
        scheduler.shutdown()
