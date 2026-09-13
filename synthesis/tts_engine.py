"""
Master Malayalam Voice Synthesis Engine v3.0 (Presenter Intelligence Pipeline)
Orchestrates Presenter Markup parsing, domain entity detection, contextual importance scoring,
syntactic phrase boundary parsing, segmented TTS synthesis, energy boost modulation,
audio post-processing mastering chain, and JSON metadata export.
"""

import sys
import time
import json
from pathlib import Path
import numpy as np
from typing import Tuple, Dict, Any, List
from preprocessing.text_processor import TextProcessor
from preprocessing.presenter_markup import PresenterMarkupParser, PresenterSegment
from preprocessing.prosody_planner import ProsodyPlanner
from models.model_loader import ModelLoader
from synthesis.audio_processor import AudioProcessor
from config import DEFAULT_SAMPLE_RATE, DEFAULT_MODEL_ID, SPEAKING_STYLES, OUTPUT_DIR


from synthesis.sentence_synthesizer import SentenceSynthesizer
from evaluation.qa_reporter import QAReporter


class MalayalamVoiceEngine:
    def __init__(self, default_model_key: str = DEFAULT_MODEL_ID, custom_dict_path: str = None):
        self.text_processor = TextProcessor(custom_dict_path)
        self.markup_parser = PresenterMarkupParser()
        self.prosody_planner = ProsodyPlanner()
        self.model_loader = ModelLoader()
        self.audio_processor = AudioProcessor(target_sample_rate=DEFAULT_SAMPLE_RATE)
        self.current_model_key = default_model_key
        self.qa_reporter = QAReporter()

    def generate(
        self,
        text: str,
        output_filepath: str = None,
        style: str = "movie_news",
        speed: float = 1.0,
        pitch: float = 0.0,
        model_key: str = None,
        overrides: Any = None,
        output_format: str = "wav"
    ) -> Dict[str, Any]:
        """Synthesizes raw text or marked-up text into high-quality Malayalam audio."""
        if overrides:
            self.text_processor.pronunciation_dict.apply_overrides(overrides)

        if "<" in text and ">" in text:
            return self.generate_from_markup(
                markup_text=text,
                output_filepath=output_filepath,
                model_key=model_key,
                overrides=overrides,
                output_format=output_format
            )

        start_time = time.time()
        active_model_key = model_key or self.current_model_key

        # Step 1: Preprocess Text
        preprocessed_text = self.text_processor.process(text)

        # Step 2: Apply Style Preset Parameters
        style_preset = SPEAKING_STYLES.get(style, SPEAKING_STYLES["movie_news"])
        effective_speed = speed * style_preset.get("speed", 1.0)
        effective_pitch = pitch + style_preset.get("pitch_shift", 0.0)

        # Step 3: Load Model Engine & Synthesize
        engine = self.model_loader.get_engine(active_model_key)
        raw_waveform, native_sr = engine.synthesize(
            text=preprocessed_text,
            speed=effective_speed,
            pitch=effective_pitch
        )

        # Step 4: Audio Post-Processing (Mastering Chain: High-Pass Filter + Compression + LUFS Norm + Limiter)
        processed_waveform = self.audio_processor.process_mastering_chain(
            waveform=raw_waveform,
            orig_sample_rate=native_sr
        )

        # Step 5: Save Audio Output
        if not output_filepath:
            timestamp = int(time.time() * 1000)
            output_filepath = str(OUTPUT_DIR / f"malayalam_voice_{timestamp}.{output_format}")

        saved_path = self.audio_processor.save_audio(
            waveform=processed_waveform,
            output_filepath=output_filepath,
            format=output_format
        )

        elapsed = time.time() - start_time

        return {
            "audio_path": saved_path,
            "waveform": processed_waveform,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "original_text": text,
            "preprocessed_text": preprocessed_text,
            "generation_time": round(elapsed, 3),
            "model_used": active_model_key,
            "style_used": style
        }

    def generate_from_markup(
        self,
        markup_text: str,
        output_filepath: str = None,
        model_key: str = None,
        overrides: Any = None,
        output_format: str = "wav"
    ) -> Dict[str, Any]:
        """
        Runs Presenter Engine v3.3 Pipeline:
        1. Parses XML Presenter Markup.
        2. Applies Pronunciation Overrides.
        3. Pre-scans Malayalam text for speech integrity.
        4. Synthesizes sentence-by-sentence with per-sentence 3-Level Speech QA retry verification.
        5. Applies 5-stage studio audio mastering chain (-16 LUFS, -1 dBFS True Peak).
        6. Saves WAV and exports matching metadata JSON and Voice QA Report Card.
        """
        start_time = time.time()
        active_model_key = model_key or self.current_model_key
        engine = self.model_loader.get_engine(active_model_key)
        sentence_synth = SentenceSynthesizer(engine, self.audio_processor)

        if overrides:
            self.text_processor.pronunciation_dict.apply_overrides(overrides)

        segments: List[PresenterSegment] = self.markup_parser.parse(markup_text)

        combined_waveforms = []
        preprocessed_segments_text = []
        full_script_metadata = []
        sentence_qa_results = []

        for idx, seg in enumerate(segments, 1):
            if not seg.text:
                continue

            # Run Presenter Intelligence Prosody Planner on segment text
            seg_metadata = self.prosody_planner.plan_sentence_prosody(
                text=seg.text,
                tag_name=seg.tag,
                sentence_id=idx
            )
            full_script_metadata.append(seg_metadata)

            effective_speed = seg_metadata["speed"]
            energy_boost_db = seg_metadata["energy_boost_db"]
            pause_after_ms = seg_metadata["pause_after"]

            print(f"[*] Synthesizing Segment {idx}/{len(segments)} [{seg.tag.upper()}] (importance={seg_metadata['importance']}, speed={effective_speed}, boost={energy_boost_db}dB)...")
            sys.stdout.flush()

            # Preprocess segment text
            norm_text = self.text_processor.process(seg.text)
            preprocessed_segments_text.append(f"[{seg.tag.upper()}] {norm_text}")

            # Synthesize segment with sentence-by-sentence QA retry loop
            padded_seg, qa_res = sentence_synth.synthesize_sentence_with_qa(
                text=norm_text,
                speed=effective_speed,
                pitch=seg.pitch_shift
            )
            sentence_qa_results.append(qa_res)

            # Apply Energy Boost if segment contains key entities/announcements
            if energy_boost_db > 0.0:
                padded_seg = self.audio_processor.apply_gain(padded_seg, gain_db=energy_boost_db)

            # Calculate exact sentence segment duration including trailing pause
            pause_samples = int(DEFAULT_SAMPLE_RATE * (pause_after_ms / 1000.0))
            seg_duration_sec = (len(padded_seg) + pause_samples) / DEFAULT_SAMPLE_RATE
            seg_metadata["duration"] = round(seg_duration_sec, 3)

            combined_waveforms.append(padded_seg)
            if pause_samples > 0:
                combined_waveforms.append(np.zeros(pause_samples, dtype=np.float32))

        if not combined_waveforms:
            master_raw = np.zeros(0, dtype=np.float32)
        else:
            master_raw = np.concatenate(combined_waveforms)

        # Apply Studio Mastering Chain (Filter -> Compression -> LUFS -16 -> Limiter -1 dBFS)
        mastered_waveform = self.audio_processor.process_mastering_chain(
            waveform=master_raw,
            orig_sample_rate=DEFAULT_SAMPLE_RATE
        )

        if not output_filepath:
            timestamp = int(time.time() * 1000)
            output_filepath = str(OUTPUT_DIR / f"malayalam_presenter_markup_{timestamp}.{output_format}")

        saved_path = self.audio_processor.save_audio(
            waveform=mastered_waveform,
            output_filepath=output_filepath,
            format=output_format
        )

        # Generate Voice QA Report Card
        qa_json_path = str(Path(saved_path).with_name(f"{Path(saved_path).stem}_qa_report.json"))
        report_card = self.qa_reporter.generate_report(sentence_qa_results, qa_json_path)

        # Save Metadata JSON alongside WAV
        json_path = str(Path(saved_path).with_suffix('.json'))
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "presenter_version": "3.3",
                "audio_path": saved_path,
                "qa_report_path": qa_json_path,
                "overall_quality_score": report_card["overall_quality_score"],
                "total_segments": len(segments),
                "script_metadata": full_script_metadata
            }, f, ensure_ascii=False, indent=2)

        elapsed = time.time() - start_time
        full_preprocessed_preview = "\n\n".join(preprocessed_segments_text)

        return {
            "audio_path": saved_path,
            "metadata_path": json_path,
            "qa_report_path": qa_json_path,
            "report_card": report_card,
            "waveform": mastered_waveform,
            "sample_rate": DEFAULT_SAMPLE_RATE,
            "original_text": markup_text,
            "preprocessed_text": full_preprocessed_preview,
            "generation_time": round(elapsed, 3),
            "model_used": active_model_key,
            "segments_count": len(segments),
            "script_metadata": full_script_metadata
        }

    def generate_diagnostic_triplet(
        self,
        text: str,
        output_dir: str,
        label: str
    ) -> Dict[str, str]:
        """
        Diagnostic helper producing 3 separate comparison files for phonetic inspection:
        01_raw_tts.wav      -> Direct raw output from TTS model (native 16kHz)
        02_processed.wav    -> Resampled to 44.1kHz with 120ms/200ms padding, no mastering
        03_final.wav        -> Globally mastered audio (-16 LUFS, -1 dBFS peak ceiling)
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        norm_text = self.text_processor.process(text)
        engine = self.model_loader.get_engine(self.current_model_key)

        # 01_raw_tts.wav
        raw_wave, native_sr = engine.synthesize(text=norm_text, speed=1.0)
        raw_path = str(out_path / f"{label}_01_raw_tts.wav")
        self.audio_processor.save_audio(raw_wave, raw_path, format="wav")

        # 02_processed.wav (resampled + padded)
        resampled_wave = self.audio_processor.resample(raw_wave, native_sr)
        padded_wave = self.audio_processor.add_padding(resampled_wave, leading_ms=120.0, trailing_ms=200.0)
        processed_path = str(out_path / f"{label}_02_processed.wav")
        self.audio_processor.save_audio(padded_wave, processed_path, format="wav")

        # 03_final.wav (globally mastered single track)
        final_wave = self.audio_processor.process_mastering_chain(padded_wave, DEFAULT_SAMPLE_RATE)
        final_path = str(out_path / f"{label}_03_final.wav")
        self.audio_processor.save_audio(final_wave, final_path, format="wav")

        return {
            "label": label,
            "raw_tts_path": raw_path,
            "processed_path": processed_path,
            "final_path": final_path
        }
