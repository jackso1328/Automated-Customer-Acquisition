"""
base_scout.py — Abstract Base for All Web Scouts

Provides shared infrastructure for all scout implementations:
  - Randomized browser-like HTTP headers for stealth scraping.
  - HTML-to-text content extraction with noise removal.
  - A standardized scan loop that subclasses configure via attributes.
"""

import random
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import logging
from bs4 import BeautifulSoup
from src.engine import analyze_signal_with_llm
from src.database import save_opportunity

# Tier values that are worth saving (P4 = Archive, skip it)
SAVEABLE_TIERS = frozenset({"P1", "P2", "P3"})

# Minimum characters of page content before we fall back to title-only analysis
MIN_CONTENT_LENGTH = 300


class BaseScout:
    """
    Abstract scout that all domain-specific scouts inherit from.
    
    Subclasses only need to define:
      - self.scout_name:      Human-readable label for logs.
      - self.search_phrases:  List of Google News search queries.
      - self.results_per_phrase: How many RSS items to process per phrase (default 3).
    """

    def __init__(self):
        self.scout_name = "BaseScout"
        self.search_phrases = []
        self.results_per_phrase = 3
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ]

    def get_headers(self):
        """Returns randomized browser-like headers to avoid bot detection."""
        return {
            "User-Agent": random.choice(self._user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    def fetch_page_text(self, url):
        """
        Fetches a webpage, strips navigation/script noise, and returns
        the first 3000 characters of clean text content.
        """
        try:
            response = requests.get(
                url, headers=self.get_headers(), timeout=10, allow_redirects=True
            )
            if response.status_code != 200:
                logging.warning(f"Failed to fetch {url} — Status: {response.status_code}")
                return ""

            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()

            clean_text = " ".join(soup.get_text().split())
            return clean_text[:3000]

        except Exception as e:
            logging.error(f"Scout exception browsing {url}: {e}")
            return ""

    def scan_for_opportunities(self):
        """
        Standard scan loop: queries Google News RSS, scrapes each result,
        sends content to the LLM for analysis, and saves qualifying leads.
        
        Subclasses configure behavior via self.scout_name, self.search_phrases,
        and self.results_per_phrase — no need to override this method.
        """
        logging.info(f"{self.scout_name} starting scan cycle...")

        for phrase in self.search_phrases:
            encoded = urllib.parse.quote(phrase)
            rss_url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"

            try:
                response = requests.get(rss_url, headers=self.get_headers(), timeout=10)
                if response.status_code != 200:
                    continue

                root = ET.fromstring(response.content)
                items = root.findall(".//item")[:self.results_per_phrase]

                for item in items:
                    title = item.find("title").text
                    link = item.find("link").text

                    logging.info(f"{self.scout_name} found signal: {title}")

                    # Attempt to scrape full article content
                    page_content = self.fetch_page_text(link)
                    if not page_content or len(page_content) < MIN_CONTENT_LENGTH:
                        logging.info("-> Source unreadable. Falling back to title text.")
                        page_content = title
                    else:
                        logging.info(f"-> Extracted {len(page_content)} chars from source.")

                    # Send to LLM for financial analysis
                    logging.info("-> Sending to LLM for evaluation...")
                    result = analyze_signal_with_llm(page_content)

                    if result and isinstance(result, dict):
                        tier = result.get("priority_tier", "P4")
                        confidence = result.get("confidence_score", 0.0)
                        logging.info(f"-> Evaluation complete. Confidence: {confidence} | Tier: {tier}")

                        if tier in SAVEABLE_TIERS:
                            save_opportunity(result)
                    else:
                        logging.warning("-> LLM returned empty or invalid data.")

            except Exception as e:
                logging.error(f"{self.scout_name} error on phrase '{phrase}': {e}")