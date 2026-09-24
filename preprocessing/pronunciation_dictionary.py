"""
Malayalam Pronunciation Dictionary
Maps English words, movie industry terms, OTT platforms, actor/director names,
and technical terms into phonetically accurate Malayalam script.
"""

import re
import json
from pathlib import Path

DEFAULT_PRONUNCIATION_DICT = {
    # OTT & Tech Platforms
    "OTT": "ഒ.ടി.ടി",
    "Netflix": "നെറ്റ്ഫ്ലിക്സ്",
    "Amazon Prime": "ആമസോൺ പ്രൈം",
    "Prime Video": "പ്രൈം വീഡിയോ",
    "YouTube": "യൂട്യൂബ്",
    "Instagram": "ഇൻസ്റ്റാഗ്രാം",
    "Facebook": "ഫേസ്ബുക്ക്",
    "Twitter": "ട്വിറ്റർ",
    "Hotstar": "ഹോട്ട്സ്റ്റാർ",
    "JioHotstar": "ജിയോ ഹോട്ട്സ്റ്റാർ",
    "Disney+": "ഡിസ്നി പ്ലസ്",
    "ZEE5ൽ": "സീ ഫൈവിൽ",
    "ZEE5": "സീ ഫൈവ്",
    "ZEE": "സീ",
    "SonyLIV": "സോണിലിവ്",
    "ManoramaMAX": "മനോരമ മാക്സ്",

    # Movie Titles & Specific English Phrases
    "NP 51ലേക്ക്": "എൻ.പി. അൻപത്തൊന്നിലേക്ക്",
    "NP 51": "എൻ.പി. അൻപത്തൊന്ന്",
    "NP": "എൻ.പി.",
    "L370ന്റെ": "എൽ മൂന്നൂറ്റി ഏഴുപതിന്റെ",
    "L370": "എൽ മൂന്നൂറ്റി ഏഴുപത്",
    "Ekadesham – The Uncertainty Principle": "ഏകദേശം ദി അൺസെർട്ടന്റി പ്രിൻസിപ്പിൾ",
    "Ekadesham": "ഏകദേശം",
    "I'm Game": "ഐ ആം ഗെയിം",
    "I'M GAME": "ഐ ആം ഗെയിം",
    "Don't Trouble the Trouble": "ഡോണ്ട് ട്രബിൾ ദി ട്രബിൾ",
    "1 Princess Street": "വൺ പ്രിൻസസ് സ്ട്രീറ്റ്",
    "Credit Score": "ക്രെഡിറ്റ് സ്കോർ",
    "OM: Chapter One": "ഓം ചാപ്റ്റർ വൺ",
    "Chapter One": "ചാപ്റ്റർ വൺ",

    # Movie Industry Terms
    "Trailer": "ട്രെയിലർ",
    "Teaser": "ടീസർ",
    "Release": "റിലീസ്",
    "Update": "അപ്ഡേറ്റ്",
    "Director": "സംവിധായകൻ",
    "Producer": "നിർമ്മാതാവ്",
    "Review": "റിവ്യൂ",
    "First Look": "ഫസ്റ്റ് ലുക്ക്",
    "Poster": "പോസ്റ്റർ",
    "Box Office": "ബോക്സ് ഓഫീസ്",
    "Collection": "കളക്ഷൻ",
    "Blockbuster": "ബ്ലോക്ക്ബസ്റ്റർ",
    "Hit": "ഹിറ്റ്",
    "Super Hit": "സൂപ്പർ ഹിറ്റ്",
    "Flop": "ഫ്ലോപ്പ്",
    "Cinema": "സിനിമ",
    "Movie": "മൂവി",
    "Song": "സോങ്",
    "Lyrical": "ലിറിക്കൽ",
    "Video": "വീഡിയോ",
    "Audio": "ഓഡിയോ",
    "Shooting": "ഷൂട്ടിംഗ്",
    "Dubbing": "ഡബ്ബിംഗ്",
    "Casting": "കാസ്റ്റിംഗ്",
    "Interval": "ഇന്റർവൽ",
    "Climax": "ക്ലൈമാക്സ്",
    "VFX": "വി.എഫ്.എക്സ്",
    "BGM": "ബി.ജി.എം",
    "HD": "എച്ച്.ഡി",
    "4K": "ഫോർ കെ",

    # Key Actor & Director Names (English to Malayalam)
    "Mohanlal": "മോഹൻലാൽ",
    "Mammootty": "മമ്മൂട്ടി",
    "Prithviraj": "പൃഥ്വിരാജ്",
    "Prithviraj Sukumaran": "പൃഥ്വിരാജ് സുകുമാരൻ",
    "Fahadh Faasil": "ഫഹദ് ഫാസിൽ",
    "Dulquer Salmaan": "ദുൽഖർ സൽമാൻ",
    "Tovino Thomas": "ടൊവിനോ തോമസ്",
    "Nivin Pauly": "നിവിൻ പോളി",
    "Asif Ali": "ആസിഫ് അലി",
    "Suresh Gopi": "സുരേഷ് ഗോപി",
    "Dileep": "ദിലീപ്",
    "Jayasurya": "ജയസൂര്യ",
    "Kunchacko Boban": "കുഞ്ചാക്കോ ബോബൻ",
    "Manju Warrier": "മഞ്ജു വാര്യർ",
    "Parvathy": "പാർവ്വതി",
    "Keerthy Suresh": "കീർത്തി സുരേഷ്",
    "Kalyani Priyadarshan": "കല്യാണി പ്രിയദർശൻ",
    "Naslen": "നസ്ലൻ",
    "Mamitha Baiju": "മമിത ബൈജു",
    "Basil Joseph": "ബേസിൽ ജോസഫ്",
    "Lijo Jose Pellissery": "ലിജോ ജോസ് പെല്ലിശ്ശേരി",
    "Jeethu Joseph": "ജീത്തു ജോസഫ്",
    "Amal Neerad": "അമൽ നീരദ്",
    "Anwar Rasheed": "അൻവർ റഷീദ്",
    "Aphonse Puthren": "അൽഫോൻസ് പുത്രൻ",

    # Specific Malayalam Name & Word Pronunciation Corrections
    "ആന്തണി": "ആന്റണി",
    "Jude Anthany": "ജൂഡ് ആന്റണി",
    "Jude Anthany Joseph": "ജൂഡ് ആന്റണി ജോസഫ്",
    "Jude Antony": "ജൂഡ് ആന്റണി",
    "Jude Antony Joseph": "ജൂഡ് ആന്റണി ജോസഫ്",
    "സമ്വൃത": "സംവൃത",
    "ലേക്ക് കടക്കാം": "ലേക്ക് പോകാം",
    "കടക്കാം": "പോകാം"
}


ENGLISH_LETTER_MAP = {
    'A': 'എ', 'B': 'ബി', 'C': 'സി', 'D': 'ഡി', 'E': 'ഈ', 'F': 'എഫ്', 'G': 'ജി', 'H': 'എച്ച്',
    'I': 'ഐ', 'J': 'ജെ', 'K': 'കെ', 'L': 'എൽ', 'M': 'എം', 'N': 'എൻ', 'O': 'ഒ', 'P': 'പി',
    'Q': 'ക്യു', 'R': 'ആർ', 'S': 'എസ്', 'T': 'ടി', 'U': 'യു', 'V': 'വി', 'W': 'ഡബ്ല്യു',
    'X': 'എക്സ്', 'Y': 'വൈ', 'Z': 'സെഡ്'
}


class PronunciationDictionary:
    def __init__(self, custom_dict_path: str = None):
        self.dictionary = DEFAULT_PRONUNCIATION_DICT.copy()
        if custom_dict_path and Path(custom_dict_path).exists():
            self.load_custom_dictionary(custom_dict_path)

    def load_custom_dictionary(self, filepath: str):
        """Load external JSON dictionary (dict or list of {"text": ..., "spoken_as": ...}) and merge."""
        with open(filepath, 'r', encoding='utf-8') as f:
            custom_data = json.load(f)
            self.apply_overrides(custom_data)

    def apply_overrides(self, overrides):
        """
        Applies overrides passed as a dict {"text": "spoken"} or list [{"text": "...", "spoken_as": "..."}].
        """
        if isinstance(overrides, dict):
            for k, v in overrides.items():
                self.dictionary[k.strip()] = v.strip()
        elif isinstance(overrides, list):
            for item in overrides:
                if isinstance(item, dict) and "text" in item and "spoken_as" in item:
                    self.dictionary[item["text"].strip()] = item["spoken_as"].strip()

    def add_override(self, english_word: str, malayalam_phonetic: str):
        """Dynamically add or update a word mapping."""
        self.dictionary[english_word.strip()] = malayalam_phonetic.strip()

    def replace_english_words(self, text: str) -> str:
        """
        Replaces known English words/phrases and Malayalam phonetic corrections.
        Transliterates any remaining English acronyms and letters into Malayalam script.
        """
        sorted_keys = sorted(self.dictionary.keys(), key=len, reverse=True)

        processed_text = text
        for key in sorted_keys:
            replacement = self.dictionary[key]
            if re.search(r'[\u0d00-\u0d7f]', key):
                # Malayalam Unicode boundary matching
                pattern = re.compile(r'(?<![\u0d00-\u0d7f])' + re.escape(key) + r'(?![\u0d00-\u0d7f])', re.IGNORECASE)
            else:
                # ASCII / English word boundary matching
                pattern = re.compile(r'(?<![A-Za-z0-9])' + re.escape(key) + r'(?![A-Za-z0-9])', re.IGNORECASE)
            processed_text = pattern.sub(replacement, processed_text)

        # Transliterate remaining uppercase English letters / acronyms (e.g. C.I. -> സി.ഐ.)
        def _acronym_replacer(match):
            word = match.group(0)
            if word.isupper() and len(word) <= 4:
                return ''.join(ENGLISH_LETTER_MAP.get(ch, ch) for ch in word)
            return word

        processed_text = re.sub(r'\b[A-Z]{1,4}\b', _acronym_replacer, processed_text)
        return processed_text

