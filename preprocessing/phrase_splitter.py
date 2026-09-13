"""
Syntactic Phrase Boundary Parser for Malayalam Sentences v3.0
Splits complex Malayalam sentences into natural human presenter phrase units:
Subject -> Action / Descriptor -> Important Entity -> Result / Verb
"""

import re
from typing import List, Dict, Any


PHRASE_DELIMITERS = [
    r'\bനായകനാക്കി\b', r'\bസംവിധാനം ചെയ്യുന്ന\b', r'\bനിർവ്വഹിക്കുന്നു\b',
    r'\bപ്രധാന വേഷത്തിലെത്തുന്നത്\b', r'\bഭാഗമാകുന്നു\b', r'\bഒന്നിക്കുന്ന\b',
    r'\bതുടങ്ങുന്ന\b', r'\bലഭിക്കുന്നത്\b', r'\bതിരിച്ചെത്തുകയാണ്\b',
    r'\bഅണിയറയിലൊരുങ്ങുന്നു\b', r'\bപുറത്തിറങ്ങി\b', r'\bപ്രഖ്യാപിച്ചു\b'
]


class PhraseSplitter:
    def __init__(self):
        pass

    def split_into_phrases(self, sentence: str, entities: Dict[str, list] = None) -> List[Dict[str, Any]]:
        """
        Parses sentence into syntactic phrase units and assigns phrase boundary pause durations.
        """
        sentence = sentence.strip()
        if not sentence:
            return []

        # 1. First check if sentence has explicit punctuation splits (commas, colons, ellipses)
        raw_chunks = re.split(r'([,;:!\?–\n]+)', sentence)
        chunks = []
        for i in range(0, len(raw_chunks), 2):
            text_chunk = raw_chunks[i].strip()
            punct_chunk = raw_chunks[i+1] if i+1 < len(raw_chunks) else ""
            if text_chunk:
                chunks.append(text_chunk + punct_chunk)

        if not chunks:
            chunks = [sentence]

        # 2. Refine long chunks using syntactic Malayalam phrase boundaries
        phrases = []
        for chunk in chunks:
            sub_phrases = self._split_chunk_syntactically(chunk)
            phrases.extend(sub_phrases)

        # 3. Annotate phrase metadata & calculate pause_after_ms
        annotated_phrases = []
        total_count = len(phrases)

        for idx, phrase_text in enumerate(phrases):
            is_last = (idx == total_count - 1)
            pause_ms = 300 if is_last else 120

            # Check if phrase contains key entities
            contains_entity = False
            if entities:
                for cat, items in entities.items():
                    for item in items:
                        if item in phrase_text:
                            contains_entity = True
                            break

            # Slightly longer pause after entity phrases
            if contains_entity and not is_last:
                pause_ms = 150

            annotated_phrases.append({
                "phrase_id": idx + 1,
                "text": phrase_text,
                "pause_after_ms": pause_ms,
                "contains_entity": contains_entity,
                "contour": "rising_flat" if not is_last else "falling"
            })

        return annotated_phrases

    def _split_chunk_syntactically(self, chunk: str) -> List[str]:
        """Sub-splits a text chunk at syntactic verb/participle boundaries if longer than 35 chars."""
        if len(chunk) <= 35:
            return [chunk]

        pattern = r'(' + '|'.join(PHRASE_DELIMITERS) + r')'
        split_parts = re.split(pattern, chunk)

        refined = []
        current = ""
        for part in split_parts:
            if not part:
                continue
            current += part
            if any(re.search(r'\b' + d + r'\b', part) for d in [p.replace(r'\b', '') for p in PHRASE_DELIMITERS]):
                refined.append(current.strip())
                current = ""

        if current.strip():
            refined.append(current.strip())

        return refined if refined else [chunk]
