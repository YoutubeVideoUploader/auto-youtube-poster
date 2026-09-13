"""
Coqui XTTS v2 Zero-Shot Voice Cloning Model Engine
Clones voice timbre, tone, warmth, and accent from a reference speaker audio sample.
"""

import os
import sys
import ssl
import time
import urllib3
import torch
import numpy as np
from typing import Tuple, Optional
from pathlib import Path

# SSL & TOS Agreement setup
os.environ["HF_HUB_DISABLE_SSL_VERIFICATION"] = "1"
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    old_merge = requests.Session.merge_environment_settings
    def merge_env_settings(self, url, proxies, stream, verify, cert):
        return old_merge(self, url, proxies, stream, False, cert)
    requests.Session.merge_environment_settings = merge_env_settings
except Exception:
    pass

# Patch transformers.pytorch_utils for TTS compatibility with newer transformers
try:
    import transformers.pytorch_utils
    if not hasattr(transformers.pytorch_utils, 'isin_mps_friendly'):
        def isin_mps_friendly(elements, test_elements):
            return (elements.unsqueeze(-1) == test_elements).any(-1)
        transformers.pytorch_utils.isin_mps_friendly = isin_mps_friendly
except Exception:
    pass

from models.base_engine import BaseTTSEngine
from config import BASE_DIR, DEFAULT_SAMPLE_RATE


class XTTSEngine(BaseTTSEngine):
    def __init__(
        self,
        model_id: str = "xtts_v2",
        reference_wav: str = None
    ):
        super().__init__(model_id=model_id)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.native_sample_rate = 24000
        
        default_ref = BASE_DIR / "voices" / "reference_voices" / "presenter_cloning_sample.wav"
        self.reference_wav = reference_wav if reference_wav else str(default_ref)

    def load_model(self):
        if self.is_loaded:
            return

        print(f"[*] Loading Coqui XTTS v2 Zero-Shot Voice Cloning Engine on {self.device}...")
        t0 = time.time()
        from TTS.api import TTS
        self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(self.device)
        self.is_loaded = True
        print(f"[+] Coqui XTTS v2 loaded successfully in {time.time() - t0:.2f} seconds.")

    def set_reference_wav(self, wav_path: str):
        """Updates the reference speaker audio WAV file path."""
        if Path(wav_path).exists():
            self.reference_wav = str(Path(wav_path).resolve())
            print(f"[+] Updated voice cloning reference audio to: {self.reference_wav}")

    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        if not self.is_loaded:
            self.load_model()

        if not text or not text.strip():
            return np.zeros(0, dtype=np.float32), self.native_sample_rate

        if not self.reference_wav or not Path(self.reference_wav).exists():
            raise FileNotFoundError(f"Reference audio file not found at: {self.reference_wav}")

        # Generate voice-cloned speech audio waveform
        out_wav = self.tts.tts(
            text=text,
            speaker_wav=self.reference_wav,
            language="hi",
            speed=float(speed)
        )

        waveform = np.array(out_wav, dtype=np.float32)
        return waveform, self.native_sample_rate
