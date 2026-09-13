"""
Domain-Specific Named Entity Detector for Malayalam Movie News v3.0
Extracts Actors, Directors, Movie Titles, Dates/Releases, OTT platforms, and Key Announcements.
"""

import re
from typing import List, Dict, Any

# Malayalam & English Known Entities
KNOWN_ACTORS = [
    "മോഹൻലാൽ", "മോഹൻലാലിന്റെ", "മോഹൻലാലും", "മോഹൻലാലിനെ",
    "മമ്മൂട്ടി", "മമ്മൂട്ടിയുടെ", "മമ്മൂട്ടിയും",
    "സംവൃത സുനിൽ", "ഉർവശി", "ജോജു ജോർജ്", "ഐശ്വര്യ ലക്ഷ്മി", "വിജയരാഘവൻ",
    "റോഷൻ മാത്യു", "ദിവ്യ പ്രഭ", "ജിതിൻ പുത്തഞ്ചേരി", "വിനയ് ഫോർട്ട്", "അർഷ ബൈജു",
    "മഹേഷ് നാരായണൻ", "ശാന്തി ബാലചന്ദ്രൻ", "ദുൽഖർ സൽമാൻ", "ദുൽഖർ സൽമാന്റെ",
    "വിസ്മയ മോഹൻലാൽ", "ജഗദീഷ്", "മുകേഷ്", "സിദ്ദിഖ്", "അശോകൻ", "ധനുഷ്",
    "പൃഥ്വിരാജ്", "പൃഥ്വിരാജ് സുകുമാരൻ", "ഫഹദ് ഫാസിൽ", "ടൊവിനോ തോമസ്", "നിവിൻ പോളി",
    "ആസിഫ് അലി", "സുരേഷ് ഗോപി", "ദിലീപ്", "ദിലീഷ് പോത്തനും", "ദിലീഷ് പോത്തൻ",
    "ജയസൂര്യ", "കുഞ്ചാക്കോ ബോബൻ", "മഞ്ജു വാര്യർ", "നസ്ലൻ", "മമിത ബൈജു", "ബേസിൽ ജോസ്"
]

KNOWN_DIRECTORS = [
    "ജൂഡ് ആന്തണി ജോസഫ്", "ജൂഡ് ആന്തണി ജോസഫും", "അഷിഖ് ഉസ്മാൻ", "അഷിഖ് ഉസ്മാനും",
    "അൽഫോൺസ് പുത്രൻ", "അൽഫോൺസ് പുത്രനും", "ഷാഹിദ് അറഫാത്ത്",
    "നിതീഷ് സഹദേവ്", "അനുരാജ് ഒ.ബി.", "മമ്മൂട്ടി കമ്പനി", "ജിംഷി ഖാലിദ്",
    "സഫർ സനൽ", "ഡോൺ പാലത്തറ", "നഹാസ് ഹിദായത്ത്", "ലിജോ ജോസ് പെല്ലിശ്ശേരി",
    "ജീത്തു ജോസഫ്", "അമൽ നീരദ്", "അൻവർ റഷീദ്"
]

KNOWN_MOVIES = [
    "L370", "എൽ 370", "മേള", "മേളയുടെ", "ആശ", "ഐ ആം ഗെയിം", "തുടക്കം",
    "അതി മനോഹരം", "പ്രഥമ ദൃഷ്ട്യാ കുറ്റക്കാർ", "രന്താൾ", "അമാനുഷികം",
    "ഡോണ്ട് ട്രബിൾ ദി ട്രബിൾ", "മണ്ടാടി", "ബൊളഗോലം", "വരാഹം", "നിംറോഡ്",
    "വൺ പ്രിൻസസ് സ്ട്രീറ്റ്", "ക്രെഡിറ്റ് സ്കോർ", "അവരാൻ", "ഓം ചാപ്റ്റർ വൺ",
    "പാതിരാക്കുറുക്കൻ", "ഏകദേശം ദി അൺസെർട്ടന്റി പ്രിൻസിപ്പിൾ", "ഏകദേശം"
]

KNOWN_OTT = [
    "ജിയോ ഹോട്ട്സ്റ്റാർ", "ജിയോ ഹോട്ട്സ്റ്റാറിൽ", "നെറ്റ്ഫ്ലിക്സ്", "നെറ്റ്ഫ്ലിക്സിൽ",
    "ഒ.ടി.ടി", "ഒ.ടി.ടിയിൽ", "OTT", "Netflix", "Hotstar", "YouTube", "യൂട്യൂബ്"
]

ANNOUNCEMENT_KEYWORDS = [
    "പ്രഖ്യാപിച്ചു", "തിരിച്ചെത്തുന്നു", "തിരിച്ചെത്തുകയാണ്", "ഫസ്റ്റ് ലുക്ക്",
    "ട്രെയിലർ പുറത്ത്", "ട്രെയിലർ പുറത്തിറങ്ങി", "സ്ട്രീമിംഗ് ആരംഭിക്കും",
    "ചിത്രീകരണം പൂർത്തിയാക്കി", "സബ്സ്ക്രൈബ് ചെയ്യൂ", "റിലീസ് ചെയ്തു",
    "തിയേറ്ററുകളിൽ എത്തും", "തിയേറ്ററുകളിലെത്തി"
]


class EntityDetector:
    def __init__(self):
        # Sort lists by length descending to match multi-word names first
        self.actors = sorted(KNOWN_ACTORS, key=len, reverse=True)
        self.directors = sorted(KNOWN_DIRECTORS, key=len, reverse=True)
        self.movies = sorted(KNOWN_MOVIES, key=len, reverse=True)
        self.ott = sorted(KNOWN_OTT, key=len, reverse=True)
        self.announcements = sorted(ANNOUNCEMENT_KEYWORDS, key=len, reverse=True)

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Scans text and extracts detected actors, directors, movies, dates, OTT, and announcements.
        Returns a dict of entity categories to list of matched text strings.
        """
        entities = {
            "movies": [],
            "actors": [],
            "directors": [],
            "dates": [],
            "ott": [],
            "announcements": []
        }

        # 1. Date & Temporal Expressions (regex pattern)
        date_pattern = r'(\b(?:സെപ്റ്റംബർ|ഡിസംബർ|ജനുവരി|ഫെബ്രുവരി|മാർച്ച്|ഏപ്രിൽ|മേയ്|ജൂൺ|ജൂലൈ|ഓഗസ്റ്റ്|ഒക്ടോബർ|നവംബർ)\s+\d{1,2}(?:,\s*\d{4})?|\b\d{4}\b|\b\d{1,3}-ാം|\b\d{1,3}\s*വർഷത്തിന് ശേഷം)'
        dates_found = re.findall(date_pattern, text)
        entities["dates"] = list(set(dates_found))

        # 2. Movie Titles
        for movie in self.movies:
            if movie.lower() in text.lower() and movie not in entities["movies"]:
                entities["movies"].append(movie)

        # 3. Actors
        for actor in self.actors:
            if actor in text and actor not in entities["actors"]:
                entities["actors"].append(actor)

        # 4. Directors
        for director in self.directors:
            if director in text and director not in entities["directors"]:
                entities["directors"].append(director)

        # 5. OTT Platforms
        for ott in self.ott:
            if ott in text and ott not in entities["ott"]:
                entities["ott"].append(ott)

        # 6. Announcements
        for ann in self.announcements:
            if ann in text and ann not in entities["announcements"]:
                entities["announcements"].append(ann)

        return entities

    def get_all_entity_phrases(self, text: str) -> List[str]:
        """Returns a flat list of all entity strings found in the sentence."""
        extracted = self.extract_entities(text)
        all_phrases = []
        for cat, items in extracted.items():
            all_phrases.extend(items)
        return list(set(all_phrases))
