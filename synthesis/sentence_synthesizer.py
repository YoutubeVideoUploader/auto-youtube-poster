"""
Sentence-by-Sentence Synthesizer & QA Retry Pipeline v3.3
Synthesizes audio sentence-by-sentence with per-sentence Speech QA verification.
If a sentence fails QA, it automatically regenerates only that sentence using phonetic consonant anchors.
"""

import sys
import numpy as np
from typing import Dict, Any, List, Tuple
from synthesis.speech_qa import SpeechQA
from preprocessing.pronunciation_database import PronunciationDatabase
from preprocessing.speech_integrity import SpeechIntegrityChecker


class SentenceSynthesizer:
    def __init__(self, tts_engine, audio_processor):
        self.engine = tts_engine
        self.audio_processor = audio_processor
        self.qa = SpeechQA()
        self.db = PronunciationDatabase()
        self.integrity_checker = SpeechIntegrityChecker()

    def synthesize_sentence_with_qa(
        self,
        text: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        max_retries: int = 2
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Synthesizes a single sentence with per-sentence QA evaluation and automatic retry logic.
        """
        current_text = text
        attempts = 0
        last_qa_result = None
        final_waveform = np.zeros(0, dtype=np.float32)

        while attempts < max_retries:
            attempts += 1

            # 1. Synthesize sentence with steady natural flow
            raw_wave, native_sr = self.engine.synthesize(text=current_text, speed=speed, pitch=pitch)
            resampled_wave = self.audio_processor.resample(raw_wave, native_sr)
            padded_wave = self.audio_processor.add_padding(resampled_wave, leading_ms=30.0, trailing_ms=60.0)

            # 2. Run 3-Level Speech QA Check
            qa_res = self.qa.evaluate_sentence_audio(text=text, waveform=padded_wave)
            qa_res["attempt"] = attempts
            last_qa_result = qa_res

            if qa_res["is_passed"]:
                final_waveform = padded_wave
                break
            else:
                print(f"[!] QA Retry Attempt {attempts} for sentence: '{text}' (Issues: {qa_res['phoneme_issues']})")
                sys.stdout.flush()
                # Apply explicit phonetic anchor for retry
                current_text = self.integrity_checker.validate_and_anchor_phonemes(text)

        if len(final_waveform) == 0:
            # Fallback to last synthesized padded wave
            raw_wave, native_sr = self.engine.synthesize(text=current_text, speed=speed, pitch=pitch)
            resampled_wave = self.audio_processor.resample(raw_wave, native_sr)
            final_waveform = self.audio_processor.add_padding(resampled_wave, leading_ms=30.0, trailing_ms=60.0)

        return final_waveform, last_qa_result
