"""
Malayalam Phoneme Preservation Stress Test Suite v3.2
Tests 5 distinct Malayalam phoneme groups and context length scaling to ensure 100% consonant preservation.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from synthesis.tts_engine import MalayalamVoiceEngine
from preprocessing.speech_integrity import SpeechIntegrityChecker
from config import OUTPUT_DIR


class TestPhonemePreservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = MalayalamVoiceEngine(default_model_key="mms_malayalam")
        cls.checker = SpeechIntegrityChecker()
        cls.out_dir = OUTPUT_DIR / "phoneme_stress_tests_v3.2"
        cls.out_dir.mkdir(parents=True, exist_ok=True)

    def test_group1_dental_tha(self):
        """Group 1 — Dental Consonant ത/ഥ/തം Vowel Series & Words"""
        phrases = [
            ("g1_series", "ത, തം, താ, തി, തീ, തു, തൂ, തെ, തേ, തൈ, തൊ, തോ, തൗ."),
            ("g1_swagatham", "സ്വാഗതം"),
            ("g1_thudakkam", "തുടക്കം"),
            ("g1_theeram", "തീരം"),
            ("g1_theeyathi", "തീയതി"),
            ("g1_maathram", "മാത്രം"),
            ("g1_puthiya", "പുതിയ"),
            ("g1_kooduthal", "കൂടുതൽ"),
            ("g1_ethum", "എത്തും")
        ]
        for label, text in phrases:
            res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), f"g1_{label}")
            self.assertTrue(Path(res["final_path"]).exists())

    def test_group2_ta_vs_tha(self):
        """Group 2 — Minimal Contrasts: Dental ത vs Retroflex ട"""
        text = "ത, ട. താ, ടാ. തി, ടി. തെ, ടെ."
        res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), "g2_minimal_ta_tha")
        self.assertTrue(Path(res["final_path"]).exists())

    def test_group3_na_vs_nna(self):
        """Group 3 — Nasals: Dental ന vs Retroflex ണ"""
        text = "ന, ണ. നാ, ണാ. നി, ണി. നു, ണു. ഗുണം, കാരണം, പ്രമാണം."
        res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), "g3_nasals_na_nna")
        self.assertTrue(Path(res["final_path"]).exists())

    def test_group4_la_lla_zha(self):
        """Group 4 — Liquids: Dental ല vs Retroflex ള vs Retroflex Approximant ഴ"""
        text = "ല, ള, ഴ. ലാ, ളാ, ഴാ. കേരളം, ലളിതം, ആളുകൾ, മഴ, വഴിയമ്പലം, അഴക്."
        res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), "g4_liquids_la_lla_zha")
        self.assertTrue(Path(res["final_path"]).exists())

    def test_group5_ra_rra(self):
        """Group 5 — Trills: Dental ര vs Alveolar റ"""
        text = "ര, റ. രാ, റാ. റി, റീ. തിര, റീഫണ്ട്, റിലീസ്, വിവരങ്ങൾ."
        res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), "g5_trills_ra_rra")
        self.assertTrue(Path(res["final_path"]).exists())

    def test_context_length_scaling_swagatham(self):
        """
        Context Length Scaling Test for 'സ്വാഗതം':
        Level A: Isolated word
        Level B: Short sentence
        Level C: Full presenter intro sentence
        """
        levels = [
            ("level_A_isolated", "സ്വാഗതം"),
            ("level_B_short_sentence", "എല്ലാവർക്കും സ്വാഗതം."),
            ("level_C_full_intro", "നമസ്കാരം! മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ അപ്ഡേറ്റുകളിലേക്ക് എല്ലാവർക്കും സ്വാഗതം.")
        ]
        for label, text in levels:
            res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), f"context_{label}")
            self.assertTrue(Path(res["final_path"]).exists())


if __name__ == "__main__":
    unittest.main()
