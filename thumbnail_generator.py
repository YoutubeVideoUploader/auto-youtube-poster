"""
Automated YouTube Thumbnail Generator Module
Creates broadcast-quality 1280x720 YouTube thumbnail with:
- Gemini AI Creative Director: AI-generated main_hook, sub_text, badge, color_theme, layout_style
- Next-Gen Broadcast Engine: 3D Impact typography, glowing neon diagonal separators, cinematic vignette
- Backward-compatible create_collage_thumbnail() for legacy callers
"""

import os
import io
import re
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
THUMBNAIL_DIR = OUTPUT_DIR / "youtube_thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# FONT UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def get_font(size: int) -> ImageFont.ImageFont:
    """Tries loading DejaVuSans-Bold or FreeSansBold or fallback default font (legacy helper)."""
    font_candidates = [
        "DejaVuSans-Bold.ttf",
        "FreeSansBold.ttf",
        "arialbd.ttf",
        "arial.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def get_best_font(size: int, font_type: str = "impact") -> ImageFont.ImageFont:
    """Returns Impact for main hook or Arial Bold for sub-text/badge. Fallback chain for Linux/Windows."""
    impact_candidates = [
        "C:\\Windows\\Fonts\\impact.ttf",
        "impact.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    sans_candidates = [
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\trebucbd.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    cands = impact_candidates if font_type == "impact" else sans_candidates
    for c in cands:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def clean_text_no_emoji(text: str) -> str:
    """Removes emoji characters and stray unicode glyphs to prevent hollow boxes in text rendering."""
    if not text:
        return ""
    text = re.sub(r'[\U00010000-\U0010ffff]', '', str(text))
    text = re.sub(r'[\u2600-\u27bf]', '', text)
    text = text.replace('"', '').replace("'", '').replace("`", "")
    return re.sub(r'\s+', ' ', text).strip()


def upgrade_image_url_quality(url: str) -> str:
    """Upgrades web image URLs from low-res (w=480/300) to Full HD 1280p resolution."""
    if not url or not isinstance(url, str):
        return url
    if "w=480" in url or "w=300" in url or "w=600" in url or "w=350" in url:
        return re.sub(r'w=\d+', 'w=1280', url)
    return url


def download_image(url_or_path: str, timeout: int = 15) -> Optional[Image.Image]:
    """Loads an image from a local file path OR downloads from HTTP URL."""
    if not url_or_path or not str(url_or_path).strip():
        return None
    url_or_path = str(url_or_path).strip()

    # 1. Local file path support
    p = Path(url_or_path)
    if p.exists() and p.is_file():
        try:
            return Image.open(p).convert("RGB")
        except Exception as e:
            print(f"[!] Warning: Could not open local image {url_or_path} : {e}")
            return None

    # 2. HTTP URL download support
    if url_or_path.startswith("http"):
        url = upgrade_image_url_quality(url_or_path)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Handle Google Drive shareable links
        urls_to_try = [url]
        if "drive.google.com" in url or "/file/d/" in url:
            match1 = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            match2 = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            file_id = match1.group(1) if match1 else (match2.group(1) if match2 else "")
            if file_id:
                urls_to_try = [
                    f"https://drive.google.com/thumbnail?id={file_id}&sz=w1920",
                    f"https://lh3.googleusercontent.com/d/{file_id}",
                    f"https://drive.google.com/uc?export=download&id={file_id}"
                ]

        for u in urls_to_try:
            try:
                resp = requests.get(u, headers=headers, timeout=timeout, verify=False)
                if resp.status_code == 200 and len(resp.content) > 500 and not resp.content.startswith(b'<!DOCTYPE') and not resp.content.startswith(b'<html'):
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    return img
            except Exception:
                pass
        print(f"[!] Warning: Could not download image {url_or_path[:60]}...")
    return None


def enhance_poster(img: Image.Image) -> Image.Image:
    """Enhances contrast, saturation, and sharpness for cinematic punch."""
    try:
        c = ImageEnhance.Contrast(img).enhance(1.22)
        s = ImageEnhance.Color(c).enhance(1.25)
        sh = ImageEnhance.Sharpness(s).enhance(1.35)
        return sh
    except Exception:
        return img


def crop_center(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Legacy center crop – maintained for backward compatibility."""
    img_aspect = img.width / img.height
    target_aspect = target_width / target_height

    if img_aspect > target_aspect:
        new_height = target_height
        new_width = int(new_height * img_aspect)
    else:
        new_width = target_width
        new_height = int(new_width / img_aspect)

    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    try:
        sharpener = ImageEnhance.Sharpness(resized)
        resized = sharpener.enhance(1.25)
    except Exception:
        pass

    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height
    return resized.crop((left, top, right, bottom))


def crop_smart(img: Image.Image, tw: int, th: int, focus_top: bool = True) -> Image.Image:
    """
    Crops and resizes image to target dimensions.
    If focus_top=True (movie posters), crops towards the upper-center to preserve faces.
    """
    aspect = img.width / img.height
    target_aspect = tw / th
    if aspect > target_aspect:
        nh = th
        nw = int(nh * aspect)
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - tw) // 2
        top = 0
    else:
        nw = tw
        nh = int(nw / aspect)
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = 0
        if focus_top and nh > th:
            top = int((nh - th) * 0.15)  # 15% from top keeps faces in frame
        else:
            top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


# ─────────────────────────────────────────────────────────────────────────────
# 3D IMPACT TEXT RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def draw_3d_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple,
    text: str,
    font,
    fill_color,
    stroke_color=(0, 0, 0),
    stroke_width: int = 7,
    shadow_offset: tuple = (5, 6)
):
    """Renders text with a deep 3D drop shadow + multi-angle thick black outline + vivid fill."""
    x, y = pos
    sx, sy = shadow_offset

    # 1. Deep 3D Drop Shadow
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + sx + dx, y + sy + dy), text, font=font, fill=(5, 5, 10, 240))

    # 2. Multi-angle black outline stroke
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)

    # 3. Main vivid text fill
    draw.text((x, y), text, font=font, fill=fill_color)


# ─────────────────────────────────────────────────────────────────────────────
# NEXT-GEN BROADCAST THUMBNAIL ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def create_nextgen_thumbnail(
    image_urls: List[str],
    brief: Dict[str, Any],
    output_filename: str = "custom_thumbnail.jpg"
) -> Optional[str]:
    """
    Creates a broadcast-quality 1280x720 YouTube thumbnail using:
    - Gemini AI brief (main_hook, sub_text, badge, color_theme, layout_style)
    - 3D Impact typography with neon glow diagonal dividers and cinematic vignette
    Returns absolute path to the generated JPEG thumbnail.
    """
    W, H = 1280, 720
    canvas = Image.new("RGBA", (W, H), (8, 10, 18, 255))

    # ── Resolve theme colors from Gemini brief ──────────────────────────────
    theme_name = str(brief.get("color_theme", "crimson")).lower()
    if "gold" in theme_name:
        accent_color = (255, 215, 0)
        accent_glow = (255, 235, 100)
        badge_bg = (217, 119, 6)
        text_accent = (255, 230, 0)
    elif "cyan" in theme_name:
        accent_color = (0, 242, 254)
        accent_glow = (79, 172, 254)
        badge_bg = (2, 132, 199)
        text_accent = (0, 242, 254)
    else:  # crimson (default)
        accent_color = (255, 42, 75)
        accent_glow = (255, 90, 120)
        badge_bg = (225, 29, 72)
        text_accent = (255, 225, 0)  # High-contrast yellow on crimson

    # ── Download & enhance poster images ───────────────────────────────────
    loaded = []
    for url_or_path in image_urls:
        img = download_image(url_or_path)
        if img:
            loaded.append(enhance_poster(img))
        if len(loaded) >= 4:
            break

    if not loaded:
        loaded = [Image.new("RGB", (W, H), (20, 24, 38))]

    layout = str(brief.get("layout_style", "diagonal_clash")).lower()
    num = len(loaded)

    # ── LAYOUT 1: Diagonal Clash (default for 2 images) ────────────────────
    if (layout == "diagonal_clash" or num == 2) and num >= 2:
        img_left = crop_smart(loaded[0], W, H, focus_top=True)
        img_right = crop_smart(loaded[1], W, H, focus_top=True)

        canvas.paste(img_left, (0, 0))

        split_top = W // 2 + 65
        split_bottom = W // 2 - 65

        mask = Image.new("L", (W, H), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.polygon([(split_top, 0), (W, 0), (W, H), (split_bottom, H)], fill=255)
        canvas.paste(img_right, (0, 0), mask)

        # Glowing neon diagonal divider (3 layers: outer glow, core, white center line)
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(glow_layer)
        draw_g.line([(split_top, 0), (split_bottom, H)], fill=(*accent_glow, 70), width=22)
        draw_g.line([(split_top, 0), (split_bottom, H)], fill=(*accent_color, 160), width=10)
        draw_g.line([(split_top, 0), (split_bottom, H)], fill=(255, 255, 255, 240), width=3)
        canvas = Image.alpha_composite(canvas, glow_layer)

    # ── LAYOUT 2: Hero Focus (1 big left, 2 stacked right) ─────────────────
    elif (layout == "hero_focus" or num == 3) and num >= 3:
        hero_w = int(W * 0.58)
        right_w = W - hero_w
        half_h = H // 2

        img_hero = crop_smart(loaded[0], hero_w, H, focus_top=True)
        img_r1 = crop_smart(loaded[1], right_w, half_h, focus_top=True)
        img_r2 = crop_smart(loaded[2], right_w, H - half_h, focus_top=True)

        canvas.paste(img_hero, (0, 0))
        canvas.paste(img_r1, (hero_w, 0))
        canvas.paste(img_r2, (hero_w, half_h))

        lines_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_l = ImageDraw.Draw(lines_layer)
        draw_l.line([(hero_w, 0), (hero_w, H)], fill=(*accent_color, 220), width=6)
        draw_l.line([(hero_w, half_h), (W, half_h)], fill=(*accent_color, 180), width=5)
        canvas = Image.alpha_composite(canvas, lines_layer)

    # ── LAYOUT 3: Cinematic Duo (side-by-side equal split) ──────────────────
    elif layout == "cinematic_duo" and num >= 2:
        half_w = W // 2
        img_l = crop_smart(loaded[0], half_w, H, focus_top=True)
        img_r = crop_smart(loaded[1], W - half_w, H, focus_top=True)
        canvas.paste(img_l, (0, 0))
        canvas.paste(img_r, (half_w, 0))

        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_g = ImageDraw.Draw(glow_layer)
        draw_g.line([(half_w, 0), (half_w, H)], fill=(*accent_glow, 90), width=18)
        draw_g.line([(half_w, 0), (half_w, H)], fill=(*accent_color, 200), width=8)
        draw_g.line([(half_w, 0), (half_w, H)], fill=(255, 255, 255, 230), width=2)
        canvas = Image.alpha_composite(canvas, glow_layer)

    # ── LAYOUT 4: Single Hero Full Bleed ───────────────────────────────────
    elif num == 1:
        canvas.paste(crop_smart(loaded[0], W, H, focus_top=True), (0, 0))

    # ── LAYOUT 5: 4-image 2×2 Grid ─────────────────────────────────────────
    else:
        half_w = W // 2
        half_h = H // 2
        canvas.paste(crop_smart(loaded[0], half_w, half_h, focus_top=True), (0, 0))
        canvas.paste(crop_smart(loaded[1], half_w, half_h, focus_top=True), (half_w, 0))
        canvas.paste(crop_smart(loaded[2], half_w, half_h, focus_top=True), (0, half_h))
        canvas.paste(crop_smart(loaded[3 if num > 3 else 0], half_w, half_h, focus_top=True), (half_w, half_h))

        lines_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_l = ImageDraw.Draw(lines_layer)
        draw_l.line([(half_w, 0), (half_w, H)], fill=(*accent_color, 200), width=5)
        draw_l.line([(0, half_h), (W, half_h)], fill=(*accent_color, 200), width=5)
        canvas = Image.alpha_composite(canvas, lines_layer)

    # ── CINEMATIC VIGNETTE OVERLAY ──────────────────────────────────────────
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_v = ImageDraw.Draw(vignette)

    # Deep bottom gradient (330px)
    grad_h = 330
    start_y = H - grad_h
    for y in range(grad_h):
        prog = (y / grad_h) ** 1.35
        alpha = int(248 * prog)
        draw_v.line([(0, start_y + y), (W, start_y + y)], fill=(6, 8, 14, alpha))

    # Top banner vignette (120px)
    for y in range(120):
        alpha = int(175 * (1.0 - (y / 120)))
        draw_v.line([(0, y), (W, y)], fill=(6, 8, 14, alpha))

    canvas = Image.alpha_composite(canvas, vignette)
    draw = ImageDraw.Draw(canvas)

    # ── BROADCAST BADGE (Top-Left) ───────────────────────────────────────────
    badge_raw = brief.get("badge", "BREAKING NEWS")
    badge_text = clean_text_no_emoji(badge_raw).upper()
    badge_font = get_best_font(26, font_type="sans")
    bbox = badge_font.getbbox(badge_text)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx, by = 40, 32
    bpad_x, bpad_y = 18, 9

    # Badge shadow
    draw.rounded_rectangle(
        [bx + 4, by + 4, bx + bw + bpad_x * 2 + 14 + 4, by + bh + bpad_y * 2 + 4],
        radius=8, fill=(0, 0, 0, 180)
    )
    # Badge background
    draw.rounded_rectangle(
        [bx, by, bx + bw + bpad_x * 2 + 14, by + bh + bpad_y * 2],
        radius=8, fill=badge_bg, outline=(255, 255, 255, 220), width=2
    )
    # Live indicator dot
    dot_cy = by + (bh + bpad_y * 2) // 2
    draw.ellipse([bx + 12, dot_cy - 5, bx + 22, dot_cy + 5], fill=(255, 255, 255))
    draw.text((bx + bpad_x + 12, by + bpad_y - 2), badge_text, font=badge_font, fill=(255, 255, 255))

    # ── TOP-RIGHT WATERMARK BADGE ────────────────────────────────────────────
    wm_text = "CINEMA DESK • 4K ULTRA HD"
    wm_font = get_best_font(20, font_type="sans")
    w_bbox = wm_font.getbbox(wm_text)
    ww = w_bbox[2] - w_bbox[0]
    wx = W - ww - 45
    draw.rounded_rectangle(
        [wx - 14, by + 2, W - 35, by + bh + bpad_y * 2 - 2],
        radius=6, fill=(10, 14, 24, 210), outline=(*accent_color, 160), width=1
    )
    draw.text((wx, by + bpad_y - 2), wm_text, font=wm_font, fill=(210, 225, 245))

    # ── 3D HIGH-CTR TYPOGRAPHY (Bottom Card) ────────────────────────────────
    main_hook = clean_text_no_emoji(brief.get("main_hook", "BREAKING CINEMA NEWS!")).upper()
    sub_text = clean_text_no_emoji(brief.get("sub_text", "LATEST MALAYALAM MOVIE UPDATES")).upper()

    # Auto-scale font by text length
    hook_size = 76 if len(main_hook) <= 18 else (64 if len(main_hook) <= 24 else 52)
    hook_font = get_best_font(hook_size, font_type="impact")

    sub_size = 34 if len(sub_text) <= 28 else (28 if len(sub_text) <= 38 else 24)
    sub_font = get_best_font(sub_size, font_type="sans")

    text_x = 45
    h_bbox = hook_font.getbbox(main_hook)
    hook_h = h_bbox[3] - h_bbox[1]
    hook_w = min(h_bbox[2] - h_bbox[0], W - 90)

    # Vertical layout: sub_text at bottom, accent bar above it, main_hook above that
    text_y_sub = H - 58
    bar_y = text_y_sub - 26
    text_y_hook = bar_y - hook_h - 18

    # 1. Colored accent underline bar
    draw.rounded_rectangle([text_x, bar_y, text_x + hook_w, bar_y + 7], radius=3, fill=accent_color)

    # 2. Main Hook – Giant Impact 3D text (Electric Yellow)
    draw_3d_text(
        draw, (text_x, text_y_hook), main_hook, hook_font,
        fill_color=text_accent, stroke_color=(0, 0, 0), stroke_width=8, shadow_offset=(5, 6)
    )

    # 3. Sub Text – Clean white with 4px stroke
    draw_3d_text(
        draw, (text_x, text_y_sub), sub_text, sub_font,
        fill_color=(255, 255, 255), stroke_color=(0, 0, 0), stroke_width=5, shadow_offset=(3, 4)
    )

    # ── SAVE FINAL 1280x720 JPEG ─────────────────────────────────────────────
    save_path = THUMBNAIL_DIR / output_filename
    final_img = canvas.convert("RGB")
    final_img.save(save_path, "JPEG", quality=95)
    print(f"[OK] Next-Gen YouTube Thumbnail saved: {save_path}")
    return str(save_path)


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY COLLAGE THUMBNAIL (Backward Compatible)
# ─────────────────────────────────────────────────────────────────────────────

def create_collage_thumbnail(
    image_urls: List[str],
    title_text: str = "LATEST MALAYALAM MOVIE UPDATES",
    output_filename: str = "generated_thumbnail.jpg",
    badge_text: str = "MOVIE NEWS • EXCLUSIVE UPDATE"
) -> Optional[str]:
    """
    Legacy: Downloads images from image_urls and creates a professional 1280x720 collage thumbnail.
    Now delegates to create_nextgen_thumbnail() with a deterministic brief derived from title/badge.
    Returns absolute path to the generated thumbnail image file.
    """
    # Build a simple brief from the legacy title and badge parameters
    title_up = (title_text or "").upper()
    if "OTT" in title_up and "THEATER" in title_up:
        theme = "cyan"
        layout = "hero_focus"
    elif "OTT" in title_up:
        theme = "cyan"
        layout = "diagonal_clash"
    elif "THEATER" in title_up or "RELEASE" in title_up:
        theme = "gold"
        layout = "diagonal_clash"
    else:
        theme = "crimson"
        layout = "diagonal_clash"

    # Truncate title to fit hook
    hook = title_text.upper().replace("LATEST ", "").replace("MALAYALAM ", "")[:28]

    brief = {
        "main_hook": hook,
        "sub_text": badge_text.replace(" • ", " | ")[:40],
        "badge": badge_text.split("•")[0].strip()[:30],
        "color_theme": theme,
        "layout_style": layout
    }
    return create_nextgen_thumbnail(image_urls, brief, output_filename)


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_urls = [
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-07%2Fqoyeyn8q%2FMammoottyMelafirstlook.jpg?auto=format%2Ccompress&fit=max&w=480",
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-12%2Fe40s25kb%2FVinayan.jpg?auto=format%2Ccompress&fit=max&w=480",
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-11%2Fv8gzh8n0%2FAmala-Paul.jpg?auto=format%2Ccompress&fit=max&w=480"
    ]
    brief = {
        "main_hook": "MAMMOOTTY MASS BLAST!",
        "sub_text": "VINAYAN • AMALA PAUL",
        "badge": "OFFICIAL TRAILER",
        "color_theme": "crimson",
        "layout_style": "hero_focus"
    }
    res_path = create_nextgen_thumbnail(sample_urls, brief, "test_nextgen_thumbnail.jpg")
    print("Test result path:", res_path)
