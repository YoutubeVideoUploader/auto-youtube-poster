"""
Persistent Pronunciation Learning Database Manager v3.3
Loads, queries, updates, and persists verified Malayalam movie-news pronunciations.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

DB_PATH = Path(__file__).resolve().parent / "pronunciation_database.json"


class PronunciationDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.entries: Dict[str, Any] = {}
        self.load_database()

    def load_database(self):
        """Loads persistent JSON database."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = data.get("entries", {})
            except Exception as e:
                print(f"[!] Error loading pronunciation database: {e}")
                self.entries = {}

    def save_database(self):
        """Persists database back to JSON."""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump({
                "database_version": "3.3",
                "entries": self.entries
            }, f, ensure_ascii=False, indent=2)

    def get_entry(self, word: str) -> Dict[str, Any]:
        """Returns entry dict if word exists in database."""
        return self.entries.get(word.strip())

    def add_entry(self, word: str, expected_syllables: List[str], phonetic_anchor: str, phoneme_group: str = "general"):
        """Adds or updates a verified word entry."""
        self.entries[word.strip()] = {
            "word": word.strip(),
            "expected_syllables": expected_syllables,
            "phonetic_anchor": phonetic_anchor,
            "phoneme_group": phoneme_group,
            "verified": True
        }
        self.save_database()

    def get_all_anchors(self) -> Dict[str, str]:
        """Returns dict of word -> phonetic_anchor mapping."""
        return {w: item["phonetic_anchor"] for w, item in self.entries.items() if item.get("phonetic_anchor")}
