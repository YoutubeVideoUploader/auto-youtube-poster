"""
Malayalam Text Processing Pipeline
Integrates Pronunciation Dictionary mapping, Malayalam Text Normalizer,
and Semantic Prosody Planner.
"""

from preprocessing.pronunciation_dictionary import PronunciationDictionary
from preprocessing.malayalam_normalizer import MalayalamNormalizer
from preprocessing.prosody_planner import ProsodyPlanner
from preprocessing.speech_integrity import SpeechIntegrityChecker


class TextProcessor:
    def __init__(self, custom_dict_path: str = None):
        self.dictionary = PronunciationDictionary(custom_dict_path)
        self.normalizer = MalayalamNormalizer()
        self.prosody_planner = ProsodyPlanner()
        self.speech_integrity = SpeechIntegrityChecker()

    def process(
        self,
        text: str,
        apply_dictionary: bool = True,
        apply_normalization: bool = True,
        apply_prosody: bool = True,
        apply_phoneme_anchors: bool = True
    ) -> str:
        """
        Processes input raw text through dictionary replacement, Malayalam normalization,
        speech integrity phoneme anchoring, and semantic prosody planning.
        """
        processed = text.strip()

        if apply_dictionary:
            processed = self.dictionary.replace_english_words(processed)

        if apply_normalization:
            processed = self.normalizer.normalize(processed)

        if apply_phoneme_anchors:
            processed = self.speech_integrity.validate_and_anchor_phonemes(processed)

        if apply_prosody:
            processed = self.prosody_planner.inject_semantic_pauses(processed)

        return processed
