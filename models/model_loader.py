"""
TTS Model Loader Factory
Manages model instances, switching, and caching.
"""

from typing import Dict
from models.base_engine import BaseTTSEngine
from models.edge_tts_engine import EdgeTTSEngine


class ModelLoader:
    def __init__(self):
        self._engines: Dict[str, BaseTTSEngine] = {}

    def get_engine(self, model_key: str = "edge_female") -> BaseTTSEngine:
        """
        Retrieves or initializes a TTS model engine.
        
        Args:
            model_key: Key identifier for the requested model ('edge_female', 'edge_male', 'mms_malayalam', 'ai4bharat_indic', 'xtts_v2')
            
        Returns:
            Instance of BaseTTSEngine ready for synthesis.
        """
        if model_key not in self._engines:
            if model_key in ["edge_female", "female", "sobhana"]:
                engine = EdgeTTSEngine(voice_name="ml-IN-SobhanaNeural", model_id="edge_female")
            elif model_key in ["edge_male", "midhun"]:
                engine = EdgeTTSEngine(voice_name="ml-IN-MidhunNeural", model_id="edge_male")
            elif model_key == "mms_malayalam":
                from models.mms_engine import MMSTTSEngine
                engine = MMSTTSEngine()
            elif model_key == "ai4bharat_indic":
                from models.ai4bharat_engine import AI4BharatTTSEngine
                engine = AI4BharatTTSEngine()
            elif model_key == "xtts_v2":
                from models.xtts_engine import XTTSEngine
                engine = XTTSEngine()
            else:
                print(f"[!] Unknown model key '{model_key}'. Defaulting to Edge TTS Sobhana.")
                engine = EdgeTTSEngine(voice_name="ml-IN-SobhanaNeural", model_id="edge_female")
            
            engine.load_model()
            self._engines[model_key] = engine

        return self._engines[model_key]

