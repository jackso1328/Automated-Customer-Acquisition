"""
trust_validator.py — Domain and Source Credibility Verifier
"""

from urllib.parse import urlparse

# A set of highly trusted domains or domain suffixes.
TRUSTED_SUFFIXES = {
    ".gov.in",
    ".nic.in",
    ".ac.in",
    ".edu.in",
}

# Domains of tier-1 news or reliable sources
TRUSTED_DOMAINS = {
    "timesofindia.indiatimes.com",
    "thehindu.com",
    "indianexpress.com",
    "ndtv.com",
    "hindustantimes.com",
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "pib.gov.in",
    "livemint.com",
    "bloombergquint.com",
    "reuters.com",
    "bloomberg.com",
    "theprint.in"
}

# Domains known for rumors or low trust that we should actively avoid if they are the ONLY source
LOW_TRUST_DOMAINS = {
    "reddit.com",
    "quora.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
}

def get_domain(url: str) -> str:
    """Extracts the domain from a URL."""
    try:
        parsed_uri = urlparse(url)
        domain = parsed_uri.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def calculate_trust_score(url: str) -> float:
    """
    Calculates a basic trust score for a given URL based on its domain.
    Returns a score between 0.0 and 1.0.
    """
    domain = get_domain(url)
    if not domain:
        return 0.1
        
    for suffix in TRUSTED_SUFFIXES:
        if domain.endswith(suffix):
            return 1.0
            
    if domain in TRUSTED_DOMAINS:
        return 0.9
        
    if domain in LOW_TRUST_DOMAINS:
        return 0.2
        
    # Default score for standard unknown sites
    return 0.5
