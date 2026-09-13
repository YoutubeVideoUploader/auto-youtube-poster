"""
Benchmark Test Suite Runner for Malayalam Voice Engine
Executes test cases across all 18 categories and saves audio clips.
"""

import sys
import json
import time
from pathlib import Path

# Force UTF-8 encoding on stdout for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from synthesis.tts_engine import MalayalamVoiceEngine
from config import TEST_OUTPUT_DIR


def run_benchmark_tests(model_key: str = "mms_malayalam"):
    print("=" * 70)
    print(f"[*] Starting Benchmark Suite Execution (Model: {model_key})")
    print("=" * 70)

    corpus_path = BASE_DIR / "tests" / "test_corpus.json"
    if not corpus_path.exists():
        print(f"[!] Test corpus not found at '{corpus_path}'")
        return

    with open(corpus_path, "r", encoding="utf-8") as f:
        test_corpus = json.load(f)

    engine = MalayalamVoiceEngine(default_model_key=model_key)
    
    results = []

    for category, sentences in test_corpus.items():
        print(f"\n--- Category: {category} ({len(sentences)} sentences) ---")
        category_dir = TEST_OUTPUT_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        for idx, sentence in enumerate(sentences, 1):
            out_file = str(category_dir / f"test_{idx}.wav")
            print(f"  [{idx}] Original: {sentence}")
            
            res = engine.generate(
                text=sentence,
                output_filepath=out_file,
                style="movie_news",
                model_key=model_key
            )

            print(f"      Preprocessed : {res['preprocessed_text']}")
            print(f"      Time taken   : {res['generation_time']} sec")
            print(f"      Saved to     : {res['audio_path']}")

            results.append({
                "category": category,
                "sentence_idx": idx,
                "original": sentence,
                "preprocessed": res['preprocessed_text'],
                "generation_time": res['generation_time'],
                "audio_path": res['audio_path']
            })

    print("\n" + "=" * 70)
    print(f"[+] Successfully generated audio for all {len(results)} test cases.")
    print(f"[+] Audio clips saved in: {TEST_OUTPUT_DIR}")
    print("=" * 70)
    return results


if __name__ == "__main__":
    run_benchmark_tests()
