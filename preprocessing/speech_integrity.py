"""
Malayalam Speech Integrity & Phoneme Validation System v3.2
Pre-scans Malayalam text to protect dental (ത/ഥ), retroflex (ട/ഡ), nasal (ന/ണ), liquid (ല/ള/ഴ),
and trill (റ/ര) consonants from swallowing or merging in long sentence contexts.
"""

import re
from typing import Dict, Any, List

# Explicit Malayalam Consonant Anchor Mappings
PHONETIC_CONSONANT_ANCHORS = {
    # Words where trailing anusvara/dental consonant gets swallowed in sentence tails
    "സ്വാഗതം": "സ്വാഗതമ്",
    "സ്വാഗതം.": "സ്വാഗതമ്.",
    "സ്വാഗതം!": "സ്വാഗതമ്!",
    "മാത്രം": "മാത്രമ്",
    "എത്തും": "എത്തുമ്",
    "തുടക്കം": "തുടക്കമ്",
    "അപ്ഡേറ്റുകൾ": "അപ്ഡേറ്റുകൾ",
    "തീരുമാനം": "തീരുമാനമ്",
    "രൂപീകരണം": "രൂപീകരണമ്",
    "കാരണം": "കാരണമ്",
    "ചിത്രീകരണം": "ചിത്രീകരണമ്"
}


class SpeechIntegrityChecker:
    def __init__(self, custom_anchors: Dict[str, str] = None):
        self.anchors = PHONETIC_CONSONANT_ANCHORS.copy()
        if custom_anchors:
            self.anchors.update(custom_anchors)

    def validate_and_anchor_phonemes(self, text: str) -> str:
        """
        Validates text for Malayalam consonant integrity and applies phonetic anchors
        to prevent phoneme collapsing (e.g. 'സ്വാഗതം' -> 'സ്വാഗതമ്').
        """
        if not text:
            return text

        processed = text
        sorted_keys = sorted(self.anchors.keys(), key=len, reverse=True)

        for target_word in sorted_keys:
            anchored = self.anchors[target_word]
            # Match target_word when not enclosed by Malayalam Unicode characters
            pattern = re.compile(r'(?<![\u0d00-\u0d7f])' + re.escape(target_word) + r'(?![\u0d00-\u0d7f])', re.IGNORECASE)
            processed = pattern.sub(anchored, processed)

        return processed

    def check_phoneme_preservation(self, text: str) -> Dict[str, Any]:
        """
        Performs a pre-synthesis inspection of Malayalam phoneme groups present in sentence.
        """
        results = {
            "has_dental_tha": bool(re.search(r'[തഥദധ]', text)),
            "has_retroflex_ta": bool(re.search(r'[ടഠഡഢ]', text)),
            "has_nasal_na_naa": bool(re.search(r'[നണ]', text)),
            "has_liquid_la_lla_zha": bool(re.search(r'[ലളഴ]', text)),
            "has_trill_ra_rra": bool(re.search(r'[റര]', text)),
            "anchored_words": []
        }

        for word in self.anchors:
            if word in text:
                results["anchored_words"].append(word)

        return results
