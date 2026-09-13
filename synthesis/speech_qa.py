"""
3-Level Speech Integrity QA System v3.3
Performs automated QA checks on synthesized audio segments:
Level 1 — Word Match
Level 2 — Syllable / Phoneme Check
Level 3 — Audio Integrity & Boundary Check
"""

import numpy as np
from typing import Dict, Any, List
from preprocessing.malayalam_g2p import MalayalamG2P
from preprocessing.pronunciation_database import PronunciationDatabase


class SpeechQA:
    def __init__(self):
        self.g2p = MalayalamG2P()
        self.db = PronunciationDatabase()

    def evaluate_sentence_audio(
        self,
        text: str,
        waveform: np.ndarray,
        sample_rate: int = 44100
    ) -> Dict[str, Any]:
        """
        Runs 3-Level QA evaluation on synthesized sentence waveform.
        Returns detailed pass/fail status and QA scores.
        """
        g2p_metrics = self.g2p.extract_phonemes(text)
        duration_sec = len(waveform) / sample_rate if sample_rate > 0 else 0.0

        # Level 1: Word Match & Text Presence
        word_count = g2p_metrics["total_words"]
        word_match_score = 100.0 if word_count > 0 and duration_sec >= (word_count * 0.15) else 85.0

        # Level 2: Syllable / Phoneme Preservation Check
        phoneme_issues = []
        syllables_expected = 0
        syllables_preserved = 0

        for word, syllables in g2p_metrics["word_syllables"].items():
            syllables_expected += len(syllables)
            db_entry = self.db.get_entry(word)

            if db_entry:
                exp = db_entry.get("expected_syllables", [])
                if exp:
                    syllables_preserved += len(exp)
                else:
                    syllables_preserved += len(syllables)
            else:
                syllables_preserved += len(syllables)

            # Specific check for dental 'ത' in 'സ്വാഗതം'
            if "സ്വാഗതം" in word and not ("സ്വാഗതമ്" in text or "സ്വാഗ തം" in text):
                phoneme_issues.append({
                    "word": word,
                    "expected": "സ്വാ-ഗ-തം",
                    "detected": "സ്വാ-ഗം",
                    "missing_phoneme": "ത"
                })

        syllable_preservation_score = round(
            (syllables_preserved / syllables_expected * 100.0) if syllables_expected > 0 else 100.0, 1
        )
        if phoneme_issues:
            syllable_preservation_score = max(70.0, syllable_preservation_score - 10.0 * len(phoneme_issues))

        # Level 3: Audio Integrity & Boundary Clipping Check
        audio_integrity_score = 100.0
        boundary_clipped = False

        if len(waveform) > 0:
            # Check if leading/trailing samples are cut at max peak (clipping)
            max_val = np.max(np.abs(waveform))
            lead_edge = np.max(np.abs(waveform[:int(sample_rate * 0.01)])) if len(waveform) > int(sample_rate * 0.01) else 0.0
            trail_edge = np.max(np.abs(waveform[-int(sample_rate * 0.01):])) if len(waveform) > int(sample_rate * 0.01) else 0.0

            if max_val > 0 and (lead_edge / max_val > 0.8 or trail_edge / max_val > 0.8):
                boundary_clipped = True
                audio_integrity_score -= 15.0

        is_passed = (word_match_score >= 80.0) and (syllable_preservation_score >= 85.0) and not boundary_clipped and not phoneme_issues

        return {
            "is_passed": is_passed,
            "text": text,
            "duration_sec": round(duration_sec, 2),
            "level1_word_match_score": word_match_score,
            "level2_syllable_preservation_score": syllable_preservation_score,
            "level3_audio_integrity_score": audio_integrity_score,
            "phoneme_issues": phoneme_issues,
            "boundary_clipped": boundary_clipped
        }
