"""
Microsoft Edge TTS Engine Implementation for Malayalam
Provides broadcast studio quality Female (Sobhana) and Male (Midhun) Malayalam neural voices.
"""

import os
import sys
import asyncio
import tempfile
import numpy as np
from pathlib import Path
from typing import Tuple
from models.base_engine import BaseTTSEngine
from config import DEFAULT_SAMPLE_RATE

import soundfile as sf
import edge_tts
import edge_tts.communicate
import ssl
import socket
import aiohttp

# Disable SSL verification and force IPv4 for edge_tts aiohttp connection on Windows
ssl._create_default_https_context = ssl._create_unverified_context
if hasattr(edge_tts.communicate, '_SSL_CTX'):
    edge_tts.communicate._SSL_CTX.check_hostname = False
    edge_tts.communicate._SSL_CTX.verify_mode = ssl.CERT_NONE

_original_tcp_init = aiohttp.TCPConnector.__init__
def _patched_tcp_init(self, *args, **kwargs):
    kwargs['family'] = socket.AF_INET
    if hasattr(edge_tts.communicate, '_SSL_CTX'):
        kwargs['ssl'] = edge_tts.communicate._SSL_CTX
    else:
        kwargs['ssl'] = False
    _original_tcp_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = _patched_tcp_init


class EdgeTTSEngine(BaseTTSEngine):
    def __init__(self, voice_name: str = "ml-IN-SobhanaNeural", model_id: str = "edge_female"):
        super().__init__(model_id=model_id)
        self.voice_name = voice_name
        self.native_sample_rate = 24000

    def load_model(self):
        # Edge TTS does not require persistent heavy GPU weights loading
        self.is_loaded = True

    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        if not text or not text.strip():
            return np.zeros(0, dtype=np.float32), self.native_sample_rate

        # Calculate rate percentage string for edge_tts (e.g., "+8%", "-5%")
        rate_pct = int(round((speed - 1.0) * 100))
        rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

        # Pitch string for edge_tts (e.g., "+2Hz", "-2Hz")
        pitch_hz = int(round(pitch))
        pitch_str = f"{pitch_hz:+d}Hz" if pitch_hz != 0 else "+0Hz"

        async def _generate_audio():
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice_name,
                rate=rate_str,
                pitch=pitch_str
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            await communicate.save(tmp_path)
            return tmp_path

        # Run async generation in loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                tmp_audio_path = loop.run_until_complete(_generate_audio())
            else:
                tmp_audio_path = asyncio.run(_generate_audio())
        except Exception:
            tmp_audio_path = asyncio.run(_generate_audio())

        # Load generated mp3 into numpy float32 array
        waveform, sr = sf.read(tmp_audio_path, dtype='float32')
        
        # Convert stereo to mono if necessary
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)

        # Cleanup temp file
        try:
            os.remove(tmp_audio_path)
        except Exception:
            pass

        return waveform, sr
