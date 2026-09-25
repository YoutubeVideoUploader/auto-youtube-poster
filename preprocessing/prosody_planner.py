"""
Presenter Intelligence Prosody Planner v3.0
Synthesizes Entity Detection, Contextual Importance Scoring, Syntactic Phrase Boundary Parsing,
and calculates sentence-level & phrase-level acoustic metadata (speed, energy boost, pauses, contours).
"""

import re
from typing import Dict, Any, List
from preprocessing.entity_detector import EntityDetector
from preprocessing.importance_scorer import ImportanceScorer
from preprocessing.phrase_splitter import PhraseSplitter


class ProsodyPlanner:
    def __init__(self):
        self.entity_detector = EntityDetector()
        self.importance_scorer = ImportanceScorer()
        self.phrase_splitter = PhraseSplitter()

    def plan_sentence_prosody(self, text: str, tag_name: str = "detail", sentence_id: int = 1) -> Dict[str, Any]:
        """
        Analyzes a sentence and produces full Presenter Intelligence metadata.
        """
        clean_text = self.inject_semantic_pauses(text)
        entities = self.entity_detector.extract_entities(clean_text)
        all_entity_phrases = self.entity_detector.get_all_entity_phrases(clean_text)

        importance_score = self.importance_scorer.calculate_score(clean_text, tag_name, entities)
        sentence_type = self.importance_scorer.determine_sentence_type(tag_name, importance_score, entities)

        # 1. Steady 1.05x speaking speed for natural, authentic YouTube presenter pace
        speed = 1.05

        # 2. Consistent 0.0 dB Energy across all segments (prevents artificial volume/tone shifts between topics)
        energy_boost_db = 0.0

        # 3. Map Pause Before/After
        pause_before = 100
        pause_after = 300
        if sentence_type in ["headline", "announcement"]:
            pause_before = 200
            pause_after = 450
        elif sentence_type == "important":
            pause_before = 150
            pause_after = 350
        elif sentence_type == "transition":
            pause_before = 150
            pause_after = 400
        elif sentence_type == "intro":
            pause_before = 100
            pause_after = 400
        elif sentence_type == "outro":
            pause_before = 200
            pause_after = 500

        # 4. Parse Phrase Boundaries
        phrases = self.phrase_splitter.split_into_phrases(clean_text, entities)

        metadata = {
          "sentence_id": sentence_id,
          "text": clean_text,
          "type": sentence_type,
          "importance": importance_score,
          "speed": speed,
          "energy_boost_db": energy_boost_db,
          "pause_before": pause_before,
          "pause_after": pause_after,
          "emphasis": all_entity_phrases,
          "entities": entities,
          "phrases": phrases
        }

        return metadata

    def inject_semantic_pauses(self, text: str) -> str:
        """
        Cleans text, normalizes ellipses, and removes redundant spaces.
        """
        processed = text.strip()
        processed = re.sub(r'\.{2,}', ',', processed)
        processed = re.sub(r'([,;:!?])([^\s])', r'\1 \2', processed)
        processed = re.sub(r'\s+', ' ', processed).strip()
        return processed
