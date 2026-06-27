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
        logging.info("EduScout checking student portals and education updates...")
        
        for phrase in self.search_phrases:
            encoded_query = urllib.parse.quote(phrase)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            try:
                response = requests.get(rss_url, headers=self.get_headers(), timeout=10)
                if response.status_code != 200:
                    continue
                
                root = ET.fromstring(response.content)
                items = root.findall(".//item")[:3]
                
                for item in items:
                    title = item.find("title").text
                    link = item.find("link").text
                    
                    logging.info(f"EduScout found raw signal: {title}")
                    
                    # Checkpoint A: Web Scraping Start
                    logging.info(f"-> Attempting to fetch source content from URL...")
                    page_content = self.fetch_page_text(link)
                    
                    if not page_content or len(page_content) < 300:
                        logging.info("-> Source page locked or unreadable. Falling back to title text.")
                        page_content = title
                    else:
                        logging.info(f"-> Successfully extracted {len(page_content)} characters of text.")

                    # Checkpoint B: OpenRouter Handshake Start
                    logging.info("-> Sending payload to OpenRouter for financial evaluation...")
                    analysis_result = analyze_signal_with_llm(page_content)
                    
                    if analysis_result and isinstance(analysis_result, dict):
                        confidence = analysis_result.get("confidence_score", 0.0)
                        logging.info(f"-> LLM evaluation complete. Confidence: {confidence}")
                        
                        if confidence >= 0.75:
                            save_opportunity(analysis_result)
                    else:
                        logging.warning("-> LLM analysis returned empty or invalid structural data.")
                            
            except Exception as e:
                logging.error(f"EduScout encountered error processing phrase '{phrase}': {str(e)}")