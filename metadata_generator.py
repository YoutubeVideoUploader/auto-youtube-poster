"""
YouTube Video Metadata & Chapter Generator Module
Generates English SEO Titles, Timestamped Video Chapters, Topic Headline Lists,
Hashtags, SEO Tags, and Google Drive Thumbnail Downloader.
"""

import os
import re
import io
import requests
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
THUMBNAIL_DIR = OUTPUT_DIR / "youtube_thumbnails"
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)


def convert_drive_link_to_direct_download(drive_url: str) -> str:
    """Converts a standard Google Drive shareable link into a direct download URL."""
    drive_url = drive_url.strip()
    if not drive_url:
        return ""

    # Match File ID from various Drive URL formats
    file_id = ""
    match1 = re.search(r'/file/d/([a-zA-Z0-9_-]+)', drive_url)
    match2 = re.search(r'id=([a-zA-Z0-9_-]+)', drive_url)

    if match1:
        file_id = match1.group(1)
    elif match2:
        file_id = match2.group(1)

    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    return drive_url


def download_thumbnail_from_drive(drive_url: str, save_filename: str = "custom_thumbnail.jpg") -> Optional[str]:
    """Downloads thumbnail image from Google Drive link into outputs/youtube_thumbnails."""
    if not drive_url or not drive_url.strip():
        return None

    direct_url = convert_drive_link_to_direct_download(drive_url)
    save_path = THUMBNAIL_DIR / save_filename

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        r = requests.get(direct_url, headers=headers, verify=False, timeout=25)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(save_path, 'wb') as f:
                f.write(r.content)
            print(f"[✓] Thumbnail downloaded from Google Drive: {save_path}")
            return str(save_path)
    except Exception as e:
        print(f"[!] Error downloading thumbnail from Drive: {e}")

    return None


def generate_english_title(month_year: Optional[str] = None) -> str:
    """Generates clean, professional English SEO YouTube video title."""
    if not month_year:
        now = datetime.datetime.now()
        month_year = now.strftime("%B %Y")  # e.g. September 2026

    return f"Malayalam Movie News & OTT Release Updates | {month_year}"


def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats float seconds into M:SS or H:MM:SS YouTube chapter format."""
    secs = int(seconds)
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins}:{rem_secs:02d}"


def generate_youtube_description(
    sheet_data: Dict[str, List[Dict[str, Any]]],
    chunk_timestamps: Optional[List[Tuple[str, float]]] = None
) -> str:
    """
    Generates YouTube video description complete with:
    - Timestamped Video Chapters
    - Topic Headline Bullet Points
    - Channel Disclaimer & Hashtags
    """
    desc_lines = []
    
    desc_lines.append("Latest Malayalam Movie News, Upcoming Theater Release Dates, and OTT Streaming Updates!")
    desc_lines.append("")

    # 1. Video Chapters
    desc_lines.append("⏱️ VIDEO CHAPTERS:")
    desc_lines.append("0:00 🎬 Introduction")

    # Default chapter estimates if exact timestamps aren't passed
    if not chunk_timestamps:
        desc_lines.append("0:04 🎭 Movie Updates")
        desc_lines.append("1:43 📅 Theater Release Updates")
        desc_lines.append("3:28 🍿 OTT Streaming Updates")
        desc_lines.append("4:50 🎬 Conclusion & Outro")
    else:
        current_time = 0.0
        for name, dur in chunk_timestamps:
            ts_str = format_seconds_to_timestamp(current_time)
            desc_lines.append(f"{ts_str} {name}")
            current_time += dur

    desc_lines.append("")
    desc_lines.append("=" * 50)
    desc_lines.append("📌 TODAY'S MAIN MOVIE HEADLINES:")
    desc_lines.append("=" * 50)

    # 2. Topic Headlines List
    for section_name, topics in sheet_data.items():
        if topics is None or len(topics) == 0:
            continue
        desc_lines.append(f"\n🔹 {section_name.upper()}:")
        
        # Handle both DataFrame and list of dicts
        rows_iter = topics.iterrows() if hasattr(topics, 'iterrows') else enumerate(topics, start=1)
        for idx, item in enumerate(topics if not hasattr(topics, 'iterrows') else topics.to_dict(orient="records"), start=1):
            text = str(item.get("Malayalam News Text", item.get("text", ""))).strip()
            if not text or text.lower() == "nan":
                continue
            short_text = text[:120] + "..." if len(text) > 120 else text
            desc_lines.append(f"  {idx}. {short_text}")

    desc_lines.append("")
    desc_lines.append("=" * 50)
    desc_lines.append("🔔 Subscribe for daily Malayalam Movie News, Reviews & OTT Updates!")
    desc_lines.append("")
    desc_lines.append("#MalayalamMovieNews #Mollywood #OTTRelease #MalayalamCinema #MovieUpdates #KeralaBoxOffice")

    return "\n".join(desc_lines)


def generate_youtube_tags() -> List[str]:
    """Returns optimized SEO keywords list for YouTube Video upload."""
    return [
        "Malayalam Movie News",
        "Mollywood Updates",
        "Malayalam Movie Release Dates",
        "OTT Release Malayalam",
        "Malayalam Cinema News",
        "Kerala Box Office",
        "Netflix Malayalam",
        "Prime Video Malayalam",
        "Hotstar Malayalam",
        "Malayalam Movie Trailers",
        "Mammootty New Movie",
        "Mohanlal New Movie",
        "Malayalam Movie Updates 2026"
    ]
