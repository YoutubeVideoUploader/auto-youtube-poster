"""
Presenter Markup Language Parser
Parses XML-style presenter tags (<intro>, <headline>, <important>, <detail>, <transition>, <question>, <outro>)
and generates structured speech segments with custom prosody attributes.
"""

import re
from typing import List, Dict, Any

DEFAULT_TAG_PRESETS = {
    "intro": {
        "speed": 1.05,
        "pitch_shift": 0.0,
        "pause_after_ms": 250,
        "description": "Engaging, high-energy presenter intro"
    },
    "headline": {
        "speed": 1.05,
        "pitch_shift": 0.0,
        "pause_after_ms": 300,
        "description": "Bold, emphatic news headline delivery"
    },
    "important": {
        "speed": 0.90,          # Slower speed for key facts & dates
        "pitch_shift": 0.0,
        "pause_after_ms": 250,
        "description": "Deliberate, measured emphasis on critical information"
    },
    "detail": {
        "speed": 1.00,
        "pitch_shift": 0.0,
        "pause_after_ms": 150,
        "description": "Standard informative presenter cadence"
    },
    "transition": {
        "speed": 1.05,
        "pitch_shift": 0.0,
        "pause_after_ms": 350,
        "description": "Smooth transition between news topics"
    },
    "section_intro": {
        "speed": 1.05,
        "pitch_shift": 0.0,
        "pause_after_ms": 350,
        "description": "Engaging section transition intro"
    },
    "question": {
        "speed": 0.98,
        "pitch_shift": 0.0,
        "pause_after_ms": 200,
        "description": "Interrogative cadence"
    },
    "outro": {
        "speed": 1.00,
        "pitch_shift": 0.0,
        "pause_after_ms": 400,
        "description": "Warm, descending closing cadence"
    }
}


class PresenterSegment:
    def __init__(
        self,
        text: str,
        tag: str = "detail",
        speed: float = 1.0,
        pitch_shift: float = 0.0,
        pause_after_ms: int = 300
    ):
        self.text = text.strip()
        self.tag = tag
        self.speed = speed
        self.pitch_shift = pitch_shift
        self.pause_after_ms = pause_after_ms

    def __repr__(self):
        return f"<Segment [{self.tag}] speed={self.speed} pause={self.pause_after_ms}ms: '{self.text[:30]}...'>"


class PresenterMarkupParser:
    def __init__(self):
        self.tag_presets = DEFAULT_TAG_PRESETS.copy()

    def parse(self, text: str) -> List[PresenterSegment]:
        """
        Parses text containing XML presenter tags into a list of PresenterSegment objects.
        If no tags are present, treats paragraphs as standard 'detail' or 'headline' segments.
        """
        # Pattern to match <tag>content</tag>
        pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        matches = list(pattern.finditer(text))

        segments = []

        if matches:
            for match in matches:
                tag_name = match.group(1).lower()
                content = match.group(2).strip()
                if not content:
                    continue

                preset = self.tag_presets.get(tag_name, self.tag_presets["detail"])
                segments.append(
                    PresenterSegment(
                        text=content,
                        tag=tag_name,
                        speed=preset["speed"],
                        pitch_shift=preset["pitch_shift"],
                        pause_after_ms=preset["pause_after_ms"]
                    )
                )
        else:
            # Fallback for plain text: split into paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for idx, p in enumerate(paragraphs):
                tag_name = "intro" if idx == 0 else "detail"
                preset = self.tag_presets[tag_name]
                segments.append(
                    PresenterSegment(
                        text=p,
                        tag=tag_name,
                        speed=preset["speed"],
                        pitch_shift=preset["pitch_shift"],
                        pause_after_ms=preset["pause_after_ms"]
                    )
                )

        return segments
