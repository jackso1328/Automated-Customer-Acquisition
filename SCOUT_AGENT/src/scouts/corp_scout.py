"""
corp_scout.py — Corporate & Infrastructure Scout

Monitors Google News for high-value corporate signals:
manufacturing expansions, government tenders, startup funding rounds, MSME trade.
"""

from src.scouts.base_scout import BaseScout


class CorpScout(BaseScout):
    def __init__(self):
        super().__init__()
        self.scout_name = "CorpScout"
        self.search_phrases = [
            "manufacturing plant expansion India investment",
            "government infrastructure tender awarded NHAI",
            "startup series B funding raised India",
            "cross border trade export license MSME",
        ]
