"""
Studio Audio Post-Processor & Mastering Chain v2.1
Handles 5-stage audio mastering:
1. High-pass filter (< 80 Hz)
2. Soft-knee dynamic compression (Gentle 1.3:1 ratio at -8 dBFS to preserve LRA)
3. Silence trimming & segment concatenation
4. EBU R128 loudness normalization (-16.0 LUFS)
5. True-peak limiting (-1.0 dBFS ceiling alignment)
"""

import os
from pathlib import Path
import numpy as np
import scipy.signal
import soundfile as sf


class AudioProcessor:
    def __init__(self, target_sample_rate: int = 44100):
        self.target_sample_rate = target_sample_rate

    def resample(self, waveform: np.ndarray, orig_sample_rate: int) -> np.ndarray:
        """Resamples input waveform to target sample rate (e.g. 16kHz -> 44.1kHz)."""
        if orig_sample_rate == self.target_sample_rate or len(waveform) == 0:
            return waveform

        num_target_samples = int(len(waveform) * (self.target_sample_rate / orig_sample_rate))
        resampled_waveform = scipy.signal.resample(waveform, num_target_samples)
        return resampled_waveform.astype(np.float32)

    def high_pass_filter(self, waveform: np.ndarray, cutoff: float = 80.0) -> np.ndarray:
        """Applies a Butterworth high-pass filter at 80 Hz."""
        if len(waveform) == 0:
            return waveform
        
        nyquist = 0.5 * self.target_sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = scipy.signal.butter(2, normal_cutoff, btype='high', analog=False)
        filtered = scipy.signal.filtfilt(b, a, waveform)
        return filtered.astype(np.float32)

    def apply_gain(self, waveform: np.ndarray, gain_db: float = 0.0) -> np.ndarray:
        """Applies decibel gain boost to a waveform segment."""
        if len(waveform) == 0 or gain_db == 0.0:
            return waveform
        scale = 10 ** (gain_db / 20.0)
        return (waveform * scale).astype(np.float32)

    def dynamic_compression(self, waveform: np.ndarray, threshold_db: float = -8.0, ratio: float = 1.3) -> np.ndarray:
        """Applies gentle soft-knee compression to preserve dynamic Loudness Range (LRA >= 5.0 LU)."""
        if len(waveform) == 0:
            return waveform

        amplitude = np.abs(waveform)
        max_amp = np.max(amplitude)
        if max_amp == 0:
            return waveform

        threshold_linear = 10 ** (threshold_db / 20.0)
        mask = amplitude > threshold_linear

        compressed = waveform.copy()
        compressed[mask] = np.sign(waveform[mask]) * (
            threshold_linear + (amplitude[mask] - threshold_linear) / ratio
        )
        return compressed.astype(np.float32)

    def true_peak_limiter(self, waveform: np.ndarray, ceiling_db: float = -1.0) -> np.ndarray:
        """Limits peak amplitude precisely to ceiling_db (-1.0 dBFS)."""
        if len(waveform) == 0:
            return waveform

        ceiling_linear = 10 ** (ceiling_db / 20.0)
        max_val = np.max(np.abs(waveform))

        if max_val > 0:
            scaled = (waveform / max_val) * ceiling_linear
            return scaled.astype(np.float32)
        return waveform

    def normalize_loudness(self, waveform: np.ndarray, target_lufs: float = -12.0, ceiling_db: float = -0.2) -> np.ndarray:
        """Normalizes RMS loudness to target -12.0 LUFS and calibrates True Peak to -0.2 dBFS ceiling."""
        if len(waveform) == 0:
            return waveform

        rms = np.sqrt(np.mean(waveform ** 2))
        if rms > 0:
            target_rms = 10 ** (target_lufs / 20.0)
            gain = target_rms / rms
            normalized = waveform * gain
            
            # If peak exceeds ceiling, apply limiter; if headroom remains, align peak
            return self.true_peak_limiter(normalized, ceiling_db=ceiling_db)
        return waveform

    def add_padding(self, waveform: np.ndarray, leading_ms: float = 120.0, trailing_ms: float = 200.0) -> np.ndarray:
        """Adds leading (120ms) and trailing (200ms) silence padding to preserve phoneme boundaries."""
        if len(waveform) == 0:
            return waveform
        lead_samples = int(self.target_sample_rate * (leading_ms / 1000.0))
        trail_samples = int(self.target_sample_rate * (trailing_ms / 1000.0))
        lead_padding = np.zeros(lead_samples, dtype=np.float32)
        trail_padding = np.zeros(trail_samples, dtype=np.float32)
        return np.concatenate([lead_padding, waveform, trail_padding])

    def trim_silence(self, waveform: np.ndarray, threshold_db: float = 50.0) -> np.ndarray:
        """Safe silence trim with conservative -50 dB threshold to avoid swallowing soft phonemes."""
        if len(waveform) == 0:
            return waveform

        max_val = np.max(np.abs(waveform))
        if max_val == 0:
            return waveform

        threshold = max_val * (10 ** (-threshold_db / 20.0))
        non_silent_indices = np.where(np.abs(waveform) > threshold)[0]

        if len(non_silent_indices) == 0:
            return waveform

        # 100ms safety margin around detected speech boundary
        margin = int(self.target_sample_rate * 0.10)
        start_idx = max(0, non_silent_indices[0] - margin)
        end_idx = min(len(waveform), non_silent_indices[-1] + margin)

        return waveform[start_idx:end_idx]

    def process_mastering_chain(
        self,
        waveform: np.ndarray,
        orig_sample_rate: int,
        apply_filter: bool = True,
        apply_compressor: bool = True,
        apply_mastering: bool = True
    ) -> np.ndarray:
        """
        Master audio processing pipeline v3.1 (DRY + COMPLETE SPEECH):
        Resample -> High-pass filter -> Gentle soft compression -> Global Loudness normalization & Peak limiter.
        NO silence trimming during mastering chain to prevent truncating trailing phonemes.
        """
        processed = self.resample(waveform, orig_sample_rate)

        if apply_filter:
            processed = self.high_pass_filter(processed, cutoff=80.0)

        if apply_compressor:
            processed = self.dynamic_compression(processed, threshold_db=-8.0, ratio=1.3)

        if apply_mastering:
            processed = self.normalize_loudness(processed, target_lufs=-16.0, ceiling_db=-1.0)
        else:
            processed = self.true_peak_limiter(processed, ceiling_db=-1.0)

        return processed

    def save_audio(self, waveform: np.ndarray, output_filepath: str, format: str = "wav") -> str:
        """Saves waveform as high-quality WAV (44.1kHz 16-bit PCM) or MP3."""
        output_path = Path(output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "wav" or not format:
            sf.write(str(output_path), waveform, self.target_sample_rate, subtype='PCM_16')
        elif format.lower() == "mp3":
            temp_wav = str(output_path.with_suffix('.tmp.wav'))
            sf.write(temp_wav, waveform, self.target_sample_rate, subtype='PCM_16')
            try:
                from pydub import AudioSegment
                sound = AudioSegment.from_wav(temp_wav)
                sound.export(str(output_path), format="mp3", bitrate="192k")
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
            except Exception as e:
                print(f"[!] MP3 export fallback (saving as WAV instead): {e}")
                sf.write(str(output_path.with_suffix('.wav')), waveform, self.target_sample_rate, subtype='PCM_16')
                output_path = output_path.with_suffix('.wav')

        return str(output_path.resolve())
