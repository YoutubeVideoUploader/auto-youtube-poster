"""
Meta MMS-TTS Malayalam Model Engine Implementation
Uses Hugging Face VitsModel for facebook/mms-tts-mal.
"""

import os
import sys
import ssl
import time
import urllib3
import torch
import numpy as np
from typing import Tuple
from transformers import VitsModel, AutoTokenizer

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


class MMSTTSEngine(BaseTTSEngine):
    def __init__(self, model_repo: str = "facebook/mms-tts-mal"):
        super().__init__(model_id="mms_malayalam")
        self.model_repo = model_repo
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.native_sample_rate = 16000

    def load_model(self):
        if self.is_loaded:
            return

        print(f"[*] Loading Meta MMS-TTS Malayalam from '{self.model_repo}' on device: {self.device}...")
        t0 = time.time()
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_repo)
        self.model = VitsModel.from_pretrained(self.model_repo).to(self.device)
        self.model.eval()
        self.is_loaded = True
        print(f"[+] MMS-TTS Model loaded successfully in {time.time() - t0:.2f} seconds.")

    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        if not self.is_loaded:
            self.load_model()

        if not text or not text.strip():
            return np.zeros(0, dtype=np.float32), self.native_sample_rate

        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)

        with torch.no_grad():
            output = self.model(**inputs)
            waveform = output.waveform[0].cpu().numpy().astype(np.float32)

        # Apply smooth polyphase speed scaling if speed != 1.0
        if speed != 1.0 and speed > 0 and len(waveform) > 0:
            import scipy.signal
            target_samples = int(len(waveform) / float(speed))
            waveform = scipy.signal.resample(waveform, target_samples).astype(np.float32)

        return waveform, self.native_sample_rate
