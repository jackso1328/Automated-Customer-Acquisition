import random
import requests
from bs4 import BeautifulSoup
import logging

class BaseScout:
    def __init__(self):
        # A pool of common browser user-agents to blend into normal web traffic
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

    def get_headers(self):
        return {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

    def fetch_page_text(self, url):
        """
        Visits a webpage safely, strips away navigation bars/footers, 
        and extracts the core textual information.
        """
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Strip script, style, header, footer elements to clean the text
                for element in soup(["script", "style", "header", "footer", "nav"]):
                    element.decompose()
                    
                # Extract clean spacing text content
                clean_text = " ".join(soup.get_text().split())
                # Return the first 3000 characters to keep context size manageable
                return clean_text[:3000]
            else:
                logging.warning(f"Failed to fetch {url} - Status Code: {response.status_code}")
                return ""
        except Exception as e:
            logging.error(f"Scout exception browsing URL {url}: {str(e)}")
            return ""