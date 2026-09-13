"""
Abstract Base Class for Malayalam TTS Engines
Ensures all model wrappers conform to a uniform synthesizer API contract.
"""

from abc import ABC, abstractmethod
from typing import Tuple
import numpy as np


class BaseTTSEngine(ABC):
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.is_loaded = False

    @abstractmethod
    def load_model(self):
        """Loads model weights and tokenizers into memory/GPU."""
        pass

    @abstractmethod
    def synthesize(self, text: str, speed: float = 1.0, pitch: float = 0.0) -> Tuple[np.ndarray, int]:
        """
        Synthesizes preprocessed Malayalam text to audio waveform.
        
        Args:
            text: Normalized Malayalam text string
            speed: Playback speed multiplier (1.0 = normal)
            pitch: Pitch shift offset in semitones (0.0 = default)
            
        Returns:
            Tuple of (audio_waveform: np.ndarray, sample_rate: int)
        """
        pass
