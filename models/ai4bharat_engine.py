"""
AI4Bharat IndicTTS / Indic-VITS Engine Implementation
Provides multi-speaker support for Indic languages including Malayalam.
"""

import os
import sys
import ssl
import time
import urllib3
import torch
import numpy as np
from typing import Tuple
from transformers import AutoModel, AutoTokenizer

# Disable SSL verification for Hugging Face hub downloads on Windows if local certs fail
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["PYTHONHTTPSVERIFY"] = "0"
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    # Patch requests Session verify default
    old_merge_environment_settings = requests.Session.merge_environment_settings
    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        return old_merge_environment_settings(self, url, proxies, stream, False, cert)
    requests.Session.merge_environment_settings = merge_environment_settings
except Exception:
    pass
from models.base_engine import BaseTTSEngine


class AI4BharatTTSEngine(BaseTTSEngine):
    def __init__(self, model_repo: str = "ai4bharat/vits_rasa_13"):
        super().__init__(model_id="ai4bharat_indic")
        self.model_repo = model_repo
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.native_sample_rate = 22050

    def load_model(self):
        if self.is_loaded:
            return

        print(f"[*] Loading AI4Bharat IndicTTS from '{self.model_repo}' on device: {self.device}...")
        t0 = time.time()
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_repo, trust_remote_code=True)
            self.model = AutoModel.from_pretrained(self.model_repo, trust_remote_code=True).to(self.device)
            self.model.eval()
            self.is_loaded = True
            print(f"[+] AI4Bharat Model loaded successfully in {time.time() - t0:.2f} seconds.")
        except Exception as e:
            print(f"[!] Primary AI4Bharat model load fallback: {e}")
            # Fallback to MMS model if AI4Bharat weights unavailable or custom code restricted
            from models.mms_engine import MMSTTSEngine
            fallback = MMSTTSEngine()
            fallback.load_model()
            self.tokenizer = fallback.tokenizer
            self.model = fallback.model
            self.native_sample_rate = fallback.native_sample_rate
            self.is_loaded = True

    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        if not self.is_loaded:
            self.load_model()

        if not text or not text.strip():
            return np.zeros(0, dtype=np.float32), self.native_sample_rate

        try:
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            with torch.no_grad():
                output = self.model(**inputs)
                if hasattr(output, 'waveform'):
                    waveform = output.waveform[0].cpu().numpy().astype(np.float32)
                else:
                    waveform = output[0].cpu().numpy().astype(np.float32)
        except Exception:
            # Safe execution fallback
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            with torch.no_grad():
                output = self.model(**inputs)
                waveform = output.waveform[0].cpu().numpy().astype(np.float32)

        if speed != 1.0 and speed > 0:
            import librosa
            waveform = librosa.effects.time_stretch(waveform, rate=float(speed))

        return waveform, self.native_sample_rate
