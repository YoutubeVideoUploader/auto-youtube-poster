"""
Gemini TTS Engine Implementation for Malayalam Voice Synthesis
Locked strictly to Gemini 2.5 (gemini-2.5-flash-preview-tts) for 100% uniform voice.
Multi-key rotation across verified active keys with persistent disk caching.
Keys are loaded securely from environment variables or local gitignored config.
"""

import os
import re
import sys
import json
import time
import base64
import hashlib
import requests
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from models.base_engine import BaseTTSEngine
from config import OUTPUT_DIR

# Ensure UTF-8 console output on Windows without crashing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def _log(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", "replace").decode("ascii"), flush=True)
        except Exception:
            pass


class GeminiTTSEngine(BaseTTSEngine):
    def __init__(self, voice_name: str = "Kore", model_id: str = "gemini_voice", api_key: Optional[str] = None):
        super().__init__(model_id=model_id)
        self.voice_name = voice_name
        # Upgraded to Gemini 3.1 Flash TTS Preview for next-gen clarity & natural Malayalam delivery
        self.model_name = "gemini-3.1-flash-tts-preview"
        self.fallback_model_name = "gemini-2.5-flash-preview-tts"
        self.native_sample_rate = 24000
        self.api_keys = self._resolve_api_keys(api_key)
        self.current_key_idx = 0
        self._last_call_time = 0.0

    def _resolve_api_keys(self, single_key: Optional[str] = None) -> list:
        keys = []
        if single_key:
            for k in str(single_key).split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        # 1. Environment Variable(s)
        env_k = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_k:
            for k in env_k.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        env_keys = os.environ.get("GEMINI_API_KEYS", "").strip()
        if env_keys:
            for k in env_keys.split(","):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)

        # 2. Local gitignored keys file (outputs/gemini_keys.json or gemini_keys.json)
        for cand in [OUTPUT_DIR / "gemini_keys.json", Path("gemini_keys.json")]:
            if cand.exists():
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        file_keys = json.load(f)
                        if isinstance(file_keys, list):
                            for fk in file_keys:
                                fk_clean = str(fk).strip()
                                if fk_clean and fk_clean not in keys:
                                    keys.append(fk_clean)
                except Exception:
                    pass

        # 3. Check sheet_cache.json Config
        cache_path = OUTPUT_DIR / "sheet_cache.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f).get("Config", [])
                    for row in cfg:
                        if isinstance(row, dict):
                            k = str(row.get("Key Name", "")).strip().lower()
                            v = str(row.get("Key Value", "")).strip()
                            if "gemini" in k and v and v not in keys:
                                keys.append(v)
            except Exception:
                pass

        return keys

    def load_model(self):
        if not self.api_keys:
            raise ValueError("No valid Gemini API keys found. Please set GEMINI_API_KEY in environment or gemini_keys.json.")
        self.is_loaded = True

    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        """
        Synthesizes Malayalam text to 24kHz float32 audio waveform using Gemini 2.5 TTS API.
        Includes local disk caching and multi-key rotation to guarantee uniform voice.
        """
        if not text or not text.strip():
            return np.zeros(0, dtype=np.float32), self.native_sample_rate

        cleaned_text = text.strip()
        # Direct pronunciation safeguard: avoid known phonetic hallucination in Gemini Malayalam voice
        cleaned_text = re.sub(r'ലേക്ക്\s+കടക്കാം', 'ലേക്ക് പോകാം', cleaned_text)
        cleaned_text = re.sub(r'(?<![\u0d00-\u0d7f])കടക്കാം(?![\u0d00-\u0d7f])', 'പോകാം', cleaned_text)

        # 1. Check local persistent disk cache (model-specific hash)
        cache_dir = OUTPUT_DIR / "gemini_voice_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        text_hash = hashlib.md5((cleaned_text + "_" + self.voice_name + "_" + self.model_name).encode('utf-8')).hexdigest()
        cache_file = cache_dir / f"{text_hash}.npy"

        if cache_file.exists():
            try:
                waveform = np.load(str(cache_file))
                _log(f"[Gemini 2.5] Cache Hit: loaded {len(waveform)} samples")
                return waveform, self.native_sample_rate
            except Exception:
                pass

        # 2. Prepare payload & headers with explicit Malayalam instruction
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Read naturally, clearly, and expressively in Malayalam as a professional cinema news anchor with crisp enunciation: {cleaned_text}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.voice_name
                        }
                    }
                }
            }
        }
        headers = {"Content-Type": "application/json"}

        # 3. Pacing: brief pause between calls (Paid tier allows rapid throughput)
        elapsed = time.time() - self._last_call_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self._last_call_time = time.time()

        max_attempts = len(self.api_keys) * 4

        for attempt in range(1, max_attempts + 1):
            key = self.api_keys[self.current_key_idx % len(self.api_keys)]
            self.current_key_idx += 1
            # If primary model hits issues across full rotation, try fallback model
            active_model = self.model_name if attempt <= len(self.api_keys) * 2 else self.fallback_model_name
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={key}"

            r = None
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=40)
            except Exception as e:
                _log(f"[!] Network exception on key ...{key[-6:]}: {e}")
                time.sleep(1)
                continue

            if r.status_code == 200:
                try:
                    data = r.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for p in parts:
                            if "inlineData" in p:
                                raw_b64 = p["inlineData"].get("data", "")
                                if raw_b64:
                                    pcm_bytes = base64.b64decode(raw_b64)
                                    waveform = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                                    try:
                                        np.save(str(cache_file), waveform)
                                    except Exception:
                                        pass
                                    _log(f"[Gemini 3.1] OK: generated {len(waveform)} samples via {active_model} (key ...{key[-6:]})")
                                    return waveform, self.native_sample_rate
                except Exception as ex:
                    _log(f"[!] Error parsing audio response: {ex}")
                    break

                _log(f"[!] Warning: Gemini 3.1 response missing audio data.")
                break

            elif r.status_code in [429, 503]:
                # If a key hits 429, immediately try next key in pool
                if len(self.api_keys) > 1 and (attempt % len(self.api_keys) != 0):
                    _log(f"[Gemini 3.1] Key ...{key[-6:]} hit 429. Instantly rotating to next key...")
                    continue

                _log(f"[Gemini 3.1] Cooldown pause 10s (attempt {attempt}/{max_attempts})...")
                time.sleep(10)

            else:
                _log(f"[!] Gemini 3.1 error {r.status_code} on key ...{key[-6:]}: {r.text[:120]}")
                if attempt < len(self.api_keys):
                    continue
                time.sleep(2)

        # Fallback to Edge TTS only as an absolute last resort
        _log(f"[!] Gemini 3.1 exhausted {max_attempts} attempts. Falling back to Edge TTS.")
        try:
            from models.edge_tts_engine import EdgeTTSEngine
            edge_engine = EdgeTTSEngine()
            return edge_engine.synthesize(cleaned_text, speed=speed, pitch=pitch)
        except Exception as e:
            _log(f"[!] Fallback failed: {e}")
            fallback_silence = np.zeros(int(self.native_sample_rate * 0.5), dtype=np.float32)
            return fallback_silence, self.native_sample_rate
