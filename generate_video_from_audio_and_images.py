"""
Malayalam Movie News Video Generator v3.4
Combines synthesized presenter WAV audio, segment metadata, and downloaded topic images
into a broadcast 1080p Full HD MP4 video using PIL and FFmpeg.
"""

import sys
import os
import json
import glob
import subprocess
import soundfile as sf
import textwrap
from pathlib import Path
from typing import Dict, Any, List
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw, ImageFont

# Force UTF-8 stdout encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config import OUTPUT_DIR, BGM_VOLUME

ASSETS_DIR = BASE_DIR / "assets"
INTRO_BANNER_PATH = str(ASSETS_DIR / "intro_banner.jpg")
OUTRO_BANNER_PATH = str(ASSETS_DIR / "outro_banner.jpg")
TRANSITION_BANNER_PATH = str(ASSETS_DIR / "transition_banner.jpg")
INTRO_DIR = OUTPUT_DIR / "Intro Video"


def get_intro_video_duration(video_path: Path) -> float:
    """Gets exact duration of an intro video file via ffprobe."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 10.0 if "Main Intro" in video_path.name else 4.04


def resolve_video_for_segment(seg: dict, item_data: dict, next_item_data: dict) -> Path:
    """Resolves section intro/outro MP4 video path for intro/section_intro/transition/outro segments."""
    seg_type = seg.get("type", "")
    seg_text = seg.get("text", "").lower()

    if seg_type == "intro":
        p = INTRO_DIR / "Main Intro.mp4"
        if p.exists():
            return p

    elif seg_type == "outro":
        for name in ["Outro Video.mp4", "Outro.mp4", "Main Outro.mp4"]:
            p = INTRO_DIR / name
            if p.exists():
                return p

    elif seg_type in ["section_intro", "transition"]:
        # 1. Match by segment text keywords first (most reliable Malayalam root stems)
        if "ഒടിടി" in seg_text or "സ്ട്രീമിംഗ്" in seg_text or "ott" in seg_text:
            p = INTRO_DIR / "OTT update Intro.mp4"
            if p.exists():
                return p
        elif "റിലീ" in seg_text or "തിയേ" in seg_text or "release" in seg_text or "theater" in seg_text:
            p = INTRO_DIR / "Theater Release Intro.mp4"
            if p.exists():
                return p
        elif "സിനിമ" in seg_text or "വാർത്ത" in seg_text or "അപ്ഡേറ്റ്" in seg_text or "movie" in seg_text or "ആദ്യം" in seg_text:
            p = INTRO_DIR / "Movie update Intro.mp4"
            if p.exists():
                return p

        # 2. Fallback to section_slug inspection
        sec = str(item_data.get("section_slug", "")).lower()
        next_sec = str(next_item_data.get("section_slug", "")).lower()

        if "ott" in sec or "ott" in next_sec:
            p = INTRO_DIR / "OTT update Intro.mp4"
            if p.exists():
                return p
        elif "release" in sec or "release" in next_sec:
            p = INTRO_DIR / "Theater Release Intro.mp4"
            if p.exists():
                return p
        else:
            p = INTRO_DIR / "Movie update Intro.mp4"
            if p.exists():
                return p

    return None


def create_fitted_banner_slide(banner_path: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Fits a custom 16:9 banner image perfectly into a 1920x1080 slide canvas.
    """
    if not Path(banner_path).exists():
        bg = Image.new("RGB", (width, height), (20, 20, 35))
        bg.save(output_path, "JPEG", quality=95)
        return str(output_path)

    img = Image.open(banner_path).convert("RGB")
    img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
    img_resized.save(output_path, "JPEG", quality=95)
    return str(output_path)


def create_outro_banner_slide(topic_items: list, banner_path: str, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Renders an Outro slide banner. If banner_path exists (assets/outro_banner.jpg), it uses it.
    Otherwise, creates a broadcast poster collage slide from topic_items and saves it to banner_path.
    """
    if Path(banner_path).exists():
        img = Image.open(banner_path).convert("RGB")
        img_resized = img.resize((width, height), Image.Resampling.LANCZOS)
        img_resized.save(output_path, "JPEG", quality=95)
        return str(output_path)

    all_imgs = []
    if topic_items:
        for item in topic_items:
            imgs = item.get("image_paths", []) or []
            if not imgs:
                p_path = item.get("movie_poster_path")
                if p_path:
                    imgs = [p_path]
            for p in imgs:
                if p and Path(p).exists() and p not in all_imgs:
                    all_imgs.append(p)

    if not all_imgs:
        if Path(INTRO_BANNER_PATH).exists():
            return create_fitted_banner_slide(INTRO_BANNER_PATH, output_path, width, height)
        bg = Image.new("RGB", (width, height), (15, 20, 35))
        bg.save(output_path, "JPEG", quality=95)
        bg.save(banner_path, "JPEG", quality=95)
        return str(output_path)

    step = max(1, len(all_imgs) // 4)
    selected_imgs = all_imgs[::step][:4]

    create_actor_collage_slide(selected_imgs, output_path, width, height)

    try:
        import shutil
        shutil.copy(output_path, banner_path)
        print(f"[OK] Generated custom outro banner poster: {banner_path}")
    except Exception as e:
        print(f"[!] Warning copying outro banner: {e}")

    return str(output_path)


def scale_image_to_fit(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scales an image proportionally to fit within max_w and max_h using Lanczos resampling and subtle sharpness/vibrancy enhancement."""
    w, h = im.size
    if w <= 0 or h <= 0:
        return im
    scale = min(max_w / w, max_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    resized = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    try:
        sharpener = ImageEnhance.Sharpness(resized)
        resized = sharpener.enhance(1.2)
        color_enhancer = ImageEnhance.Color(resized)
        resized = color_enhancer.enhance(1.05)
    except Exception:
        pass
    return resized


def create_actor_collage_slide(image_paths: list, output_path: str, width: int = 1920, height: int = 1080) -> str:
    """
    Creates a professional 1920x1080 photo collage slide containing 1 to 5+ actor portraits.
    """
    valid_paths = [p for p in image_paths if Path(p).exists()]
    if not valid_paths:
        bg = Image.new("RGB", (width, height), (20, 20, 35))
        bg.save(output_path, "JPEG", quality=95)
        return str(output_path)

    imgs = []
    for p in valid_paths:
        try:
            imgs.append(Image.open(p).convert("RGB"))
        except Exception:
            continue

    if not imgs:
        bg = Image.new("RGB", (width, height), (20, 20, 35))
        bg.save(output_path, "JPEG", quality=95)
        return str(output_path)

    # 1. Create Blurred Dark Background from first actor image
    first_img = imgs[0]
    img_aspect = first_img.width / first_img.height
    target_aspect = width / height
    if img_aspect > target_aspect:
        new_h = height
        new_w = int(height * img_aspect)
    else:
        new_w = width
        new_h = int(width / img_aspect)

    bg_resized = first_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    bg = bg_resized.crop((left, top, left + width, top + height))

    bg = bg.filter(ImageFilter.GaussianBlur(radius=45))
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.35)

    n = len(imgs)
    padding = 40

    if n == 1:
        max_h = height - 120
        max_w = width - 200
        fg = scale_image_to_fit(imgs[0], max_w, max_h)
        cards = [(fg, (width - fg.width) // 2, (height - fg.height) // 2)]

    elif n == 2:
        card_w = (width - 3 * padding) // 2
        card_h = height - 160
        cards = []
        for i, im in enumerate(imgs[:2]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            cx = padding + i * (card_w + padding) + (card_w - c_im.width) // 2
            cy = (height - c_im.height) // 2
            cards.append((c_im, cx, cy))

    elif n == 3:
        card_w = (width - 4 * padding) // 3
        card_h = height - 180
        cards = []
        for i, im in enumerate(imgs[:3]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            cx = padding + i * (card_w + padding) + (card_w - c_im.width) // 2
            cy = (height - c_im.height) // 2
            cards.append((c_im, cx, cy))

    elif n == 4:
        card_w = (width - 3 * padding) // 2
        card_h = (height - 3 * padding) // 2
        cards = []
        positions = [
            (padding, padding),
            (padding * 2 + card_w, padding),
            (padding, padding * 2 + card_h),
            (padding * 2 + card_w, padding * 2 + card_h)
        ]
        for i, im in enumerate(imgs[:4]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            px, py = positions[i]
            cx = px + (card_w - c_im.width) // 2
            cy = py + (card_h - c_im.height) // 2
            cards.append((c_im, cx, cy))

    else:
        row1_count = 3
        row2_count = min(n - 3, 3)

        card_w1 = (width - (row1_count + 1) * padding) // row1_count
        card_h = (height - 3 * padding) // 2

        cards = []
        for i, im in enumerate(imgs[:3]):
            c_im = scale_image_to_fit(im, card_w1, card_h)
            cx = padding + i * (card_w1 + padding) + (card_w1 - c_im.width) // 2
            cy = padding + (card_h - c_im.height) // 2
            cards.append((c_im, cx, cy))

        card_w2 = (width - (row2_count + 1) * padding) // row2_count
        row2_start_x = (width - (row2_count * card_w2 + (row2_count - 1) * padding)) // 2
        for i, im in enumerate(imgs[3:3+row2_count]):
            c_im = scale_image_to_fit(im, card_w2, card_h)
            cx = row2_start_x + i * (card_w2 + padding) + (card_w2 - c_im.width) // 2
            cy = padding * 2 + card_h + (card_h - c_im.height) // 2
            cards.append((c_im, cx, cy))

    shadow_pad = 15
    for c_im, cx, cy in cards:
        shadow = Image.new("RGBA", (c_im.width + shadow_pad*2, c_im.height + shadow_pad*2), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(shadow)
        s_draw.rectangle([shadow_pad//2, shadow_pad//2, c_im.width + shadow_pad + shadow_pad//2, c_im.height + shadow_pad + shadow_pad//2], fill=(0, 0, 0, 160))
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))

        bg.paste(shadow, (cx - shadow_pad, cy - shadow_pad), shadow)
        bg.paste(c_im, (cx, cy))

    bg.save(output_path, "JPEG", quality=95)
    return str(output_path)


MONTH_MAP = {
    'സെപ്റ്റംബർ': 'September', 'സെപ്തംബർ': 'September', 'ഓഗസ്റ്റ്': 'August', 'ആഗസ്റ്റ്': 'August',
    'ഒക്ടോബർ': 'October', 'നവംബർ': 'November', 'ഡിസംബർ': 'December', 'ജനുവരി': 'January',
    'ഫെബ്രുവരി': 'February', 'മാർച്ച്': 'March', 'ഏപ്രിൽ': 'April', 'മേയ്': 'May', 'മെയ്': 'May',
    'ജൂൺ': 'June', 'ജൂലൈ': 'July'
}

PLATFORM_MAP = {
    'പ്രൈം': 'Prime Video', 'prime': 'Prime Video',
    'സീ': 'ZEE5', 'zee': 'ZEE5',
    'നെറ്റ്ഫ്ലിക്': 'Netflix', 'netflix': 'Netflix',
    'ഹോട്ട്സ്റ്റാർ': 'JioHotstar', 'hotstar': 'JioHotstar',
    'സൺ': 'Sun NXT', 'sun': 'Sun NXT',
    'മനോരമ': 'ManoramaMAX', 'sony': 'SonyLIV'
}

TITLE_MAP = {
    'ധൂമകേതു': 'Dhoomakethu',
    'ഇറ്റ്സ് എ മെഡിക്കൽ മിറക്കിൾ': 'Its A Medical Miracle',
    'ഓട്ടംതുള്ളൽ': 'Ottamthullal',
    'ആരം': 'Aaram',
    'ലോ ആൻഡ് ഓർഡർ': 'Law & Order',
    'ഭാസ്കരാഭരണം': 'Bhaskarabharanam',
    'മാജിക് മഷ്റൂംസ്': 'Magic Mushrooms',
    'വരവ്': 'Varavu',
    'വിശ്വനാഥ് ആൻഡ് സൺസ്': 'Viswanath & Sons',
    'പ്രിൻസ് ഓഫ് മോളിവുഡ്': 'Prince of Mollywood',
    'വിവാഹ്': 'Vivah',
    'തുടക്കം': 'Thudakkam',
    'ആശ': 'Aasha',
    'അവറാച്ചൻ ആൻഡ് സൺസ്': 'Avarachan & Sons',
    'തേന്മാവിൻ കൊമ്പത്ത്': 'Thenmavin Kombath',
    'മേള': 'Mela',
    'വിശുദ്ധ സെമിനാരി': 'Visudha Seminary',
    'എൽ 370': 'L370',
    'എൽ മൂന്നൂറ്റി ഏഴുപത്': 'L370',
    'സീൻ': 'Scene',
    'ബെത്‌ലഹേം കുടുംബ യൂണിറ്റ്': 'Bethlehem Kudumba Unit'
}


NUMBER_WORD_MAP = {
    'ഒന്ന്': '1', 'ഒന്നിന്': '1',
    'രണ്ട്': '2', 'രണ്ടിന്': '2',
    'മൂന്ന്': '3', 'മൂന്നിന്': '3',
    'നാല്': '4', 'നാലിന്': '4',
    'അഞ്ച്': '5', 'അഞ്ചിന്': '5',
    'ആറ്': '6', 'ആറിന്': '6',
    'ഏഴ്': '7', 'ഏഴിന്': '7',
    'എട്ട്': '8', 'എട്ടിന്': '8',
    'ഒൻപത്': '9', 'ഒമ്പത്': '9', 'ഒൻപതിന്': '9', 'ഒമ്പതിന്': '9',
    'പത്ത്': '10', 'പത്തിന്': '10',
    'പതിനൊന്ന്': '11', 'പതിനൊന്നിന്': '11',
    'പന്ത്രണ്ട്': '12', 'പന്ത്രണ്ടിന്': '12',
    'പതിമൂന്ന്': '13', 'പതിമൂന്നിന്': '13',
    'പതിനാല്': '14', 'പതിനാലിന്': '14',
    'പതിനഞ്ച്': '15', 'പതിനഞ്ചിന്': '15',
    'പതിനാറ്': '16', 'പതിനാറിന്': '16',
    'പതിനേഴ്': '17', 'പതിനേഴിന്': '17',
    'പതിനെട്ട്': '18', 'പതിനെട്ടിന്': '18',
    'പത്തൊൻപത്': '19', 'പത്തൊമ്പത്': '19', 'പത്തൊൻപതിന്': '19',
    'ഇരുപത്': '20', 'ഇരുപതിന്': '20',
    'ഇരുപത്തൊന്ന്': '21', 'ഇരുപത്തൊന്നിന്': '21',
    'ഇരുപത്തിരണ്ട്': '22', 'ഇരുപത്തിരണ്ടിന്': '22',
    'ഇരുപത്തിമൂന്ന്': '23', 'ഇരുപത്തിമൂന്നിന്': '23',
    'ഇരുപത്തിനാല്': '24', 'ഇരുപത്തിനാലിന്': '24',
    'ഇരുപത്തിയഞ്ച്': '25', 'ഇരുപത്തിയഞ്ചിന്': '25', 'ഇരുപത്തഞ്ച്': '25', 'ഇരുപത്തഞ്ചിന്': '25',
    'ഇരുപത്തിയാറ്': '26', 'ഇരുപത്തിയാറിന്': '26',
    'ഇരുപത്തിഏഴ്': '27', 'ഇരുപത്തിഏഴിന്': '27',
    'ഇരുപത്തിഎട്ട്': '28', 'ഇരുപത്തിഎട്ടിന്': '28',
    'ഇരുപത്തൊൻപത്': '29', 'ഇരുപത്തൊമ്പത്': '29', 'ഇരുപത്തൊൻപതിന്': '29',
    'முപ്പത്': '30', 'മുപ്പത്': '30', 'മുപ്പതിന്': '30',
    'മുപ്പത്തൊന്ന്': '31', 'മുപ്പത്തൊന്നിന്': '31'
}

SORTED_NUMBER_WORDS = sorted(NUMBER_WORD_MAP.items(), key=lambda x: len(x[0]), reverse=True)


CONSONANTS = {
    'ക': 'k', 'ഖ': 'kh', 'ഗ': 'g', 'ഘ': 'gh', 'ങ': 'ng',
    'ച': 'ch', 'ഛ': 'chh', 'ജ': 'j', 'ഝ': 'jh', 'ഞ': 'ny',
    'ട': 't', 'ഠ': 'th', 'ഡ': 'd', 'ഢ': 'dh', 'ണ': 'n',
    'ത': 'th', 'ഥ': 'thh', 'ദ': 'd', 'ധ': 'dh', 'ന': 'n',
    'പ': 'p', 'ഫ': 'ph', 'ബ': 'b', 'ഭ': 'bh', 'മ': 'm',
    'യ': 'y', 'ര': 'r', 'ല': 'l', 'വ': 'v', 'ശ': 'sh',
    'ഷ': 'sh', 'സ': 's', 'ഹ': 'h', 'ള': 'l', 'ഴ': 'zh', 'റ': 'r'
}

VOWEL_SIGNS = {
    'ാ': 'a', 'ി': 'i', 'ീ': 'ee', 'ു': 'u', 'ൂ': 'oo', 'ൃ': 'ri',
    'െ': 'e', 'േ': 'e', 'ൈ': 'ai', 'ൊ': 'o', 'ോ': 'o', 'ൗ': 'au',
    '്': '', 'ം': 'm', 'ഃ': 'h'
}

INDEPENDENT_VOWELS = {
    'അ': 'A', 'ആ': 'Aa', 'ഇ': 'I', 'ഈ': 'Ee', 'ഉ': 'U', 'ഊ': 'Oo', 'ഋ': 'Ri',
    'എ': 'E', 'ഏ': 'Ea', 'ഐ': 'Ai', 'ഒ': 'O', 'ഓ': 'Oo', 'ഔ': 'Au'
}

CHILLU = {
    'ൻ': 'n', 'ർ': 'r', 'ൽ': 'l', 'ൾ': 'l', 'ക്': 'k', 'ൺ': 'n'
}

def transliterate_malayalam_to_english(text: str) -> str:
    """Phonetically transliterates Malayalam script to clean Latin English script."""
    import re
    if not text:
        return ""
    if re.search(r'[a-zA-Z]', text):
        clean_en = re.sub(r'[^a-zA-Z0-9\s\&]', '', text).strip()
        return clean_en.title() if clean_en else text.strip()

    res = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in CHILLU:
            res.append(CHILLU[ch])
            i += 1
        elif ch in INDEPENDENT_VOWELS:
            res.append(INDEPENDENT_VOWELS[ch])
            i += 1
        elif ch in CONSONANTS:
            base_c = CONSONANTS[ch]
            if i + 1 < n and text[i + 1] in VOWEL_SIGNS:
                vs = VOWEL_SIGNS[text[i + 1]]
                res.append(base_c + vs)
                i += 2
            else:
                res.append(base_c + 'a')
                i += 1
        elif ch in VOWEL_SIGNS:
            res.append(VOWEL_SIGNS[ch])
            i += 1
        else:
            res.append(ch)
            i += 1

    clean = "".join(res)
    clean = re.sub(r'[^a-zA-Z0-9\s\&]', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean.title() if clean else text.strip()


def extract_table_data(topic_text: str, is_ott: bool = False, topic_headline: str = "", release_date: str = "", ott_platform: str = ""):
    """
    Extracts English Movie Name, Release Date, and OTT Platform from Malayalam topic text.
    Uses explicit parameters if available, with 4-layer fallback strategy for unparsed text.
    """
    import re

    title_raw = ""

    # Strategy 1: Explicit Topic Headline parameter
    if topic_headline and topic_headline.strip() and topic_headline.strip().lower() != 'nan':
        title_raw = topic_headline.strip()

    # Strategy 2: Quoted text in topic_text
    if not title_raw:
        m = re.search(r'[‘\'\"“]([^’\'\"”]+)[’\'\"”]', topic_text)
        if m:
            title_raw = m.group(1).strip()

    # Strategy 2.5: Search known movie titles in TITLE_MAP directly inside topic_text
    if not title_raw:
        sorted_titles = sorted(TITLE_MAP.keys(), key=len, reverse=True)
        for ml_title in sorted_titles:
            if ml_title in topic_text:
                title_raw = ml_title
                break

    # Strategy 3: Keyword Pattern Matching for unquoted movie titles
    if not title_raw:
        m_enna = re.search(r'([A-Za-z0-9\u0D00-\u0D7F]{2,25})\s+എന്ന\s+(?:പുതിയ\s+)?(?:ചിത്രം|സിനിമ|ഫിലിം|മൂവി)', topic_text)
        if m_enna:
            title_raw = m_enna.group(1).strip()

        if not title_raw:
            m_after = re.search(r'(?:ചിത്രം|സിനിമ|ഫിലിം|മൂവി|ചിത്രമായ|സിനിമയായ)\s+([A-Za-z0-9\u0D00-\u0D7F]{2,25})', topic_text)
            if m_after:
                t_cand = m_after.group(1).strip()
                if t_cand not in ['റിലീസിന്', 'സെപ്റ്റംബർ', 'പ്രധാന', 'ഈ', 'ഒരു', 'പുതിയ', 'ഒക്ടോബറിൽ', 'തിയേറ്ററുകളിൽ']:
                    title_raw = t_cand

        if not title_raw:
            km = re.search(r'([A-Za-z0-9\u0D00-\u0D7F]{2,25})\s+(?:ചിത്രം|സിനിമ|ഫിലിം|മൂവി)', topic_text)
            if km:
                t_cand = km.group(1).strip()
                if t_cand not in ['പുതിയ', 'ഒരു', 'മറ്റൊരു', 'ബ്രിട്ടീഷ്']:
                    title_raw = t_cand

    # Strategy 4: Fallback to first few words of topic text if still empty
    if not title_raw or title_raw.lower() in ['nan', 'none', 'movie update']:
        first_words = topic_text.strip().split()
        if len(first_words) >= 2:
            title_raw = " ".join(first_words[:3])
        else:
            title_raw = 'Movie Update'

    title_raw = title_raw.strip(".,;:|'\"------------- ")

    if title_raw in TITLE_MAP:
        title_en = TITLE_MAP[title_raw]
    else:
        matched = None
        for k_ml, v_en in TITLE_MAP.items():
            if k_ml in title_raw or title_raw in k_ml:
                matched = v_en
                break
        if matched:
            title_en = matched
        else:
            title_en = transliterate_malayalam_to_english(title_raw)

    if not title_en or len(title_en) < 2:
        title_en = "Movie Update"

    date_en = 'Coming Soon'
    if release_date and release_date.strip() and release_date.strip().lower() != 'nan':
        date_en = release_date.strip()
    else:
        for ml_m, en_m in MONTH_MAP.items():
            if ml_m in topic_text:
                dm = re.search(rf'{ml_m}\s*(\d{{1,2}})', topic_text)
                if dm:
                    date_en = f'{en_m} {dm.group(1)}'
                    break

                dm_before = re.search(rf'(\d{{1,2}})\s*{ml_m}', topic_text)
                if dm_before:
                    date_en = f'{en_m} {dm_before.group(1)}'
                    break

                found_day = None
                for w_ml, d_num in SORTED_NUMBER_WORDS:
                    if w_ml in topic_text:
                        found_day = d_num
                        break
                if found_day:
                    date_en = f'{en_m} {found_day}'
                    break

    plat_en = 'OTT'
    if ott_platform and ott_platform.strip() and ott_platform.strip().lower() != 'nan':
        plat_en = ott_platform.strip()
    elif is_ott:
        for ml_p, en_p in PLATFORM_MAP.items():
            if ml_p.lower() in topic_text.lower():
                plat_en = en_p
                break

    return title_en, date_en, plat_en


def create_mini_cell_collage(image_paths: list, cell_w: int, cell_h: int) -> Image.Image:
    """
    Creates a mini collage for table cells:
    - 1 image: Single scaled image
    - 2 images: 2 side-by-side images
    - 3 images: 3 side-by-side images
    - 4+ images: 2x2 grid of images
    """
    valid_paths = [p for p in image_paths if Path(p).exists()]
    if not valid_paths:
        return Image.new("RGB", (cell_w, cell_h), (20, 25, 40))

    imgs = []
    for p in valid_paths:
        try:
            imgs.append(Image.open(p).convert("RGB"))
        except Exception:
            continue

    if not imgs:
        return Image.new("RGB", (cell_w, cell_h), (20, 25, 40))

    n = len(imgs)
    canvas = Image.new("RGBA", (cell_w, cell_h), (0, 0, 0, 0))
    padding = 10

    if n == 1:
        c_im = scale_image_to_fit(imgs[0], cell_w, cell_h)
        cx = (cell_w - c_im.width) // 2
        cy = (cell_h - c_im.height) // 2
        canvas.paste(c_im, (cx, cy))

    elif n == 2:
        card_w = (cell_w - 3 * padding) // 2
        card_h = cell_h - 2 * padding
        for i, im in enumerate(imgs[:2]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            cx = padding + i * (card_w + padding) + (card_w - c_im.width) // 2
            cy = padding + (card_h - c_im.height) // 2
            canvas.paste(c_im, (cx, cy))

    elif n == 3:
        card_w = (cell_w - 4 * padding) // 3
        card_h = cell_h - 2 * padding
        for i, im in enumerate(imgs[:3]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            cx = padding + i * (card_w + padding) + (card_w - c_im.width) // 2
            cy = padding + (card_h - c_im.height) // 2
            canvas.paste(c_im, (cx, cy))

    else:
        card_w = (cell_w - 3 * padding) // 2
        card_h = (cell_h - 3 * padding) // 2
        positions = [
            (padding, padding),
            (padding * 2 + card_w, padding),
            (padding, padding * 2 + card_h),
            (padding * 2 + card_w, padding * 2 + card_h)
        ]
        for i, im in enumerate(imgs[:4]):
            c_im = scale_image_to_fit(im, card_w, card_h)
            px, py = positions[i]
            cx = px + (card_w - c_im.width) // 2
            cy = py + (card_h - c_im.height) // 2
            canvas.paste(c_im, (cx, cy))

    return canvas.convert("RGB")


def get_font(size: int, bold: bool = True):
    font_candidates = [
        "C:/Windows/Fonts/NirmalaB.ttf" if bold else "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "FreeSansBold.ttf" if bold else "FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for fn in font_candidates:
        try:
            return ImageFont.truetype(fn, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def draw_section_countdown_badge(
    image_path: str,
    label_text: str,
    rem_sec: float,
    border_color: tuple = (255, 215, 0),
    accent_color: tuple = (255, 215, 0),
    top_y: int = 40
) -> str:
    """
    Renders a broadcast countdown timer badge in PIL with 100% perfect baseline alignment,
    clean spacing, zero box artifacts, and exact symmetric padding.
    """
    if not label_text or rem_sec is None:
        return image_path

    try:
        img = Image.open(image_path).convert("RGBA")
        font = get_font(32, bold=True)

        m = max(0, int(rem_sec)) // 60
        s = max(0, int(rem_sec)) % 60
        time_str = f"{m:02d}:{s:02d}"

        display_label = label_text.strip() + " "

        dummy = Image.new("RGBA", (1, 1))
        d_draw = ImageDraw.Draw(dummy)

        l_bbox = d_draw.textbbox((0, 0), display_label, font=font)
        l_w = l_bbox[2] - l_bbox[0]
        l_h = l_bbox[3] - l_bbox[1]

        t_bbox = d_draw.textbbox((0, 0), time_str, font=font)
        t_w = t_bbox[2] - t_bbox[0]
        t_h = t_bbox[3] - t_bbox[1]

        total_tw = l_w + t_w
        th = max(l_h, t_h)

        pad_x = 28
        pad_y = 16
        badge_w = total_tw + pad_x * 2
        badge_h = th + pad_y * 2

        width, height = img.size
        right_x = width - 40
        left_x = right_x - badge_w

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)

        rect = [left_x, top_y, right_x, top_y + badge_h]
        # Dark semi-transparent pill box with 4px border
        o_draw.rounded_rectangle(rect, radius=14, fill=(15, 20, 35, 240), outline=border_color, width=4)

        center_y = top_y + badge_h / 2

        # White label text centered vertically in box
        o_draw.text((left_x + pad_x, center_y), display_label, font=font, fill=(255, 255, 255), anchor="lm")
        # Accent-colored timer digits centered vertically in box
        o_draw.text((left_x + pad_x + l_w, center_y), time_str, font=font, fill=accent_color, anchor="lm")

        final_img = Image.alpha_composite(img, overlay).convert("RGB")
        final_img.save(image_path, "JPEG", quality=95)
    except Exception as e:
        print(f"[!] Warning drawing countdown badge on {image_path}: {e}")
    return image_path




def create_headline_banner_overlay(headline_text: str, output_path: str, height: int = 125) -> tuple:
    """
    Creates a broadcast PNG lower-third headline banner image with transparent background.
    Used exclusively for Movie Updates slide animation.
    Calculates dynamic banner width and auto-wraps text into 2 lines if long to prevent overflowing video bounds.
    Returns (output_path_str, box_w).
    """
    display_text = headline_text.strip()
    badge_font = get_font(20, bold=True)

    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)

    badge_bbox = dummy_draw.textbbox((0, 0), "CINEMA UPDATE", font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0]

    font_size = 40
    title_font = get_font(font_size, bold=True)
    text_bbox = dummy_draw.textbbox((0, 0), display_text, font=title_font)
    single_line_w = text_bbox[2] - text_bbox[0]

    lines = [display_text]
    line_height = 42

    if single_line_w > 1600 or len(display_text) > 42:
        font_size = 30
        title_font = get_font(font_size, bold=True)
        wrapped = textwrap.wrap(display_text, width=42)
        if len(wrapped) > 2:
            lines = [wrapped[0], " ".join(wrapped[1:])]
        else:
            lines = wrapped
        height = 155
        line_height = 36

    max_line_w = 0
    for line in lines:
        l_bbox = dummy_draw.textbbox((0, 0), line, font=title_font)
        w = l_bbox[2] - l_bbox[0]
        if w > max_line_w:
            max_line_w = w

    content_w = max(max_line_w, badge_w)
    box_w = max(420, min(1820, int(content_w) + 70))

    canvas = Image.new("RGBA", (box_w, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Dark semi-transparent rounded container
    rect = [0, 0, box_w, height]
    draw.rounded_rectangle(rect, radius=12, fill=(18, 18, 35, 235), outline=(255, 42, 75), width=3)

    # 2. Left vertical red accent bar
    draw.rounded_rectangle([0, 0, 14, height], radius=6, fill=(255, 42, 75))

    # 3. Small Category Badge: "CINEMA UPDATE"
    draw.text((30, 12), "CINEMA UPDATE", font=badge_font, fill=(255, 215, 0))

    # 4. Headline Text (1 or 2 lines)
    if len(lines) == 1:
        draw.text((30, 48), lines[0], font=title_font, fill=(255, 255, 255))
    else:
        y_pos = 46
        for line in lines[:2]:
            draw.text((30, y_pos), line, font=title_font, fill=(255, 255, 255))
            y_pos += line_height

    canvas.save(output_path, "PNG")
    return str(output_path), box_w


def create_table_slide(topic_text: str, image_paths: list, output_path: str, section_slug: str, width: int = 1920, height: int = 1080, topic_headline: str = "", release_date: str = "", ott_platform: str = "") -> str:
    """
    Renders a broadcast 2-row table card slide:
    - Release Updates: Row 1 (Merged Title), Row 2 [Col 1: Image Collage | Col 2: Date]
    - OTT Updates: Row 1 (Merged Title), Row 2 [Col 1: Image Collage | Col 2: Platform | Col 3: Date]
    """
    is_ott = ('ott' in section_slug.lower())
    title_en, date_en, plat_en = extract_table_data(topic_text, is_ott=is_ott, topic_headline=topic_headline, release_date=release_date, ott_platform=ott_platform)

    valid_paths = [p for p in image_paths if Path(p).exists()]
    poster_img = Image.open(valid_paths[0]).convert('RGB') if valid_paths else Image.new('RGB', (400, 600), (30, 35, 50))

    # Background
    bg = poster_img.resize((width, height), Image.Resampling.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=50))
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.25)

    draw = ImageDraw.Draw(bg)

    font_label = get_font(36, bold=True)
    font_val = get_font(52, bold=True)
    font_sec = get_font(38, bold=True)

    # Section Top Badge
    sec_title = 'OTT STREAMING UPDATE' if is_ott else 'THEATRICAL RELEASE UPDATE'
    draw.rectangle([0, 0, width, 70], fill=(15, 20, 35))
    draw.text((width // 2, 35), sec_title, font=font_sec, fill=(255, 215, 0), anchor='mm')

    if not is_ott:
        # 2-Row, 2-Column Table for Release Updates
        box_w, box_h = 1400, 720
        bx, by = (width - box_w) // 2, 220
        header_h = 110

        # Outer Border & Row 1 Header
        draw.rectangle([bx - 4, by - 4, bx + box_w + 4, by + box_h + 4], outline=(255, 215, 0), width=3)
        draw.rectangle([bx, by, bx + box_w, by + header_h], fill=(30, 45, 80))

        # Row 1 Title Text Wrapping & Dynamic Scaling
        title_text = title_en.upper()
        t_font = get_font(52, bold=True)
        t_bbox = draw.textbbox((0, 0), title_text, font=t_font)
        t_w = t_bbox[2] - t_bbox[0]

        if t_w > box_w - 80 or len(title_text) > 28:
            t_font = get_font(34, bold=True)
            wrapped_t = textwrap.wrap(title_text, width=30)
            t_lines = [wrapped_t[0], " ".join(wrapped_t[1:])] if len(wrapped_t) > 2 else wrapped_t
            y_start = by + (header_h - (len(t_lines) * 36)) // 2 + 10
            for line in t_lines:
                draw.text((bx + box_w // 2, y_start), line, font=t_font, fill=(255, 255, 255), anchor='mm')
                y_start += 36
        else:
            draw.text((bx + box_w // 2, by + header_h // 2), title_text, font=t_font, fill=(255, 255, 255), anchor='mm')

        # Row 2 (2 Columns)
        r2_by = by + header_h
        r2_h = box_h - header_h
        col1_w = 580
        col2_w = box_w - col1_w

        # Col 1: Poster / Collage Image Cell
        draw.rectangle([bx, r2_by, bx + col1_w, r2_by + r2_h], fill=(15, 20, 35), outline=(60, 70, 100), width=2)
        c_poster = create_mini_cell_collage(valid_paths, col1_w - 40, r2_h - 40)
        px = bx + (col1_w - c_poster.width) // 2
        py = r2_by + (r2_h - c_poster.height) // 2
        bg.paste(c_poster, (px, py))

        # Col 2: Date
        c2_x = bx + col1_w
        draw.rectangle([c2_x, r2_by, c2_x + col2_w, r2_by + r2_h], fill=(22, 28, 48), outline=(60, 70, 100), width=2)
        draw.text((c2_x + col2_w // 2, r2_by + r2_h // 2 - 40), 'RELEASE DATE', font=font_label, fill=(255, 215, 0), anchor='mm')
        draw.text((c2_x + col2_w // 2, r2_by + r2_h // 2 + 30), date_en, font=font_val, fill=(255, 255, 255), anchor='mm')

    else:
        # 2-Row, 3-Column Table for OTT Updates
        box_w, box_h = 1600, 720
        bx, by = (width - box_w) // 2, 220
        header_h = 110

        draw.rectangle([bx - 4, by - 4, bx + box_w + 4, by + box_h + 4], outline=(0, 229, 255), width=3)
        draw.rectangle([bx, by, bx + box_w, by + header_h], fill=(20, 40, 75))

        # Merged Row 1 Header Text Wrapping & Dynamic Scaling
        title_text = title_en.upper()
        t_font = get_font(52, bold=True)
        t_bbox = draw.textbbox((0, 0), title_text, font=t_font)
        t_w = t_bbox[2] - t_bbox[0]

        if t_w > box_w - 80 or len(title_text) > 32:
            t_font = get_font(34, bold=True)
            wrapped_t = textwrap.wrap(title_text, width=34)
            t_lines = [wrapped_t[0], " ".join(wrapped_t[1:])] if len(wrapped_t) > 2 else wrapped_t
            y_start = by + (header_h - (len(t_lines) * 36)) // 2 + 10
            for line in t_lines:
                draw.text((bx + box_w // 2, y_start), line, font=t_font, fill=(255, 255, 255), anchor='mm')
                y_start += 36
        else:
            draw.text((bx + box_w // 2, by + header_h // 2), title_text, font=t_font, fill=(255, 255, 255), anchor='mm')

        # Row 2 (3 Columns)
        r2_by = by + header_h
        r2_h = box_h - header_h
        col_w = box_w // 3

        # Col 1: Poster / Collage Image Cell
        draw.rectangle([bx, r2_by, bx + col_w, r2_by + r2_h], fill=(15, 20, 35), outline=(50, 75, 110), width=2)
        c_poster = create_mini_cell_collage(valid_paths, col_w - 40, r2_h - 40)
        px = bx + (col_w - c_poster.width) // 2
        py = r2_by + (r2_h - c_poster.height) // 2
        bg.paste(c_poster, (px, py))

        # Col 2: Platform
        c2_x = bx + col_w
        draw.rectangle([c2_x, r2_by, c2_x + col_w, r2_by + r2_h], fill=(20, 28, 52), outline=(50, 75, 110), width=2)
        draw.text((c2_x + col_w // 2, r2_by + r2_h // 2 - 40), 'PLATFORM', font=font_label, fill=(0, 229, 255), anchor='mm')
        draw.text((c2_x + col_w // 2, r2_by + r2_h // 2 + 30), plat_en, font=font_val, fill=(255, 255, 255), anchor='mm')

        # Col 3: Date
        c3_x = bx + col_w * 2
        draw.rectangle([c3_x, r2_by, c3_x + col_w, r2_by + r2_h], fill=(20, 28, 52), outline=(50, 75, 110), width=2)
        draw.text((c3_x + col_w // 2, r2_by + r2_h // 2 - 40), 'RELEASE DATE', font=font_label, fill=(255, 215, 0), anchor='mm')
        draw.text((c3_x + col_w // 2, r2_by + r2_h // 2 + 30), date_en, font=font_val, fill=(255, 255, 255), anchor='mm')

    bg.save(output_path, "JPEG", quality=95)
    return str(output_path)


def find_latest_audio_and_json():
    """Auto-detects the newest generated WAV and JSON files in OUTPUT_DIR."""
    wav_files = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*.wav"), key=os.path.getmtime, reverse=True)
    json_files = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*.json"), key=os.path.getmtime, reverse=True)

    # Exclude qa report json
    json_files = [f for f in json_files if not f.name.endswith("_qa_report.json")]

    latest_wav = str(wav_files[0]) if wav_files else None
    latest_json = str(json_files[0]) if json_files else None

    return latest_wav, latest_json


def generate_video(
    audio_path: str = None,
    metadata_json_path: str = None,
    output_video_path: str = None
) -> str:
    """
    Reads audio metadata and segment images to render a high quality 1080p presentation video.
    """
    auto_wav, auto_json = find_latest_audio_and_json()

    if not audio_path:
        audio_path = auto_wav
    if not metadata_json_path:
        metadata_json_path = auto_json

    print("=" * 70)
    print(f"[*] Generating Presenter Video Presentation (1080p Full HD Collages)")
    print(f"    Audio Source   : {audio_path}")
    print(f"    Metadata Source: {metadata_json_path}")
    print("=" * 70)
    sys.stdout.flush()

    if not audio_path or not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not metadata_json_path or not Path(metadata_json_path).exists():
        raise FileNotFoundError(f"Metadata JSON not found: {metadata_json_path}")

    with open(metadata_json_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)

    # Get total audio duration
    audio_info = sf.info(audio_path)
    total_audio_duration = audio_info.duration

    script_meta = meta.get("script_metadata", [])

    slides_dir = OUTPUT_DIR / "temp_slides"
    slides_dir.mkdir(parents=True, exist_ok=True)

    images_dir = OUTPUT_DIR / "topic_images"

    total_segs = max(len(script_meta), 1)
    duration_per_seg = total_audio_duration / total_segs

    # Pre-calculate cumulative start times for segments and target section start times
    seg_start_times = []
    curr_t = 0.0
    for seg in script_meta:
        seg_dur = seg.get("duration", duration_per_seg)
        seg_start_times.append(curr_t)
        curr_t += seg_dur

    release_start_time = None
    ott_start_time = None
    c_idx = 0
    topic_items = meta.get("topic_items", [])

    for i, seg in enumerate(script_meta):
        seg_type = seg.get("type", "headline")
        seg_text = seg.get("text", "").lower()
        if seg_type == "headline":
            c_idx += 1
            t_idx = c_idx
        else:
            t_idx = max(c_idx, 1)

        item_data = topic_items[t_idx - 1] if t_idx <= len(topic_items) else {}
        sec_slug = str(item_data.get("section_slug", "")).lower()

        if release_start_time is None:
            if seg_type == "section_intro" and any(k in seg_text for k in ["റിലീ", "തിയേ", "release", "theater"]):
                release_start_time = seg_start_times[i]
            elif sec_slug == "release_updates":
                release_start_time = seg_start_times[i]

        if ott_start_time is None:
            if seg_type == "section_intro" and any(k in seg_text for k in ["ഒടിടി", "സ്ട്രീമിംഗ്", "ott"]):
                ott_start_time = seg_start_times[i]
            elif sec_slug == "ott_updates":
                ott_start_time = seg_start_times[i]

    rel_str = f"{release_start_time:.1f}s" if release_start_time is not None else "N/A"
    ott_str = f"{ott_start_time:.1f}s" if ott_start_time is not None else "N/A"
    print(f"[*] Section Timing Targets -> Theater Updates: {rel_str} | OTT Updates: {ott_str}")

    # 1. Build visual entries for each segment (video or slide image)
    visual_entries = []
    current_topic_index = 0

    for i, seg in enumerate(script_meta):
        seg_type = seg.get("type", "headline")
        seg_duration = seg.get("duration", duration_per_seg)
        seg_t = seg_start_times[i]

        if seg_type == "headline":
            current_topic_index += 1
            topic_idx = current_topic_index
        else:
            topic_idx = max(current_topic_index, 1)

        item_data = topic_items[topic_idx - 1] if topic_idx <= len(topic_items) else {}
        next_item_data = topic_items[topic_idx] if topic_idx < len(topic_items) else item_data

        vpath = resolve_video_for_segment(seg, item_data, next_item_data)

        if vpath and vpath.exists():
            visual_entries.append({
                "kind": "video",
                "vpath": vpath,
                "duration": seg_duration,
                "segment_index": i
            })
        else:
            slide_img_path = str(slides_dir / f"slide_{i+1}.jpg")
            if seg_type == "intro":
                create_fitted_banner_slide(INTRO_BANNER_PATH, slide_img_path)
            elif seg_type == "outro":
                create_outro_banner_slide(topic_items, OUTRO_BANNER_PATH, slide_img_path)
            elif seg_type in ["transition", "section_intro"]:
                create_fitted_banner_slide(TRANSITION_BANNER_PATH, slide_img_path)
            banner_overlay_path = None
            if seg_type not in ["intro", "outro", "transition", "section_intro"]:
                all_imgs = item_data.get("image_paths", [])
                if not all_imgs:
                    p_path = item_data.get("movie_poster_path")
                    a_paths = item_data.get("actor_photo_paths", [])
                    all_imgs = ([p_path] if p_path else []) + (a_paths if a_paths else [])
                valid_imgs = [p for p in all_imgs if p and Path(p).exists()]

            banner_overlay_path = None
            banner_width = 750
            if item_data:
                sec_slug = str(item_data.get("section_slug", "")).lower()
                topic_text = item_data.get("topic_text", "")
                topic_headline = item_data.get("topic_headline", "").strip()

                if sec_slug in ["release_updates", "ott_updates"]:
                    rel_date = str(item_data.get("release_date", "")).strip()
                    ott_plat = str(item_data.get("ott_platform", "")).strip()
                    create_table_slide(topic_text, valid_imgs, slide_img_path, sec_slug, topic_headline=topic_headline, release_date=rel_date, ott_platform=ott_plat)
                else:
                    create_actor_collage_slide(valid_imgs, slide_img_path)
                    if topic_headline:
                        overlay_png = str(slides_dir / f"headline_banner_{i+1}.png")
                        _, banner_w = create_headline_banner_overlay(topic_headline, overlay_png)
                        banner_overlay_path = overlay_png
                        banner_width = banner_w

                timer_info = None
                # Section Countdown Timer Overlay Badge (Position top_y = 40 for BOTH!)
                if sec_slug == "movie_updates" and release_start_time is not None and seg_t < release_start_time:
                    timer_info = {
                        "label_text": "THEATER UPDATES IN",
                        "target_time": release_start_time,
                        "color": (255, 215, 0),
                        "top_y": 40
                    }
                elif sec_slug == "release_updates" and ott_start_time is not None and seg_t < ott_start_time:
                    timer_info = {
                        "label_text": "OTT UPDATES IN",
                        "target_time": ott_start_time,
                        "color": (0, 229, 255),
                        "top_y": 40
                    }

                # Pre-render 1-second sub-slide images in PIL for dynamic per-second countdown
                sec_slides = []
                if timer_info:
                    n_secs = max(1, int(round(seg_duration)))
                    for s in range(n_secs):
                        frame_img_path = str(slides_dir / f"slide_{i+1}_sec_{s:02d}.jpg")
                        import shutil
                        shutil.copy(slide_img_path, frame_img_path)
                        rem_s = timer_info["target_time"] - (seg_t + s)
                        draw_section_countdown_badge(
                            frame_img_path,
                            timer_info["label_text"],
                            rem_s,
                            border_color=timer_info["color"],
                            accent_color=timer_info["color"],
                            top_y=timer_info["top_y"]
                        )
                        sec_slides.append(frame_img_path)
                else:
                    sec_slides = [slide_img_path]

            visual_entries.append({
                "kind": "slide",
                "image": slide_img_path,
                "sec_slides": sec_slides,
                "duration": seg_duration,
                "segment_index": i,
                "banner_overlay": banner_overlay_path,
                "banner_width": banner_width,
                "timer_info": timer_info
            })

    # 2. Group visual entries into consecutive chunks
    chunks = []
    for entry in visual_entries:
        if entry["kind"] == "video":
            chunks.append({
                "kind": "video",
                "vpath": entry["vpath"],
                "duration": entry["duration"]
            })
        elif entry.get("banner_overlay"):
            chunks.append({
                "kind": "animated_slide",
                "slides": [entry],
                "duration": entry["duration"],
                "banner_width": entry.get("banner_width", 750)
            })
        else:
            if chunks and chunks[-1]["kind"] == "slides":
                chunks[-1]["slides"].append(entry)
                chunks[-1]["duration"] += entry["duration"]
            else:
                chunks.append({
                    "kind": "slides",
                    "slides": [entry],
                    "duration": entry["duration"]
                })

    # 3. Render each chunk to chunk_{k:02d}.mp4 with exact frame-accurate duration
    rendered_chunk_paths = []
    print(f"[*] Rendering {len(chunks)} Visual Chunks with Exact Audio-Sync Durations...")
    sys.stdout.flush()

    for k, chunk in enumerate(chunks):
        chunk_mp4 = str(slides_dir / f"chunk_{k:02d}.mp4")
        chunk_dur = chunk["duration"]

        if chunk["kind"] == "video":
            vpath = chunk["vpath"]
            native_dur = get_intro_video_duration(vpath)
            pts_scale = chunk_dur / max(native_dur, 0.1)
            print(f"    - Chunk {k:02d} [VIDEO] : {vpath.name} ({chunk_dur:.2f}s, Retimed)")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(vpath),
                "-an",
                "-vf", f"scale=1920:1080,fps=30,setsar=1,setpts={pts_scale:.6f}*PTS,tpad=stop_mode=clone:stop_duration={chunk_dur:.3f}",
                "-t", f"{chunk_dur:.4f}",
                "-c:v", "libx264",
                "-crf", "17",
                "-preset", "medium",
                "-b:v", "12M",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                chunk_mp4
            ]
            subprocess.run(cmd, check=True)

        elif chunk["kind"] == "animated_slide":
            slide_entry = chunk["slides"][0]
            dur = chunk_dur
            banner_img = slide_entry["banner_overlay"].replace("\\", "/")
            banner_w = chunk.get("banner_width", 750)
            sec_slides = slide_entry.get("sec_slides", [slide_entry["image"]])

            concat_txt = str(slides_dir / f"concat_slide_{k:02d}.txt")
            with open(concat_txt, "w", encoding="utf-8") as f:
                for s_img in sec_slides:
                    esp = s_img.replace("\\", "/")
                    f.write(f"file '{esp}'\n")
                    f.write("duration 1.0\n")
                if sec_slides:
                    esp_last = sec_slides[-1].replace("\\", "/")
                    f.write(f"file '{esp_last}'\n")

            t_out = max(1.5, dur - 1.0)
            t_out_end = t_out + 0.4
            
            offscreen_x = -(banner_w + 50)
            slide_speed = (banner_w + 90) / 0.4

            filter_str = (
                f"[0:v]scale=1920:1080,fps=30,setsar=1[bg];"
                f"[1:v]scale={banner_w}:125[banner];"
                f"[bg][banner]overlay=x='if(lt(t,1.0),{offscreen_x},if(lt(t,1.4),{offscreen_x}+(t-1.0)*{slide_speed:.2f},if(lt(t,{t_out:.2f}),40,if(lt(t,{t_out_end:.2f}),40-(t-{t_out:.2f})*{slide_speed:.2f},{offscreen_x}))))':y=905[v]"
            )

            print(f"    - Chunk {k:02d} [ANIMATED HEADLINE SLIDE]: ({dur:.2f}s, Left Slide Banner width={banner_w}px + PIL Per-Sec Timer)")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_txt,
                "-loop", "1", "-t", f"{dur:.4f}", "-i", banner_img,
                "-filter_complex", filter_str,
                "-map", "[v]",
                "-t", f"{dur:.4f}",
                "-c:v", "libx264",
                "-crf", "17",
                "-preset", "medium",
                "-b:v", "12M",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                chunk_mp4
            ]
            subprocess.run(cmd, check=True)

        else:
            concat_txt = str(slides_dir / f"concat_chunk_{k:02d}.txt")
            with open(concat_txt, "w", encoding="utf-8") as f:
                for s in chunk["slides"]:
                    sec_slides = s.get("sec_slides", [s["image"]])
                    per_sec_dur = s["duration"] / max(len(sec_slides), 1)
                    for s_img in sec_slides:
                        esp = s_img.replace("\\", "/")
                        f.write(f"file '{esp}'\n")
                        f.write(f"duration {per_sec_dur:.3f}\n")
                if chunk["slides"]:
                    last_sec_slides = chunk["slides"][-1].get("sec_slides", [chunk["slides"][-1]["image"]])
                    esp = last_sec_slides[-1].replace("\\", "/")
                    f.write(f"file '{esp}'\n")

            has_timer = any(s.get("timer_info") for s in chunk["slides"])
            print(f"    - Chunk {k:02d} [SLIDES]: {len(chunk['slides'])} slide(s) ({chunk_dur:.2f}s{' + PIL Per-Sec Timer' if has_timer else ''})")
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_txt,
                "-t", f"{chunk_dur:.4f}",
                "-vf", "scale=1920:1080,fps=30,setsar=1",
                "-c:v", "libx264",
                "-crf", "17",
                "-preset", "medium",
                "-b:v", "12M",
                "-pix_fmt", "yuv420p",
                "-r", "30",
                chunk_mp4
            ]
            subprocess.run(cmd, check=True)

        rendered_chunk_paths.append(chunk_mp4)

    # 4. Master Concatenation of all visual chunks into combined_visuals.mp4
    master_txt = str(slides_dir / "master_chunks.txt")
    with open(master_txt, "w", encoding="utf-8") as f:
        for cp in rendered_chunk_paths:
            escaped_path = cp.replace("\\", "/")
            f.write(f"file '{escaped_path}'\n")

    combined_visuals = str(slides_dir / "combined_visuals.mp4")
    print(f"[*] Concatenating {len(rendered_chunk_paths)} Visual Chunks into Master Visual Track...")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", master_txt,
        "-c", "copy",
        combined_visuals
    ]
    subprocess.run(cmd_concat, check=True)

    # 5. Final Audio Overlay & BGM Ducking Pass
    if not output_video_path:
        output_video_path = str(OUTPUT_DIR / "Malayalam_Movie_News_Presenter_1080p.mp4")

    BGM_PATH = ASSETS_DIR / "bgm_track.mp3"
    print(f"[*] Finalizing Presentation Video: {output_video_path}...")

    if BGM_PATH.exists():
        print(f"[*] Mixing Background Music Track: {BGM_PATH.name}")
        try:
            bgm_info = sf.info(str(BGM_PATH))
            full_bgm_dur = bgm_info.duration
            trimmed_bgm_dur = max(5.0, full_bgm_dur - 5.0)
            fade_start = max(0.0, total_audio_duration - 5.0)

            filter_complex = (
                f"[2:a]atrim=0:{trimmed_bgm_dur:.2f},aloop=loop=-1:size={int(trimmed_bgm_dur * 44100)}[bgm_loop];"
                f"[bgm_loop]volume={BGM_VOLUME},afade=t=out:st={fade_start:.2f}:d=5[bgm_ducked];"
                f"[1:a]volume=4.0[voice];"
                f"[voice][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=3[aout]"
            )

            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", combined_visuals,
                "-i", audio_path,
                "-i", str(BGM_PATH),
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_video_path
            ]
        except Exception as e:
            print(f"[!] BGM processing warning: {e}")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", combined_visuals,
                "-i", audio_path,
                "-filter_complex", "[1:a]volume=4.0[aout]",
                "-map", "0:v",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_video_path
            ]
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-i", combined_visuals,
            "-i", audio_path,
            "-filter_complex", "[1:a]volume=4.0[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video_path
        ]

    subprocess.run(ffmpeg_cmd, check=True)

    # Clean up temporary slides cache after video generation
    import shutil
    try:
        if slides_dir.exists():
            shutil.rmtree(slides_dir)
        print("[+] Cleaned up temporary slide cache files.")
    except Exception as e:
        print(f"[!] Cleanup warning: {e}")

    # Automatically generate 1280x720 YouTube Thumbnail Collage
    thumb_path = None
    try:
        from metadata_generator import download_thumbnail_from_drive
        thumb_path = download_thumbnail_from_drive()
        if thumb_path:
            print(f"    🖼️ Thumbnail Path : {thumb_path}")
    except Exception as e:
        print(f"[!] Warning generating thumbnail after video render: {e}")

    print("\n" + "=" * 70)
    print(f"[SUCCESS] Presentation Video Rendered Successfully!")
    print(f"    📁 MP4 Video Path : {output_video_path}")
    if thumb_path:
        print(f"    🖼️ Thumbnail Path : {thumb_path}")
    print(f"    ⏱️ Video Duration : {round(total_audio_duration, 2)} seconds")
    print(f"    📺 Resolution     : 1920x1080 Full HD (30 FPS)")
    print("=" * 70)

    return output_video_path


if __name__ == "__main__":
    audio = None
    meta = None
    if len(sys.argv) > 1:
        audio = sys.argv[1]
    if len(sys.argv) > 2:
        meta = sys.argv[2]

    generate_video(audio_path=audio, metadata_json_path=meta)
