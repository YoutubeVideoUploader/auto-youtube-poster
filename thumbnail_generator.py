"""
Automated YouTube Thumbnail Collage Generator Module
Creates broadcast-quality 1280x720 YouTube thumbnail collages from movie poster image URLs,
complete with dark gradient overlays, gold/red badges, and high-contrast title typography.
"""

import os
import io
import requests
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
THUMBNAIL_DIR = OUTPUT_DIR / "youtube_thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


def get_font(size: int) -> ImageFont.ImageFont:
    """Tries loading DejaVuSans-Bold or FreeSansBold or fallback default font."""
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


def upgrade_image_url_quality(url: str) -> str:
    """Upgrades web image URLs (e.g. CinemaExpress/Assettype CDN parameters) from low-res (w=480/300) to Full HD 1280p/1920p resolution."""
    import re
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
            import re
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
            except Exception as e:
                pass
        print(f"[!] Warning: Could not download image {url[:50]}...")
    return None


def crop_center(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Crops and resizes an image to fit target width and height maintaining aspect ratio with sharpness enhancement."""
    img_aspect = img.width / img.height
    target_aspect = target_width / target_height

    if img_aspect > target_aspect:
        # Image is wider: fit height first
        new_height = target_height
        new_width = int(new_height * img_aspect)
    else:
        # Image is taller: fit width first
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


def create_collage_thumbnail(
    image_urls: List[str],
    title_text: str = "LATEST MALAYALAM MOVIE UPDATES",
    output_filename: str = "generated_thumbnail.jpg",
    badge_text: str = "MOVIE NEWS • EXCLUSIVE UPDATE"
) -> Optional[str]:
    """
    Downloads images from image_urls and creates a professional 1280x720 collage thumbnail.
    Returns absolute path to the generated thumbnail image file.
    """
    canvas_w, canvas_h = 1280, 720
    canvas = Image.new("RGB", (canvas_w, canvas_h), (18, 18, 28))

    # Download all valid images
    images = []
    for u in image_urls:
        img = download_image(u)
        if img:
            images.append(img)
        if len(images) >= 6:
            break

    # Fallback placeholder if no images downloaded successfully
    if not images:
        placeholder = Image.new("RGB", (canvas_w, canvas_h), (25, 25, 45))
        draw_p = ImageDraw.Draw(placeholder)
        draw_p.rectangle([40, 40, canvas_w-40, canvas_h-40], outline=(255, 42, 75), width=4)
        images = [placeholder]

    num_imgs = len(images)

    # 1. Composite Grid/Split Layout based on image count
    if num_imgs == 1:
        # 1 Full-screen hero image
        cropped = crop_center(images[0], canvas_w, canvas_h)
        canvas.paste(cropped, (0, 0))

    elif num_imgs == 2:
        # 50-50 Vertical Split
        w_half = canvas_w // 2
        img1 = crop_center(images[0], w_half, canvas_h)
        img2 = crop_center(images[1], canvas_w - w_half, canvas_h)
        canvas.paste(img1, (0, 0))
        canvas.paste(img2, (w_half, 0))

        # Vertical Divider Line with Glow
        draw_line = ImageDraw.Draw(canvas)
        draw_line.line([(w_half, 0), (w_half, canvas_h)], fill=(255, 42, 75), width=6)

    elif num_imgs == 3:
        # 1 Featured Hero Left (50%), 2 Stacked Right (50%)
        w_hero = canvas_w // 2
        w_right = canvas_w - w_hero
        h_right = canvas_h // 2

        img_hero = crop_center(images[0], w_hero, canvas_h)
        img_r1 = crop_center(images[1], w_right, h_right)
        img_r2 = crop_center(images[2], w_right, canvas_h - h_right)

        canvas.paste(img_hero, (0, 0))
        canvas.paste(img_r1, (w_hero, 0))
        canvas.paste(img_r2, (w_hero, h_right))

        # Dividers
        draw_line = ImageDraw.Draw(canvas)
        draw_line.line([(w_hero, 0), (w_hero, canvas_h)], fill=(255, 42, 75), width=5)
        draw_line.line([(w_hero, h_right), (canvas_w, h_right)], fill=(255, 42, 75), width=4)

    elif num_imgs == 4:
        # 2x2 Grid
        w_half = canvas_w // 2
        h_half = canvas_h // 2

        img1 = crop_center(images[0], w_half, h_half)
        img2 = crop_center(images[1], canvas_w - w_half, h_half)
        img3 = crop_center(images[2], w_half, h_half)
        img4 = crop_center(images[3], canvas_w - w_half, canvas_h - h_half)

        canvas.paste(img1, (0, 0))
        canvas.paste(img2, (w_half, 0))
        canvas.paste(img3, (0, h_half))
        canvas.paste(img4, (w_half, h_half))

        # Dividers
        draw_line = ImageDraw.Draw(canvas)
        draw_line.line([(w_half, 0), (w_half, canvas_h)], fill=(255, 42, 75), width=5)
        draw_line.line([(0, h_half), (canvas_w, h_half)], fill=(255, 42, 75), width=5)

    else:
        # 5 or 6 Images: 3x2 Grid
        col_w = canvas_w // 3
        row_h = canvas_h // 2

        for idx in range(min(num_imgs, 6)):
            r = idx // 3
            c = idx % 3
            cw = col_w if c < 2 else canvas_w - (col_w * 2)
            ch = row_h if r == 0 else canvas_h - row_h
            cropped = crop_center(images[idx], cw, ch)
            canvas.paste(cropped, (c * col_w, r * row_h))

        draw_line = ImageDraw.Draw(canvas)
        draw_line.line([(col_w, 0), (col_w, canvas_h)], fill=(255, 42, 75), width=4)
        draw_line.line([(col_w * 2, 0), (col_w * 2, canvas_h)], fill=(255, 42, 75), width=4)
        draw_line.line([(0, row_h), (canvas_w, row_h)], fill=(255, 42, 75), width=4)

    # 2. Add Dark Gradient Vignette Overlay at bottom & top for typography contrast
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Bottom Gradient (height 300px)
    gradient_h = 300
    start_y = canvas_h - gradient_h
    for y in range(gradient_h):
        alpha = int(245 * (y / gradient_h) ** 1.3)
        draw_ov.line([(0, start_y + y), (canvas_w, start_y + y)], fill=(10, 10, 18, alpha))

    # Top Banner Gradient (height 100px)
    for y in range(100):
        alpha = int(180 * (1.0 - (y / 100)))
        draw_ov.line([(0, y), (canvas_w, y)], fill=(10, 10, 18, alpha))

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    # 3. Top Broadcast Badge
    badge_font = get_font(26)
    badge_text = (badge_text or "MOVIE NEWS • EXCLUSIVE UPDATE").strip()
    badge_bbox = badge_font.getbbox(badge_text)
    badge_w = badge_bbox[2] - badge_bbox[0]
    badge_h = badge_bbox[3] - badge_bbox[1]

    badge_pad_x, badge_pad_y = 16, 8
    badge_rect = [30, 25, 30 + badge_w + (badge_pad_x * 2), 25 + badge_h + (badge_pad_y * 2)]
    draw.rounded_rectangle(badge_rect, radius=6, fill=(255, 42, 75))
    draw.text((30 + badge_pad_x, 25 + badge_pad_y - 2), badge_text, font=badge_font, fill=(255, 255, 255))

    # 4. Main Bottom Title Text Card: "LATEST MALAYALAM MOVIE UPDATES"
    title_font = get_font(48)
    display_title = (title_text or "LATEST MALAYALAM MOVIE UPDATES").upper()

    tb_margin_x = 30
    tb_bottom_y = canvas_h - 35
    tb_top_y = canvas_h - 130

    draw.rounded_rectangle([tb_margin_x, tb_top_y, canvas_w - tb_margin_x, tb_bottom_y], radius=10, fill=(26, 26, 46), outline=(255, 42, 75), width=3)

    # Drop shadow & Text
    tx_x = tb_margin_x + 25
    tx_y = tb_top_y + 20

    for offset_x, offset_y in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3), (3, 0)]:
        draw.text((tx_x + offset_x, tx_y + offset_y), display_title, font=title_font, fill=(0, 0, 0))

    draw.text((tx_x, tx_y), display_title, font=title_font, fill=(255, 220, 0))

    # Save final high-res 1280x720 thumbnail JPEG
    save_path = THUMBNAIL_DIR / output_filename
    canvas.save(save_path, "JPEG", quality=95)
    print(f"[OK] Automated YouTube Thumbnail Collage generated: {save_path}")

    return str(save_path)


if __name__ == "__main__":
    sample_urls = [
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-07%2Fqoyeyn8q%2FMammoottyMelafirstlook.jpg?auto=format%2Ccompress&fit=max&w=480",
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-12%2Fe40s25kb%2FVinayan.jpg?auto=format%2Ccompress&fit=max&w=480",
        "https://cf-images.assettype.com/cinemaexpress%2F2026-09-11%2Fv8gzh8n0%2FAmala-Paul.jpg?auto=format%2Ccompress&fit=max&w=480"
    ]
    res_path = create_collage_thumbnail(sample_urls, "LATEST MALAYALAM MOVIE UPDATES")
    print("Test result path:", res_path)
