"""
Malayalam Grapheme-to-Phoneme (G2P) & Syllabification Layer v3.3
Parses Malayalam words into explicit syllabic components and phoneme tokens.
"""

import re
from typing import List, Dict, Any

MALAYALAM_VOWELS = set("അആഇഈഉഊഋഎഏഐഒഓഔ")
MALAYALAM_MATRAS = set("ാിീുൂൃെേൈൊോൗംഃ")
MALAYALAM_CHILLU = set("ൻൽർൾൺ")
VIRAMA = "്"


class MalayalamG2P:
    def __init__(self):
        pass

    def syllabify_word(self, word: str) -> List[str]:
        """
        Splits a Malayalam word into its constituent syllabic units.
        For example: 'സ്വാഗതം' -> ['സ്വാ', 'ഗ', 'തം']
        """
        word = word.strip()
        if not word:
            return []

        syllables = []
        current = ""
        i = 0
        length = len(word)

        while i < length:
            char = word[i]
            current += char

            # Check if virama connects to next consonant (Koottaksharam)
            if char == VIRAMA and (i + 1) < length:
                next_char = word[i + 1]
                # If next char is consonant/vowel matra, continue current syllable
                current += next_char
                i += 2
                # Catch any attached matra after consonant
                while i < length and word[i] in MALAYALAM_MATRAS:
                    current += word[i]
                    i += 1
                syllables.append(current)
                current = ""
                continue

            # If matra or vowel or chillu, end syllable chunk
            if char in MALAYALAM_MATRAS or char in MALAYALAM_CHILLU or char in MALAYALAM_VOWELS:
                syllables.append(current)
                current = ""
            elif (i + 1) < length and word[i + 1] not in (VIRAMA, *MALAYALAM_MATRAS):
                # Standard independent consonant without virama/matra
                syllables.append(current)
                current = ""

            i += 1

        if current:
            if syllables and len(current) == 1 and current in MALAYALAM_MATRAS:
                syllables[-1] += current
            else:
                syllables.append(current)

        return [s for s in syllables if s]

    def extract_phonemes(self, text: str) -> Dict[str, Any]:
        """
        Extracts phoneme preservation metrics from Malayalam text.
        """
        words = re.findall(r'[\u0D00-\u0D7F]+', text)
        word_syllables = {}
        for w in words:
            word_syllables[w] = self.syllabify_word(w)

        return {
            "total_words": len(words),
            "word_syllables": word_syllables,
            "has_dental_tha": any("ത" in w or "ഥ" in w for w in words),
            "has_retroflex_ta": any("ട" in w or "ഠ" in w or "ഡ" in w for w in words),
            "has_nasal": any("ന" in w or "ണ" in w for w in words),
            "has_liquid": any("ല" in w or "ള" in w or "ഴ" in w for w in words),
            "has_trill": any("ര" in w or "റ" in w for w in words)
        }
