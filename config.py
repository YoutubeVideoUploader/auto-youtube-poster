import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Output Directories
OUTPUT_DIR = BASE_DIR / "outputs"
TEST_OUTPUT_DIR = OUTPUT_DIR / "voice_tests"
BENCHMARK_OUTPUT_DIR = OUTPUT_DIR / "benchmarks"
VOICES_DIR = BASE_DIR / "voices" / "reference_voices"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Audio Settings
DEFAULT_SAMPLE_RATE = 44100  # High quality audio standard (44.1 kHz)
ALT_SAMPLE_RATE = 48000      # Video production standard (48 kHz)
DEFAULT_AUDIO_FORMAT = "wav"
NORMALIZE_LOUDNESS = True
TARGET_LUFS = -16.0          # Streaming / YouTube standard loudness
SILENCE_TRIM_DB = 30         # dB threshold for trimming leading/trailing silence
BGM_VOLUME = 0.12            # Background music volume level (increased for better audibility)

# Default TTS Engine Models
DEFAULT_MODEL_ID = "mms_malayalam"
AVAILABLE_MODELS = {
    "mms_malayalam": {
        "name": "Meta MMS-TTS Malayalam",
        "huggingface_repo": "facebook/mms-tts-mal",
        "description": "Meta Massively Multilingual Speech model for Malayalam (VITS + HiFi-GAN)",
        "sample_rate": 16000
    },
    "ai4bharat_indic": {
        "name": "AI4Bharat IndicTTS VITS",
        "huggingface_repo": "ai4bharat/vits_rasa_13",
        "description": "AI4Bharat multi-speaker Indic model supporting Malayalam",
        "sample_rate": 22050
    },
    "xtts_v2": {
        "name": "Coqui XTTS v2 Zero-Shot Voice Clone",
        "huggingface_repo": "tts_models/multilingual/multi-dataset/xtts_v2",
        "description": "Zero-Shot Voice Cloning model that mirrors custom human presenter voice sample",
        "sample_rate": 24000
    }
}

# Speaking Styles Preset Configurations
SPEAKING_STYLES = {
    "movie_news": {
        "speed": 1.08,
        "pause_factor": 1.0,
        "pitch_shift": 0,
        "description": "Professional Malayalam YouTube Movie News Presenter"
    },
    "movie_review": {
        "speed": 0.95,
        "pause_factor": 1.1,
        "pitch_shift": 0,
        "description": "Measured & Expressive Malayalam Movie Reviewer"
    },
    "breaking_news": {
        "speed": 1.1,
        "pause_factor": 0.85,
        "pitch_shift": 0,
        "description": "Energetic & Fast Pace News Anchor"
    },
    "casual": {
        "speed": 1.0,
        "pause_factor": 1.0,
        "pitch_shift": 0,
        "description": "Natural conversational Malayalam style"
    }
}

# Multi-Sheet Video Configuration
SHEET_ORDER = [
    {
        "name": "Movie Updates",
        "slug": "movie_updates",
        "intro": "ആദ്യം, പുതിയ മലയാള സിനിമാ അപ്ഡേറ്റുകളിലേക്ക് കടക്കാം."
    },
    {
        "name": "Release Updates",
        "slug": "release_updates",
        "intro": "ഇനി അടുത്തതായി, റിലീസിന് ഒരുങ്ങുന്ന സിനിമകളുടെ അപ്ഡേറ്റുകളിലേക്ക്."
    },
    {
        "name": "OTT Updates",
        "slug": "ott_updates",
        "intro": "ഇനി അടുത്തതായി, ഒടിടി റിലീസുകളുടെയും സ്ട്രീമിംഗ് അപ്ഡേറ്റുകളുടെയും വിശേഷങ്ങളിലേക്ക്."
    }
]

GLOBAL_INTRO = "എല്ലാവർക്കും സിനിമാലോകത്തെ പുതുപുത്തൻ വാർത്തകളിലേക്ക് സ്വാഗതം!"
GLOBAL_OUTRO = "ഇനി പുതിയ സിനിമാ വാർത്തകളുമായി ഉടൻ വീണ്ടും കാണാം. അതുവരെ എല്ലാവർക്കും ബൈ!"
TEST_MODE = False

