"""
Slide Preview Engine Module
Renders instant 1080p HD slide preview cards for each topic in the web dashboard
using PIL and exact rendering logic from generate_video_from_audio_and_images.py.
"""

import os
import re
import io
import requests
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PREVIEW_CACHE_DIR = OUTPUT_DIR / "preview_cache"
PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Import parsing & rendering helpers from generate_video_from_audio_and_images
import sys
sys.path.insert(0, str(BASE_DIR))

from generate_video_from_audio_and_images import (
    extract_table_data,
    create_table_slide,
    create_actor_collage_slide,
    TITLE_MAP
)
from generate_from_google_sheet import download_single_target
from preprocessing.pronunciation_dictionary import PronunciationDictionary

pron_dict = PronunciationDictionary()


class SlidePreviewEngine:
    def __init__(self):
        self.cache_dir = PREVIEW_CACHE_DIR

    def generate_topic_preview(
        self,
        section_name: str,
        topic_idx: int,
        topic_text: str,
        image_urls_str: str
    ) -> Dict[str, Any]:
        """
        Downloads topic image(s), extracts table data, and renders the 1080p preview slide image.
        Returns a dict containing preview image path, poster image path, metadata, and Malayalam text.
        """
        sec_slug = section_name.lower().replace(" ", "_")
        topic_dir = self.cache_dir / sec_slug / f"topic_{topic_idx:02d}"
        topic_dir.mkdir(parents=True, exist_ok=True)

        # Normalize English words to Malayalam script if needed
        clean_topic_text = pron_dict.replace_english_words(topic_text.strip())

        # Extract URLs
        urls = [u.strip() for u in re.split(r'[\r\n,]+', image_urls_str) if u.strip() and u.strip().lower() != 'nan']

        downloaded_paths = []
        for i, url in enumerate(urls, start=1):
            img_path = str(topic_dir / f"img_{i:02d}.jpg")
            if Path(img_path).exists() and Path(img_path).stat().st_size > 1000:
                downloaded_paths.append(img_path)
            else:
                if download_single_target(url, img_path):
                    downloaded_paths.append(img_path)

        is_ott = "ott" in sec_slug
        title_en, date_en, plat_en = extract_table_data(clean_topic_text, is_ott=is_ott)

        # Render 1080p Slide Graphic
        preview_slide_path = str(topic_dir / "preview_slide_1080p.jpg")

        try:
            create_table_slide(
                item_title=title_en,
                item_date=date_en,
                item_plat=plat_en,
                image_paths=downloaded_paths,
                output_path=preview_slide_path,
                is_ott=is_ott
            )
        except Exception as e:
            # Fallback to collage slide if split table slide hits edge-case format
            try:
                create_actor_collage_slide(
                    image_paths=downloaded_paths,
                    output_path=preview_slide_path
                )
            except Exception as e2:
                # Blank dark canvas fallback
                bg = Image.new("RGB", (1920, 1080), (20, 20, 35))
                bg.save(preview_slide_path, "JPEG", quality=95)

        poster_path = downloaded_paths[0] if downloaded_paths else None

        return {
            "topic_number": topic_idx,
            "title_en": title_en,
            "date_en": date_en,
            "plat_en": plat_en,
            "topic_text": clean_topic_text,
            "raw_text": topic_text,
            "preview_slide_path": preview_slide_path,
            "poster_path": poster_path,
            "downloaded_images": downloaded_paths,
            "image_count": len(downloaded_paths)
        }
