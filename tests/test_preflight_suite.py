"""
Mandatory Pre-Flight Test Suite v3.3
Verifies pre-flight sentences and confusable consonant pair single-word tests before full production runs.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from synthesis.tts_engine import MalayalamVoiceEngine
from config import OUTPUT_DIR

PREFLIGHT_SENTENCES = [
    ("pf_sent_1", "എല്ലാവർക്കും സ്വാഗതം."),
    ("pf_sent_2", "മലയാള സിനിമയിലെ ഏറ്റവും പുതിയ വാർത്തകളിലേക്ക് സ്വാഗതം."),
    ("pf_sent_3", "ഇന്നത്തെ പ്രധാന വാർത്ത ഇതാണ്."),
    ("pf_sent_4", "ചിത്രത്തിന്റെ റിലീസ് തീയതി സെപ്റ്റംബർ ഇരുപത് ആണ്."),
    ("pf_sent_5", "പുതിയ അപ്ഡേറ്റുകൾ ഉടൻ തന്നെ നിങ്ങളിലേക്ക് എത്തും.")
]

CONFUSABLE_WORD_TESTS = [
    ("pf_tha_ta", "തുടക്കം, തീയതി, കൂടുതൽ, മാത്രം, പുതിയത്."),
    ("pf_na_nna", "നടി, കണ്ണൻ, പണം, മണിക്കൂർ."),
    ("pf_la_lla_zha", "ലോകം, വെള്ളം, മലയാളം, പഴയ."),
    ("pf_ra_rra", "രാജു, റിലീസ്, പുതിയ.")
]


class TestPreFlightSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = MalayalamVoiceEngine(default_model_key="mms_malayalam")
        cls.out_dir = OUTPUT_DIR / "preflight_suite_v3.3"
        cls.out_dir.mkdir(parents=True, exist_ok=True)

    def test_preflight_sentences(self):
        """Runs the 5 mandatory pre-flight sentences"""
        for label, text in PREFLIGHT_SENTENCES:
            res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), label)
            self.assertTrue(Path(res["final_path"]).exists(), f"Failed pre-flight sentence: {text}")

    def test_confusable_consonant_pairs(self):
        """Runs targeted single-word tests for confusable pairs (ത/ട, ന/ണ, ല/ള/ഴ, ര/റ)"""
        for label, text in CONFUSABLE_WORD_TESTS:
            res = self.engine.generate_diagnostic_triplet(text, str(self.out_dir), label)
            self.assertTrue(Path(res["final_path"]).exists(), f"Failed confusable pair test: {text}")


def run_preflight_suite_cli() -> bool:
    """CLI runner function for pre-flight validation check."""
    print("=" * 70)
    print("🧪 RUNNING MANDATORY PRE-FLIGHT TEST SUITE v3.3")
    print("=" * 70)
    sys.stdout.flush()

    engine = MalayalamVoiceEngine(default_model_key="mms_malayalam")
    out_dir = OUTPUT_DIR / "preflight_suite_v3.3"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_passed = True
    for label, text in PREFLIGHT_SENTENCES + CONFUSABLE_WORD_TESTS:
        print(f"[*] Pre-flight Testing: [{label}] '{text}'...")
        sys.stdout.flush()
        try:
            res = engine.generate_diagnostic_triplet(text, str(out_dir), label)
            if not Path(res["final_path"]).exists():
                all_passed = False
                print(f"[❌ FAIL] Pre-flight failed for: {text}")
        except Exception as e:
            all_passed = False
            print(f"[❌ ERROR] Pre-flight error for '{text}': {e}")

    if all_passed:
        print("=" * 70)
        print("✅ ALL MANDATORY PRE-FLIGHT TESTS PASSED! PROCEEDING TO PRODUCTION.")
        print("=" * 70)
    else:
        print("=" * 70)
        print("❌ PRE-FLIGHT TEST SUITE FAILED! FULL SCRIPT GENERATION BLOCKED.")
        print("=" * 70)

    return all_passed


if __name__ == "__main__":
    unittest.main()
