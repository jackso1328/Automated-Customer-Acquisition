import urllib.parse
import xml.etree.ElementTree as ET
import requests
import logging
from src.scouts.base_scout import BaseScout
from src.engine import analyze_signal_with_llm
from src.database import save_opportunity

class EduScout(BaseScout):
    def __init__(self):
        super().__init__()
        # Automated autonomous search phrases to feed the discovery loops
        self.search_phrases = [
            "engineering admission merit list 2026 admission open",
            "study abroad education loan intake news",
            "medical college counseling dates fees"
        ]

    def scan_for_opportunities(self):
        """
        Executes the autonomous loop: generates search queries, finds links,
        extracts text, evaluates via OpenRouter, and saves valid matches.
        """
        logging.info("EduScout checking student portals and education updates...")
        
        for phrase in self.search_phrases:
            # Construct a safe Google News RSS tracking feed URL
            encoded_query = urllib.parse.quote(phrase)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            try:
                response = requests.get(rss_url, headers=self.get_headers(), timeout=10)
                if response.status_code != 200:
                    continue
                
                # Parse the XML response feed format
                root = ET.fromstring(response.content)
                
                # Grab the top 3 freshest news/event items
                items = root.findall(".//item")[:3]
                
                for item in items:
                    title = item.find("title").text
                    link = item.find("link").text
                    
                    logging.info(f"EduScout found raw signal: {title}")
                    
                    # Core Autonomy: Follow the link and grab the webpage body text
                    page_content = self.fetch_page_text(link)
                    if not page_content or len(page_content) < 300:
                        # Fallback to the title text if the page was unreadable or locked
                        page_content = title

                    # Hand off the unstructured text to our OpenRouter intelligence layer
                    analysis_result = analyze_signal_with_llm(page_content)
                    
                    # If the LLM successfully classified a strong opportunity, store it
                    if analysis_result and isinstance(analysis_result, dict):
                        # Force default evaluation if confidence score is missing
                        confidence = analysis_result.get("confidence_score", 0.0)
                        
                        # Only register high-quality prospects to keep database clear
                        if confidence >= 0.75:
                            save_opportunity(analysis_result)
                            
            except Exception as e:
                logging.error(f"EduScout encountered error processing phrase '{phrase}': {str(e)}")
