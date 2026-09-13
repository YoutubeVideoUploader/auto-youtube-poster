"""
Malayalam Text Normalizer
Handles Malayalam Unicode normalization, number-to-words conversion,
chillaksharam/koottaksharam handling, dates, currency, and pause markers.
"""

import re

# Malayalam Number Words mapping
MALAYALAM_DIGITS = {
    '0': 'പൂജ്യം',
    '1': 'ഒന്ന്',
    '2': 'രണ്ട്',
    '3': 'മൂന്ന്',
    '4': 'നാല്',
    '5': 'അഞ്ച്',
    '6': 'ആറ്',
    '7': 'ഏഴ്',
    '8': 'എട്ട്',
    '9': 'ഒൻപത്',
    '10': 'പത്ത്'
}

MALAYALAM_TEENS = {
    '11': 'പതിനൊന്ന്',
    '12': 'പന്ത്രണ്ട്',
    '13': 'പതിമൂന്ന്',
    '14': 'പതിനാല്',
    '15': 'പതിനഞ്ച്',
    '16': 'പതിനാറ്',
    '17': 'പതിനേഴ്',
    '18': 'പതിനെട്ട്',
    '19': 'പത്തൊൻപത്'
}

MALAYALAM_TENS = {
    '20': 'ഇരുപത്',
    '30': 'മുപ്പത്',
    '40': 'നാൽപ്പത്',
    '50': 'അൻപത്',
    '60': 'അറുപത്',
    '70': 'ഏഴുപത്',
    '80': 'എൺപത്',
    '90': 'തൊണ്ണൂറ്'
}

def number_to_malayalam_words(num: int) -> str:
    """Converts integers (0-99999999) into Malayalam words."""
    if num < 0:
        return "മൈനസ് " + number_to_malayalam_words(-num)
    if num <= 10:
        return MALAYALAM_DIGITS[str(num)]
    if 11 <= num <= 19:
        return MALAYALAM_TEENS[str(num)]
    if 20 <= num <= 99:
        ten = (num // 10) * 10
        rem = num % 10
        if rem == 0:
            return MALAYALAM_TENS[str(ten)]
        # Morphological joining for Malayalam numbers
        tens_prefix = {
            20: 'ഇരുപത്തി',
            30: 'മുപ്പത്തി',
            40: 'നാൽപ്പത്തി',
            50: 'അൻപത്തി',
            60: 'അറുപത്തി',
            70: 'ഏഴുപത്തി',
            80: 'എൺപത്തി',
            90: 'തൊണ്ണൂറ്റി'
        }
        return tens_prefix[ten] + MALAYALAM_DIGITS[str(rem)]
    
    if 100 <= num <= 999:
        hundred = num // 100
        rem = num % 100
        hundred_prefix = {
            1: 'നൂറ്',
            2: 'ഇരുനൂറ്',
            3: 'മൂന്നൂറ്',
            4: 'നാനൂറ്',
            5: 'അഞ്ഞൂറ്',
            6: 'അറന്നൂറ്',
            7: 'ഏഴന്നൂറ്',
            8: 'എണ്ണൂറ്',
            9: 'തൊള്ളായിരം'
        }
        if rem == 0:
            return hundred_prefix[hundred]
        prefix_mod = {
            1: 'നൂറ്റി',
            2: 'ഇരുനൂറ്റി',
            3: 'മൂന്നൂറ്റി',
            4: 'നാനൂറ്റി',
            5: 'അഞ്ഞൂറ്റി',
            6: 'അറന്നൂറ്റി',
            7: 'ഏഴന്നൂറ്റി',
            8: 'എണ്ണൂറ്റി',
            9: 'തൊള്ളായിരത്തി'
        }
        return prefix_mod[hundred] + " " + number_to_malayalam_words(rem)

    if 1000 <= num <= 99999:
        thousand = num // 1000
        rem = num % 1000
        th_word = "ആയിരം" if thousand == 1 else number_to_malayalam_words(thousand) + " ആയിരം"
        if rem == 0:
            return th_word
        th_word_mod = "ആയിരത്തി" if thousand == 1 else number_to_malayalam_words(thousand) + " ആയിരത്തി"
        return th_word_mod + " " + number_to_malayalam_words(rem)

    if 100000 <= num <= 9999999:
        lakh = num // 100000
        rem = num % 100000
        l_word = number_to_malayalam_words(lakh) + " ലക്ഷം"
        if rem == 0:
            return l_word
        return l_word + " " + number_to_malayalam_words(rem)

    if num >= 10000000:
        crore = num // 10000000
        rem = num % 10000000
        c_word = number_to_malayalam_words(crore) + " കോടി"
        if rem == 0:
            return c_word
        return c_word + " " + number_to_malayalam_words(rem)

    return str(num)


def number_to_malayalam_ordinal(num: int) -> str:
    """Converts integers into Malayalam ordinal words ending in 'ാം' (e.g. 370 -> മൂന്നൂറ്റി ഏഴുപതാം, 75 -> ഏഴുപത്തഞ്ചാം)."""
    specials = {
        1: 'ഒന്നാം', 2: 'രണ്ടാം', 3: 'മൂന്നാം', 4: 'നാലാം', 5: 'അഞ്ചാം',
        6: 'ആറാം', 7: 'ഏഴാം', 8: 'എട്ടാം', 9: 'ഒൻപതാം', 10: 'പത്താം',
        16: 'പതിനാറാം', 20: 'ഇരുപതാം', 30: 'മുപ്പതാം', 40: 'നാൽപ്പതാം',
        50: 'അൻപതാം', 60: 'അറുപതാം', 70: 'ഏഴുപതാം', 80: 'എൺപതാം', 90: 'തൊണ്ണൂറാം'
    }
    if num in specials:
        return specials[num]
    cardinal = number_to_malayalam_words(num)
    if cardinal.endswith('്') or cardinal.endswith('ു'):
        return cardinal[:-1] + 'ാം'
    elif cardinal.endswith('ത്') or cardinal.endswith('തം'):
        return cardinal[:-1] + 'ാം'
    elif cardinal.endswith('പത്'):
        return cardinal[:-1] + 'ാം'
    return cardinal + 'ാം'


def number_to_malayalam_ordinal_mathe(num: int) -> str:
    """Converts integers into Malayalam ordinal words ending in 'ാമത്തെ' (e.g. 370 -> മൂന്നൂറ്റി ഏഴുപതാമത്തെ)."""
    ord_word = number_to_malayalam_ordinal(num)
    if ord_word.endswith('ാം'):
        return ord_word[:-2] + 'ാമത്തെ'
    return ord_word + 'മത്തെ'


def number_to_malayalam_date_locative(num: int) -> str:
    """Converts integers into Malayalam date locative words ending in 'ന്' (e.g. 11 -> പതിനൊന്നിന്, 3 -> മൂന്നിന്, 18 -> പതിനെട്ടിന്)."""
    date_map = {
        1: 'ഒന്നിന്', 2: 'രണ്ടിന്', 3: 'മൂന്നിന്', 4: 'നാലിന്', 5: 'അഞ്ചിന്',
        6: 'ആറിന്', 7: 'ഏഴിന്', 8: 'എട്ടിന്', 9: 'ഒൻപതിന്', 10: 'പത്തിന്',
        11: 'പതിനൊന്നിന്', 12: 'പന്ത്രണ്ടിന്', 13: 'പതിമൂന്നിന്', 14: 'പതിനാലിന്',
        15: 'പതിനഞ്ചിന്', 16: 'പതിനാറിന്', 17: 'പതിനേഴിന്', 18: 'പതിനെട്ടിന്',
        19: 'പത്തൊൻപതിന്', 20: 'ഇരുപതിന്', 21: 'ഇരുപത്തൊന്നിന്', 22: 'ഇരുപത്തിരണ്ടിന്',
        23: 'ഇരുപത്തിമൂന്നിന്', 24: 'ഇരുപത്തിനാലിന്', 25: 'ഇരുപത്തഞ്ചിന്', 26: 'ഇരുപത്തിയാറിന്',
        27: 'ഇരുപത്തേഴിന്', 28: 'ഇരുപത്തെട്ടിന്', 29: 'ഇരുപത്തൊൻപതിന്', 30: 'മുപ്പതിന്', 31: 'മുപ്പത്തൊന്നിന്'
    }
    return date_map.get(num, number_to_malayalam_words(num) + 'ന്')


import unicodedata


class MalayalamNormalizer:
    def __init__(self):
        pass

    def convert_numbers(self, text: str) -> str:
        """Finds all ASCII digits (ordinals, decimals, date locatives, and cardinals) in text and converts them into Malayalam words."""
        # 1. Morphological ordinal '-ാമത്തെ' / 'ാമത്തെ'
        text = re.sub(r'(\d+)\s*(?:-|–)?\s*ാമത്തെ', lambda m: number_to_malayalam_ordinal_mathe(int(m.group(1))), text)
        # 2. Morphological ordinal '-ാം' / 'ാം'
        text = re.sub(r'(\d+)\s*(?:-|–)?\s*ാം', lambda m: number_to_malayalam_ordinal(int(m.group(1))), text)
        # 3. Date locative suffix 'ന്' (e.g. 11ന് -> പതിനൊന്നിന്, 25ന് -> ഇരുപത്തഞ്ചിന്)
        text = re.sub(r'(\d+)\s*(?:-|–)?\s*ന്', lambda m: number_to_malayalam_date_locative(int(m.group(1))), text)
        
        # 4. Decimals (e.g. 43.55 -> നാൽപ്പത്തിമൂന്ന് ദശാംശം അഞ്ച് അഞ്ച്)
        def replace_decimal(match):
            whole = int(match.group(1))
            frac = match.group(2)
            frac_words = " ".join(MALAYALAM_DIGITS.get(d, d) for d in frac)
            return f"{number_to_malayalam_words(whole)} ദശാംശം {frac_words}"

        text = re.sub(r'(\d+)\.(\d+)', replace_decimal, text)

        # 5. Standalone raw cardinal numbers
        def replace_match(match):
            val = int(match.group(0))
            return number_to_malayalam_words(val)

        text = re.sub(r'\b\d+\b', replace_match, text)
        return text

    def convert_symbols_and_currency(self, text: str) -> str:
        """Converts currency symbols, percentages, smart quotes, and decorative emojis."""
        # Handle ₹ amount with crore/lakh suffix e.g., ₹43.55 കോടി -> 43.55 കോടി രൂപ
        text = re.sub(r'₹\s*(\d+(?:\.\d+)?)\s*(കോടി|ലക്ഷം|ആയിരം)', r'\1 \2 രൂപ', text)
        text = re.sub(r'₹\s*(\d+(?:\.\d+)?)', r'\1 രൂപ', text)
        text = re.sub(r'\$\s*(\d+(?:\.\d+)?)\s*(കോടി|ലക്ഷം|ആയിരം)', r'\1 \2 ഡോളർ', text)
        text = re.sub(r'\$\s*(\d+(?:\.\d+)?)', r'\1 ഡോളർ', text)
        text = re.sub(r'(\d+)\s*%', r'\1 ശതമാനം', text)
        # Clean smart single/double quotes, backticks, and non-spoken decorative emojis
        text = re.sub(r'[\u2018\u2019\u201c\u201d\'"`]', '', text)
        text = re.sub(r'[🔹🔥🎬⭐🎉📋📊📁⏱️🚀]', '', text)
        text = re.sub(r'\s*–\s*', ', ', text)
        text = re.sub(r'\s*—\s*', ', ', text)
        return text


    def normalize_unicode_and_chillu(self, text: str) -> str:
        """Standardizes Malayalam Unicode NFC form, Chillaksharam, and Zero-Width Joiners (ZWJ)."""
        text = unicodedata.normalize('NFC', text)
        text = text.replace('\u200d', '').replace('\u200c', '')
        return text

    def format_pauses_and_punctuation(self, text: str) -> str:
        """
        Enhances prosody by ensuring proper spacing after punctuation.
        Replaces ellipsis (...) with explicit micro-pause markers.
        """
        # Normalize multiple dots into clean pause
        text = re.sub(r'\.{2,}', '... ', text)
        # Ensure space after commas, colons, and hyphens for natural pauses
        text = re.sub(r'([,;:!?])([^\s])', r'\1 \2', text)
        # Clean up excess whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def normalize(self, text: str) -> str:
        """Master normalization routine."""
        text = self.convert_symbols_and_currency(text)
        text = self.convert_numbers(text)
        text = self.normalize_unicode_and_chillu(text)
        text = self.format_pauses_and_punctuation(text)
        return text


