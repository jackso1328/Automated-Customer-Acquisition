"""
edu_scout.py — Education Sector Scout

Monitors Google News for education-related financial signals:
admission deadlines, merit lists, counselling results, study abroad trends.
"""

from src.scouts.base_scout import BaseScout


class EduScout(BaseScout):
    def __init__(self):
        super().__init__()
        self.scout_name = "EduScout"
        self.search_phrases = [
            "engineering admission merit list 2026 admission open",
            "study abroad education loan intake news",
            "medical college counseling dates fees",
        ]