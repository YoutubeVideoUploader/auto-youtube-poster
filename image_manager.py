"""
Image Manager System for Malayalam Movie News Presenter
Manages persistent local image library under image_library/ (actors, directors, movies),
executes context-bound searches (Movie + Person), and enforces multi-stage image validation.
"""

import os
import re
import io
import urllib.parse
import requests
import urllib3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent
LIBRARY_DIR = BASE_DIR / "image_library"
ACTORS_DIR = LIBRARY_DIR / "actors"
DIRECTORS_DIR = LIBRARY_DIR / "directors"
MOVIES_DIR = LIBRARY_DIR / "movies"

# Ensure library directories exist
for d in [ACTORS_DIR, DIRECTORS_DIR, MOVIES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

# Master WIKI Disambiguation Map
WIKI_ENTITY_MAP = {
    'urvashi': 'Urvashi (actress)',
    'joju george': 'Joju George',
    'aishwarya lekshmi': 'Aishwarya Lekshmi',
    'vijayaraghavan': 'Vijayaraghavan (actor)',
    'shaji kailas': 'Shaji Kailas',
    'vani viswanath': 'Vani Viswanath',
    'murali gopy': 'Murali Gopy',
    'nivin pauly': 'Nivin Pauly',
    'rukmini vasanth': 'Rukmini Vasanth',
    'farook abdul rahiman': 'Farook Abdul Rahiman',
    'suriya': 'Suriya',
    'mamitha baiju': 'Mamitha Baiju',
    'biju menon': 'Biju Menon',
    'sajin gopu': 'Sajin Gopu',
    'nikhila vimal': 'Nikhila Vimal',
    'mohanlal': 'Mohanlal',
    'jude anthany joseph': 'Jude Anthany Joseph',
    'jeethu madhavan': 'Jithu Madhavan',
    'jithu madhavan': 'Jithu Madhavan',
    'nazlen': 'Naslen K. Gafoor',
    'nazlen k gafoor': 'Naslen K. Gafoor',
    'samvritha sunil': 'Samvritha Sunil',
    'dileesh pothan': 'Dileesh Pothan',
    'alphonse puthren': 'Alphonse Puthren',
}

TRUSTED_MEDIA_DOMAINS = [
    'wikimedia.org', 'wikipedia.org',
    'filmibeat.com', 'timesofindia.indiatimes.com', 'indianexpress.com',
    'thehindu.com', 'manoramaonline.com', 'mathrubhumi.com', 'keralakaumudi.com',
    'cinemaexpress.com', 'kerala9.com', 'behindwoods.com',
    'imdb.com', 'm3db.com', 'indiglamour.com', 'hifioasis.com',
    'starsunfolded.com', 'wikibio.in', 'bollywoodbiography.in',
    'outlookindia.com', 'pinkvilla.com', 'ndtv.com', 'onmanorama.com'
]

BAD_DOMAINS = [
    'nike.com', 'walmart', 'amazon', 'ebay', 'aliexpress', 'r10s.jp', 'shop', 'cart',
    'caiherang.com', 'bhg.com', 'vecteezy', 'pngtree', 'pngwing', 'canva', 'pgimgs.com',
    'g2crowd.com', 'stickpng.com', 'freepik.com', 'shutterstock', 'dreamstime', 'birdhelpful.com',
    'ytimg.com', 'youtube.com', 'blogspot.com', 'wixmp.com', 'rediff.com', 'pinimg.com'
]

BAD_KEYWORDS = [
    'logo', 'icon', 'poster', 'wallpaper', 'banner', 'shirt', 'shoe', 'dress', 'car',
    'building', 'house', 'room', 'interior', 'vector', 'drawing', 'sketch', 'product',
    'item', 'nest', 'egg', 'bird', 'peach', 'fish', 'jewelry', 'diagram', 'diagrams', 'money'
]


class ImageValidator:
    """Strictly validates images for resolution, aspect ratio, format, and content quality."""

    @staticmethod
    def is_valid_image(content: bytes, min_width: int = 250, min_height: int = 250) -> bool:
        """Returns True if content is a valid PIL image meeting minimum resolution requirements."""
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            img = Image.open(io.BytesIO(content))
            w, h = img.size
            if w < min_width or h < min_height:
                return False
            # Check extreme aspect ratio (e.g. ultra-thin banners)
            ratio = max(w / h, h / w)
            if ratio > 3.0:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def is_clean_url(url: str) -> bool:
        """Returns True if image URL does not contain blacklisted domain or object keywords."""
        url_lower = url.lower()
        if any(bd in url_lower for bd in BAD_DOMAINS):
            return False
        if any(bk in url_lower for bk in BAD_KEYWORDS):
            return False
        return True


class ImageManager:
    """Manages searching, caching, validating, and retrieving movie, actor, and director images."""

    def __init__(self):
        self.validator = ImageValidator()

    def _sanitize_name(self, name: str) -> str:
        """Sanitizes entity name for filesystem storage."""
        clean = re.sub(r'[^\w\s-]', '', name).strip()
        return re.sub(r'[\s-]+', '_', clean)

    def get_local_person_images(self, person_name: str) -> List[Path]:
        """Returns list of local image paths for a person if already present in library."""
        safe_name = self._sanitize_name(person_name)
        person_dir = ACTORS_DIR / safe_name
        if not person_dir.exists():
            person_dir = DIRECTORS_DIR / safe_name
        if person_dir.exists():
            imgs = sorted(list(person_dir.glob("*.jpg")) + list(person_dir.glob("*.png")) + list(person_dir.glob("*.webp")))
            if imgs:
                return imgs
        return []

    def get_local_movie_images(self, movie_name: str) -> List[Path]:
        """Returns list of local image paths for a movie if already present in library."""
        if not movie_name or movie_name.lower() in ['nan', 'none']:
            return []
        safe_name = self._sanitize_name(movie_name)
        movie_dir = MOVIES_DIR / safe_name
        if movie_dir.exists():
            imgs = sorted(list(movie_dir.glob("*.jpg")) + list(movie_dir.glob("*.png")) + list(movie_dir.glob("*.webp")))
            if imgs:
                return imgs
        return []

    def fetch_wikipedia_portrait(self, person_name: str) -> Optional[bytes]:
        """Scrapes official Wikipedia page directly for a person's portrait."""
        key = person_name.strip().lower()
        wiki_title = WIKI_ENTITY_MAP.get(key, person_name.strip())

        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(wiki_title.replace(' ', '_'))}"
        try:
            r = requests.get(page_url, headers=HTTP_HEADERS, verify=False, timeout=8)
            if r.status_code != 200:
                return None

            # 1. og:image
            m = re.search(r'<meta[^>]+property=[\"\']og:image[\"\'][^>]+content=[\"\']([^\"\'\s>]+)[\"\']', r.text, re.IGNORECASE)
            if not m:
                m = re.search(r'<meta[^>]+content=[\"\']([^\"\'\s>]+)[\"\'][^>]+property=[\"\']og:image[\"\']', r.text, re.IGNORECASE)

            img_url = m.group(1) if m else None

            # 2. Wikimedia Commons fallback inside page HTML
            if not img_url or 'Special:FilePath' in img_url:
                all_imgs = re.findall(r'//upload\.wikimedia\.org/wikipedia/(?:commons|en)/[^\"\'\s>]+\.(?:jpg|jpeg|png|webp)', r.text, re.IGNORECASE)
                valid_imgs = [
                    'https:' + i for i in all_imgs
                    if not any(b in i.lower() for b in ['icon', 'logo', 'flag', 'symbol', 'question', 'padlock', 'edit-clear', 'ambox', 'vip.svg'])
                ]
                if valid_imgs:
                    img_url = valid_imgs[0]

            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url

                r_img = requests.get(img_url, headers=HTTP_HEADERS, verify=False, timeout=10)
                if r_img.status_code == 200 and len(r_img.content) > 5000 and self.validator.is_valid_image(r_img.content):
                    print(f"    [WIKI PORTRAIT OK] {person_name} -> {img_url[:70]}")
                    return r_img.content
        except Exception as e:
            print(f"    [WIKI SCRAPE ERROR] {person_name}: {e}")

        return None

    def fetch_context_bound_person_image(self, person_name: str, movie_name: str = "") -> Optional[bytes]:
        """Searches Bing/Google with explicit Movie+Person context (e.g. 'Urvashi Aasha Malayalam film')."""
        clean_person = person_name.strip()
        clean_movie = movie_name.strip() if movie_name and movie_name.lower() != 'nan' else ""

        queries = []
        if clean_movie:
            queries.append(f'"{clean_person}" "{clean_movie}" Malayalam film photo')
            queries.append(f'"{clean_person}" "{clean_movie}" Malayalam photo')

        queries.extend([
            f'"{clean_person}" Malayalam actor photo filmibeat',
            f'"{clean_person}" Malayalam actress photo filmibeat',
            f'"{clean_person}" Malayalam director photo filmibeat',
            f'"{clean_person}" Malayalam portrait'
        ])

        for q in queries:
            search_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first=1&count=20"
            try:
                resp = requests.get(search_url, headers=HTTP_HEADERS, verify=False, timeout=8)
                murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png|webp)(?:[^&"<>\s]*)?)&quot;', resp.text, re.IGNORECASE)

                # Strictly allow ONLY trusted media domains (Wikipedia, Filmibeat, Times of India, Manorama, etc.)
                urls_to_try = [m for m in murls if any(dom in m.lower() for dom in TRUSTED_MEDIA_DOMAINS)]

                for img_url in urls_to_try:
                    if not self.validator.is_clean_url(img_url):
                        continue
                    try:
                        r_img = requests.get(img_url, headers=HTTP_HEADERS, verify=False, timeout=8)
                        if r_img.status_code == 200 and len(r_img.content) > 10000 and self.validator.is_valid_image(r_img.content):
                            print(f"    [CONTEXT PERSON PHOTO OK] '{clean_person}' -> {img_url[:70]}")
                            return r_img.content
                    except Exception:
                        continue
            except Exception:
                pass

        return None

    def fetch_movie_poster_image(self, movie_name: str, explicit_keywords: str = "") -> Optional[bytes]:
        """Searches for official Movie Poster / Teaser image."""
        if not movie_name or movie_name.lower() in ['nan', 'none']:
            return None

        clean_movie = movie_name.strip()
        from groq_extractor import _clean_movie_search_term
        search_term = _clean_movie_search_term(clean_movie)

        queries = []

        if explicit_keywords and explicit_keywords.lower() != 'nan':
            queries.append(f'{explicit_keywords} poster')

        queries.extend([
            f'"{search_term}" Malayalam movie poster filmibeat',
            f'"{search_term}" Malayalam film first look poster',
            f'"{search_term}" Malayalam movie poster'
        ])

        for q in queries:
            search_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first=1&count=20"
            try:
                resp = requests.get(search_url, headers=HTTP_HEADERS, verify=False, timeout=8)
                murls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?\.(?:jpg|jpeg|png|webp)(?:[^&"<>\s]*)?)&quot;', resp.text, re.IGNORECASE)

                # Strictly allow ONLY trusted media domains for movie posters
                urls_to_try = [m for m in murls if any(dom in m.lower() for dom in TRUSTED_MEDIA_DOMAINS)]

                for img_url in urls_to_try:
                    if not self.validator.is_clean_url(img_url):
                        continue
                    try:
                        r_img = requests.get(img_url, headers=HTTP_HEADERS, verify=False, timeout=8)
                        if r_img.status_code == 200 and len(r_img.content) > 15000 and self.validator.is_valid_image(r_img.content, min_width=300, min_height=300):
                            print(f"    [MOVIE POSTER OK] '{clean_movie}' -> {img_url[:70]}")
                            return r_img.content
                    except Exception:
                        continue
            except Exception:
                pass

        return None

    def get_or_download_person_photo(self, person_name: str, movie_name: str = "") -> Optional[Path]:
        """Retrieves local photo or downloads and commits to image_library/actors/."""
        person_str = person_name.strip()
        if not person_str or person_str.lower() in ['nan', 'none']:
            return None

        # If Column C target is a direct URL
        if person_str.startswith(('http://', 'https://')):
            if not self.validator.is_clean_url(person_str):
                return None
            try:
                r = requests.get(person_str, headers=HTTP_HEADERS, verify=False, timeout=10)
                if r.status_code == 200 and len(r.content) > 5000 and self.validator.is_valid_image(r.content):
                    url_name = person_str.split('/')[-1].split('?')[0]
                    safe_url_name = self._sanitize_name(url_name) or "url_photo"
                    target_dir = ACTORS_DIR / safe_url_name
                    target_dir.mkdir(parents=True, exist_ok=True)
                    save_path = target_dir / "001.jpg"
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    print(f"    [DIRECT URL IMAGE OK] {url_name} -> {save_path}")
                    return save_path
            except Exception as e:
                print(f"    [DIRECT URL ERROR] {e}")
            return None

        safe_name = self._sanitize_name(person_str)
        target_dir = ACTORS_DIR / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        local_files = list(target_dir.glob("*.jpg")) + list(target_dir.glob("*.png")) + list(target_dir.glob("*.webp"))
        if local_files:
            return local_files[0]

        # 1. Direct Wikipedia
        content = self.fetch_wikipedia_portrait(person_str)

        # 2. Context-bound search on trusted media domains
        if not content:
            content = self.fetch_context_bound_person_image(person_str, movie_name)

        if content:
            save_path = target_dir / "001.jpg"
            with open(save_path, "wb") as f:
                f.write(content)
            print(f"    [STORED TO LIBRARY] {person_str} -> {save_path}")
            return save_path

        return None

    def get_or_download_movie_poster(self, movie_name: str, explicit_keywords: str = "") -> Optional[Path]:
        """Retrieves local poster if already stored in image_library/movies/."""
        if not movie_name or movie_name.lower() in ['nan', 'none']:
            return None

        safe_name = self._sanitize_name(movie_name)
        target_dir = MOVIES_DIR / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        local_files = list(target_dir.glob("*.jpg")) + list(target_dir.glob("*.png")) + list(target_dir.glob("*.webp"))
        if local_files:
            return local_files[0]

        return None
