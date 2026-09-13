"""
Unit Tests for Engine v3.0 Presenter Intelligence Pipeline
Verifies Pronunciation Overrides, Entity Detection, Importance Scoring, Phrase Splitting, and Metadata Generation.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from preprocessing.pronunciation_dictionary import PronunciationDictionary
from preprocessing.entity_detector import EntityDetector
from preprocessing.importance_scorer import ImportanceScorer
from preprocessing.phrase_splitter import PhraseSplitter
from preprocessing.prosody_planner import ProsodyPlanner


class TestPresenterIntelligenceV3(unittest.TestCase):
    def setUp(self):
        self.pdict = PronunciationDictionary()
        self.detector = EntityDetector()
        self.scorer = ImportanceScorer()
        self.splitter = PhraseSplitter()
        self.planner = ProsodyPlanner()

    def test_json_pronunciation_overrides(self):
        overrides = [
            {"text": "Netflix", "spoken_as": "നെറ്റ്ഫ്ലിക്സ്"},
            {"text": "L370", "spoken_as": "എൽ 370"}
        ]
        self.pdict.apply_overrides(overrides)
        res = self.pdict.replace_english_words("Netflix-ൽ L370 റിലീസ് ഉണ്ടാകും")
        self.assertIn("നെറ്റ്ഫ്ലിക്സ്", res)
        self.assertIn("എൽ 370", res)

    def test_entity_detection(self):
        text = "മോഹൻലാലിനെ നായകനാക്കി ജൂഡ് ആന്തണി ജോസഫ് സംവിധാനം ചെയ്യുന്ന L370 സിനിമ സെപ്റ്റംബർ 20-ന് നെറ്റ്ഫ്ലിക്സിൽ സ്ട്രീമിംഗ് ആരംഭിക്കും."
        entities = self.detector.extract_entities(text)
        self.assertIn("മോഹൻലാലിനെ", entities["actors"])
        self.assertIn("ജൂഡ് ആന്തണി ജോസഫ്", entities["directors"])
        self.assertIn("L370", entities["movies"])
        self.assertIn("നെറ്റ്ഫ്ലിക്സിൽ", entities["ott"])
        self.assertIn("സ്ട്രീമിംഗ് ആരംഭിക്കും", entities["announcements"])

    def test_importance_scoring(self):
        text = "മോഹൻലാലിനെ നായകനാക്കി L370 സിനിമ പ്രഖ്യാപിച്ചു."
        entities = self.detector.extract_entities(text)
        score = self.scorer.calculate_score(text, "headline", entities)
        self.assertGreaterEqual(score, 0.90)

    def test_phrase_splitting(self):
        text = "മോഹൻലാലിനെ നായകനാക്കി പൃഥ്വിരാജ് സുകുമാരൻ സംവിധാനം ചെയ്യുന്ന പുതിയ ചിത്രത്തിന്റെ റിലീസ് തീയതി പ്രഖ്യാപിച്ചു."
        phrases = self.splitter.split_into_phrases(text)
        self.assertGreaterEqual(len(phrases), 2)
        self.assertTrue(all("text" in p and "pause_after_ms" in p for p in phrases))

    def test_full_prosody_planner(self):
        text = "ചിത്രത്തിന്റെ റിലീസ് തീയതി സെപ്റ്റംബർ 20 ആണ്."
        meta = self.planner.plan_sentence_prosody(text, tag_name="important", sentence_id=1)
        self.assertEqual(meta["sentence_id"], 1)
        self.assertIn("importance", meta)
        self.assertIn("phrases", meta)
        self.assertIn("emphasis", meta)


if __name__ == "__main__":
    unittest.main()
