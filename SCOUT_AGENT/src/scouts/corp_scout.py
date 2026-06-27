import urllib.parse
import xml.etree.ElementTree as ET
import requests
import logging
from src.scouts.base_scout import BaseScout
from src.engine import analyze_signal_with_llm
from src.database import save_opportunity

class CorpScout(BaseScout):
    def __init__(self):
        super().__init__()
        # Autonomous search phrases targeting high-value corporate deals
        self.search_phrases = [
            "manufacturing plant expansion India investment",
            "government infrastructure tender awarded NHAI",
            "startup series B funding raised India",
            "cross border trade export license MSME"
        ]

    def scan_for_opportunities(self):
        logging.info("CorpScout hunting for major business expansions and government tenders...")
        
        for phrase in self.search_phrases:
            encoded_query = urllib.parse.quote(phrase)
            # Focused strictly on Indian business news
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
                    
                    logging.info(f"CorpScout found corporate signal: {title}")
                    
                    page_content = self.fetch_page_text(link)
                    if not page_content or len(page_content) < 300:
                        page_content = title

                    analysis_result = analyze_signal_with_llm(page_content)
                    
                    if analysis_result and isinstance(analysis_result, dict):
                        confidence = analysis_result.get("confidence_score", 0.0)
                        
                        # Set a slightly higher bar for corporate leads since the loan amounts are massive
                        if confidence >= 0.85:
                            save_opportunity(analysis_result)
                            
            except Exception as e:
                logging.error(f"CorpScout encountered error processing phrase '{phrase}': {str(e)}")
