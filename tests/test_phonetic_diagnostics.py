"""
Comprehensive Malayalam Phonetic Diagnostic Suite v3.1 (DRY + COMPLETE SPEECH)
Synthesizes 10 strict Malayalam phonetic categories and generates 3 comparison files for each:
01_raw_tts.wav   -> Native model output (16kHz)
02_processed.wav -> Resampled to 44.1kHz with 120ms/200ms padding, no mastering
03_final.wav     -> Globally mastered single-track audio (-16 LUFS, -1 dBFS ceiling)
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from synthesis.tts_engine import MalayalamVoiceEngine
from config import OUTPUT_DIR

DIAGNOSTIC_CATEGORIES = [
    ("01_short_words", "ആശ, മേള, ഒ.ടി.ടി, ഹിറ്റ്."),
    ("02_words_ending_consonants", "മോഹൻലാൽ, സംവൃത സുനിൽ, സഫർ സനൽ, ഇൻസ്റ്റാഗ്രാം."),
    ("03_words_with_zha", "കിഴക്ക്, മഴ, വഴിയമ്പലം, അഴക്."),
    ("04_words_with_la", "കേരളം, ലളിതം, ആളുകൾ, മേള."),
    ("05_words_with_na", "ഗുണം, കഷണം, പ്രമാണം, കാരണം."),
    ("06_koottaksharam", "പ്രഖ്യാപിച്ചു, ശ്രമിക്കുന്ന, അൺസെർട്ടന്റി, പ്രത്യേകം."),
    ("07_long_malayalam_words", "അഭിനയിച്ചിരുന്നതിനെക്കുറിച്ച്, പശ്ചാത്തലത്തിലൊരുങ്ങുന്ന, പ്രതികരണമാണ്."),
    ("08_actor_names", "മോഹൻലാൽ, മമ്മൂട്ടി, ദുൽഖർ സൽമാൻ, ഫഹദ് ഫാസിൽ, ടൊവിനോ തോമസ്."),
    ("09_movie_names", "ഏകദേശം ദി അൺസെർട്ടന്റി പ്രിൻസിപ്പിൾ, ഡോണ്ട് ട്രബിൾ ദി ട്രബിൾ, L370."),
    ("10_mixed_english_combination", "Netflix-ൽ സെപ്റ്റംബർ 20-ന് OTT റിലീസ് ഉണ്ടാകും.")
]


def run_phonetic_diagnostics():
    print("=" * 75)
    print("🧪 RUNNING MALAYALAM PHONETIC DIAGNOSTIC SUITE v3.1 (DRY + COMPLETE SPEECH)")
    print("=" * 75)
    sys.stdout.flush()

    engine = MalayalamVoiceEngine(default_model_key="mms_malayalam")
    diag_dir = OUTPUT_DIR / "diagnostics_v3.1"
    diag_dir.mkdir(parents=True, exist_ok=True)

    summary_results = []

    for label, text in DIAGNOSTIC_CATEGORIES:
        print(f"[*] Processing Category: [{label}] ...")
        sys.stdout.flush()

        res = engine.generate_diagnostic_triplet(
            text=text,
            output_dir=str(diag_dir),
            label=label
        )
        summary_results.append((label, text, res))

    print("\n" + "=" * 75)
    print("🎉 PHONETIC DIAGNOSTIC TRIPLETS CREATED SUCCESSFULLY!")
    print(f"📁 Diagnostic Output Folder: {diag_dir}")
    print("=" * 75)
    for label, text, res in summary_results:
        print(f"\nCategory: {label}")
        print(f"  Input Text  : {text}")
        print(f"  01_raw_tts  : {res['raw_tts_path']}")
        print(f"  02_processed: {res['processed_path']}")
        print(f"  03_final    : {res['final_path']}")
    print("=" * 75)


if __name__ == "__main__":
    run_phonetic_diagnostics()
