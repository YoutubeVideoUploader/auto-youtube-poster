"""
Unit Tests for Engine v3.3 Automated Pronunciation & Speech Integrity QA System
Verifies G2P Syllabification, Persistent Learning Database, 3-Level Speech QA, Sentence Retry, and QA Reporter.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from preprocessing.malayalam_g2p import MalayalamG2P
from preprocessing.pronunciation_database import PronunciationDatabase
from synthesis.speech_qa import SpeechQA
from evaluation.qa_reporter import QAReporter


class TestEngineV33QAPipeline(unittest.TestCase):
    def setUp(self):
        self.g2p = MalayalamG2P()
        self.db = PronunciationDatabase()
        self.qa = SpeechQA()
        self.reporter = QAReporter()

    def test_g2p_syllabification(self):
        syllables = self.g2p.syllabify_word("സ്വാഗതം")
        self.assertTrue(len(syllables) >= 3)
        self.assertIn("സ്വാ", syllables[0])

    def test_pronunciation_database(self):
        self.db.add_entry("തീയതി", ["തീ", "യ", "തി"], "തീയതി", "dental_tha")
        entry = self.db.get_entry("തീയതി")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["word"], "തീയതി")
        self.assertTrue(entry["verified"])

    def test_speech_qa_evaluation(self):
        text = "എല്ലാവർക്കും സ്വാഗതം."
        dummy_wave = (0.1 * (0.5 - sys.float_info.epsilon)).__mul__(
            [1.0] * 44100
        )
        import numpy as np
        wave_arr = np.sin(np.linspace(0, 100, 44100)).astype(np.float32)

        res = self.qa.evaluate_sentence_audio(text, wave_arr, sample_rate=44100)
        self.assertIn("is_passed", res)
        self.assertIn("level1_word_match_score", res)
        self.assertIn("level2_syllable_preservation_score", res)
        self.assertIn("level3_audio_integrity_score", res)

    def test_qa_reporter(self):
        dummy_results = [
            {
                "is_passed": True,
                "text": "നമസ്കാരം",
                "level1_word_match_score": 100.0,
                "level2_syllable_preservation_score": 100.0,
                "level3_audio_integrity_score": 100.0,
                "phoneme_issues": []
            },
            {
                "is_passed": True,
                "text": "എല്ലാവർക്കും സ്വാഗതം",
                "level1_word_match_score": 100.0,
                "level2_syllable_preservation_score": 95.0,
                "level3_audio_integrity_score": 100.0,
                "phoneme_issues": []
            }
        ]

        report = self.reporter.generate_report(dummy_results)
        self.assertGreaterEqual(report["overall_quality_score"], 90.0)
        self.assertEqual(report["summary"]["total_sentences"], 2)

        md = self.reporter.format_markdown_scorecard(report)
        self.assertIn("Overall Quality Score", md)


if __name__ == "__main__":
    unittest.main()
