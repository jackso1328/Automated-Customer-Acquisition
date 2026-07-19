"""
fetcher.py — Anti-Bot Web Fetcher
"""

import cloudscraper
from bs4 import BeautifulSoup
import logging
from duckduckgo_search import DDGS

# Minimum characters of page content before we fall back to title-only analysis
MIN_CONTENT_LENGTH = 300

def get_cloudscraper():
    """Returns a configured cloudscraper instance."""
    # cloudscraper automatically handles standard bot protections (Cloudflare JS challenges, etc.)
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def search_web_ddg(query: str, num_results: int = 3) -> list:
    """
    Searches the web using DuckDuckGo (free, no API key needed).
    Returns a list of dicts with 'title', 'href', 'body'.
    """
    results = []
    try:
        with DDGS() as ddgs:
            # We use 'news' search if it's an event, or general text search
            # We'll stick to text search which often yields news and official pages
            for r in ddgs.text(query, max_results=num_results):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
    except Exception as e:
        logging.error(f"DDG Search failed for query '{query}': {e}")
    return results

def fetch_page_text_antibot(url: str) -> str:
    """
    Fetches a webpage bypassing bot protection, strips navigation/script noise, 
    and returns clean text content.
    """
    try:
        scraper = get_cloudscraper()
        response = scraper.get(url, timeout=15)
        
        if response.status_code != 200:
            logging.warning(f"Failed to fetch {url} — Status: {response.status_code}")
            return ""

        # DOM Distillation
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form"]):
            tag.decompose()

        clean_text = " ".join(soup.get_text().split())
        return clean_text[:4000] # Increased to 4000 for better LLM context
        
    except Exception as e:
        logging.error(f"Anti-Bot Fetcher exception browsing {url}: {e}")
        return ""
