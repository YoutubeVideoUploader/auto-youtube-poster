"""
Contextual Importance Scorer for Malayalam Presenter Sentences v3.0
Evaluates sentence semantics, presenter tag context, and extracted entities to calculate an Importance Score (0.0 to 1.0).
"""

from typing import Dict, Any

TAG_BASE_IMPORTANCE = {
    "headline": 0.95,
    "important": 0.90,
    "intro": 0.85,
    "outro": 0.85,
    "question": 0.75,
    "transition": 0.70,
    "detail": 0.60,
    "announcement": 0.92
}


class ImportanceScorer:
    def __init__(self):
        pass

    def calculate_score(self, text: str, tag_name: str, entities: Dict[str, list]) -> float:
        """
        Calculates an importance score (0.0 - 1.0) based on segment tag type and entity density.
        """
        tag_key = tag_name.lower().strip()
        score = TAG_BASE_IMPORTANCE.get(tag_key, 0.65)

        # Entity Density Boosts
        if entities.get("movies"):
            score += 0.08 * len(entities["movies"])
        if entities.get("actors"):
            score += 0.06 * len(entities["actors"])
        if entities.get("directors"):
            score += 0.05 * len(entities["directors"])
        if entities.get("dates"):
            score += 0.06 * len(entities["dates"])
        if entities.get("ott"):
            score += 0.06 * len(entities["ott"])
        if entities.get("announcements"):
            score += 0.05 * len(entities["announcements"])

        # Cap between 0.0 and 1.0
        return float(round(min(1.0, max(0.2, score)), 2))

    def determine_sentence_type(self, tag_name: str, score: float, entities: Dict[str, list]) -> str:
        """
        Determines context type: announcement, headline, important, detail, transition, intro, outro, question.
        """
        if tag_name:
            return tag_name.lower().strip()
        if entities.get("announcements") or (entities.get("movies") and entities.get("dates")):
            return "announcement"
        if score >= 0.85:
            return "important"
        return "detail"
