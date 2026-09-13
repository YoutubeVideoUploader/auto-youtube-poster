"""
Audio Engineering Audit Script for v2.1 Presenter Audio
Calculates:
- Total Duration (sec)
- Total Silence Duration (sec) & Silence Percentage (%)
- Pause Count & Average Pause Duration
- Speech Chunks Count & Average Speech Chunk Duration
- True Peak Level (dBFS)
- RMS Level & Estimated LUFS
"""

import sys
import numpy as np
import soundfile as sf
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def audit_audio(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found at {file_path}")
        return

    data, sr = sf.read(str(path))
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    total_duration = len(data) / sr

    # True Peak
    max_val = np.max(np.abs(data))
    true_peak_dbfs = 20 * np.log10(max_val) if max_val > 0 else -100.0

    # RMS & Approx LUFS
    rms = np.sqrt(np.mean(data**2))
    rms_db = 20 * np.log10(rms) if rms > 0 else -100.0
    approx_lufs = rms_db - 3.0  # rough estimate for continuous speech

    # Detect Silences (threshold -40 dBFS, minimum duration 100ms)
    amplitude_threshold = 10**( -40 / 20 )
    is_silent = np.abs(data) < amplitude_threshold

    # Group frame silences into chunks
    min_silence_samples = int(sr * 0.10) # 100ms
    silence_segments = []
    current_start = None

    for i, silent in enumerate(is_silent):
        if silent and current_start is None:
            current_start = i
        elif not silent and current_start is not None:
            silence_len = i - current_start
            if silence_len >= min_silence_samples:
                silence_segments.append((current_start / sr, i / sr, silence_len / sr))
            current_start = None

    if current_start is not None:
        silence_len = len(is_silent) - current_start
        if silence_len >= min_silence_samples:
            silence_segments.append((current_start / sr, len(is_silent) / sr, silence_len / sr))

    total_silence_sec = sum(seg[2] for seg in silence_segments)
    silence_percent = (total_silence_sec / total_duration) * 100.0 if total_duration > 0 else 0.0
    pause_count = len(silence_segments)
    avg_pause_duration = (total_silence_sec / pause_count) if pause_count > 0 else 0.0

    # Speech Chunks
    total_speech_sec = total_duration - total_silence_sec
    speech_chunks_count = pause_count + 1
    avg_speech_chunk_duration = total_speech_sec / speech_chunks_count if speech_chunks_count > 0 else 0.0

    print("=" * 65)
    print(f"📊 AUDIO ENGINEERING AUDIT REPORT: {path.name}")
    print("=" * 65)
    print(f"⏱️ Total Runtime           : {total_duration:.2f} seconds ({total_duration/60:.2f} min)")
    print(f"🔊 True Peak Level        : {true_peak_dbfs:.2f} dBFS")
    print(f"🎚️ Approx Integrated RMS  : {rms_db:.2f} dB (Est. LUFS: {approx_lufs:.2f})")
    print(f"⏸️ Pause Count (>100ms)   : {pause_count}")
    print(f"⌛ Total Silence Duration  : {total_silence_sec:.2f} seconds")
    print(f"📉 Silence Percentage     : {silence_percent:.2f}%")
    print(f"⏱️ Avg Pause Duration      : {avg_pause_duration*1000:.1f} ms")
    print(f"🗣️ Avg Speech Burst Len   : {avg_speech_chunk_duration:.2f} seconds")
    print("=" * 65)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "outputs/Malayalam_Movie_News_Presenter_v2.1.wav"
    audit_audio(target)
