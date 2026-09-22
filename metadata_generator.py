"""
YouTube Video Metadata & Chapter Generator Module
Generates English SEO Titles, Timestamped Video Chapters, Topic Headline Lists,
Hashtags, SEO Tags, and Google Drive Thumbnail Downloader.
"""

import os
import re
import io
import json
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


def download_thumbnail_from_drive(
    drive_url: str = "",
    save_filename: str = "custom_thumbnail.jpg",
    sheet_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    sections: Optional[List[str]] = None
) -> Optional[str]:
    """
    Downloads thumbnail image from Google Drive link, or generates an automated 1280x720 
    collage thumbnail matching active sections (Movie, Theater, OTT, or combinations).
    """
    raw_input = (drive_url or "").strip()

    # Auto-extract embedded sections tag if present in drive_url (e.g. from web dashboard)
    if not sections and "__SECTIONS__:" in raw_input:
        m = re.search(r'__SECTIONS__:([a-zA-Z0-9_,]+)', raw_input)
        if m:
            s_val = m.group(1).strip()
            if s_val and s_val not in ['all', '*', 'all_sections', 'all_3']:
                sections = [s.strip() for s in re.split(r'[,+\s]+', s_val) if s.strip()]

    # Clean drive_url
    drive_url = re.sub(r'\|*__SECTIONS__:[a-zA-Z0-9_,]+', '', raw_input).strip().strip('|')

    # Auto-detect sections from saved output metadata JSON if not provided
    if not sections:
        meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"), reverse=True)
        if not meta_candidates:
            meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*.json"), reverse=True)
        if meta_candidates:
            try:
                with open(meta_candidates[0], 'r', encoding='utf-8') as f:
                    m = json.load(f)
                    saved_secs = m.get("selected_sections")
                    if saved_secs:
                        sections = saved_secs
            except Exception:
                pass

    # Resolve active section categories
    has_movie = True
    has_release = True
    has_ott = True
    if sections:
        s_norm = [str(s).lower().strip() for s in sections]
        is_all = any(x in s_norm for x in ['all', 'all_sections', 'all_3', '*']) or len(s_norm) == 3
        if not is_all:
            has_movie = any('movie' in s for s in s_norm)
            has_release = any('release' in s or 'theater' in s for s in s_norm)
            has_ott = any('ott' in s for s in s_norm)

    # Dynamic bottom title and top broadcast badge based on active sections
    if has_movie and not has_release and not has_ott:
        thumb_title = "LATEST MALAYALAM MOVIE UPDATES"
        badge_text = "MOVIE NEWS • EXCLUSIVE UPDATE"
        target_tabs = ["Movie Updates"]
        target_folders = ["movie_updates"]
    elif has_release and not has_movie and not has_ott:
        thumb_title = "UPCOMING THEATER RELEASES"
        badge_text = "THEATER RELEASES • EXCLUSIVE UPDATE"
        target_tabs = ["Release Updates"]
        target_folders = ["release_updates"]
    elif has_ott and not has_movie and not has_release:
        thumb_title = "LATEST OTT STREAMING RELEASES"
        badge_text = "OTT RELEASES • STREAMING UPDATE"
        target_tabs = ["OTT Updates"]
        target_folders = ["ott_updates"]
    elif has_movie and has_release and not has_ott:
        thumb_title = "MALAYALAM MOVIE & THEATER RELEASES"
        badge_text = "CINEMA UPDATES • EXCLUSIVE NEWS"
        target_tabs = ["Movie Updates", "Release Updates"]
        target_folders = ["movie_updates", "release_updates"]
    elif has_movie and has_ott and not has_release:
        thumb_title = "MALAYALAM MOVIE & OTT RELEASES"
        badge_text = "CINEMA & OTT • EXCLUSIVE NEWS"
        target_tabs = ["Movie Updates", "OTT Updates"]
        target_folders = ["movie_updates", "ott_updates"]
    elif has_release and has_ott and not has_movie:
        thumb_title = "THEATER & OTT STREAMING RELEASES"
        badge_text = "NEW RELEASES • THEATER & OTT"
        target_tabs = ["Release Updates", "OTT Updates"]
        target_folders = ["release_updates", "ott_updates"]
    else:
        thumb_title = "MALAYALAM MOVIES, THEATER & OTT"
        badge_text = "MOVIE NEWS • EXCLUSIVE UPDATE"
        target_tabs = ["Movie Updates", "Release Updates", "OTT Updates"]
        target_folders = ["movie_updates", "release_updates", "ott_updates"]

    # 1. If drive_url is a Google Drive shareable link, download directly
    if "drive.google.com" in drive_url or "/file/d/" in drive_url:
        match1 = re.search(r'/file/d/([a-zA-Z0-9_-]+)', drive_url)
        match2 = re.search(r'id=([a-zA-Z0-9_-]+)', drive_url)
        file_id = match1.group(1) if match1 else (match2.group(1) if match2 else "")

        save_path = THUMBNAIL_DIR / save_filename
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        urls_to_try = []
        if file_id:
            urls_to_try.append(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1920")
            urls_to_try.append(f"https://lh3.googleusercontent.com/d/{file_id}")
            urls_to_try.append(f"https://drive.google.com/uc?export=download&id={file_id}")
        else:
            urls_to_try.append(drive_url)

        for u in urls_to_try:
            try:
                r = requests.get(u, headers=headers, verify=False, timeout=25)
                if r.status_code == 200 and len(r.content) > 1000 and not r.content.startswith(b'<!DOCTYPE') and not r.content.startswith(b'<html'):
                    with open(save_path, 'wb') as f:
                        f.write(r.content)
                    print(f"[OK] Thumbnail downloaded from Google Drive: {save_path}")
                    return str(save_path)
            except Exception as e:
                print(f"[!] Warning trying Google Drive endpoint: {e}")

    # 2. Extract current active topic posters from latest generated metadata JSON
    current_topic_posters = []
    meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"), reverse=True)
    if not meta_candidates:
        meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*.json"), reverse=True)

    if meta_candidates:
        try:
            with open(meta_candidates[0], 'r', encoding='utf-8') as f:
                meta = json.load(f)
                items = meta.get("topic_items", [])
                for it in items:
                    sec_slug = it.get("section_slug", "")
                    if not target_folders or sec_slug in target_folders or not sections:
                        poster = it.get("movie_poster_path")
                        if poster and Path(poster).exists() and str(poster) not in current_topic_posters:
                            current_topic_posters.append(str(poster))
                        for u in it.get("image_urls", []):
                            if u and u.startswith("http") and u not in current_topic_posters:
                                current_topic_posters.append(u)
        except Exception as e:
            print(f"[!] Warning reading active topic items for thumbnail: {e}")

    # Build set of all valid URLs from current sheet_data target_tabs
    sheet_topic_posters = []
    if not sheet_data:
        cache_file = OUTPUT_DIR / "sheet_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    sheet_data = json.load(f)
            except Exception:
                pass

    if sheet_data and isinstance(sheet_data, dict):
        for tab_name in target_tabs:
            if tab_name in sheet_data:
                raw_val = sheet_data[tab_name]
                rows = raw_val.to_dict(orient="records") if hasattr(raw_val, 'to_dict') else (raw_val if isinstance(raw_val, list) else [])
                for row in rows:
                    if isinstance(row, dict):
                        raw_img = row.get("Image URLs", "") or row.get("Image", "") or row.get("URL", "")
                        if raw_img and str(raw_img).lower() != 'nan':
                            for u in re.split(r'[\r\n,]+', str(raw_img)):
                                u_clean = u.strip()
                                if u_clean.startswith("http") and u_clean not in sheet_topic_posters:
                                    sheet_topic_posters.append(u_clean)

    # 3. Handle image URLs passed in drive_url (from Thumbnail Studio or parameters)
    image_urls = []
    if drive_url and "http" in drive_url:
        candidates = [u.strip() for u in re.split(r'[\r\n,]+', drive_url) if u.strip().startswith("http")]
        # Validate candidate URLs: do they match current active topics?
        valid_pool = set(current_topic_posters + sheet_topic_posters)
        # If pool exists, only accept candidates that belong to current topics
        if valid_pool:
            matching = [u for u in candidates if u in valid_pool or any(Path(p).name in u for p in current_topic_posters if not p.startswith("http"))]
            if matching:
                image_urls = matching
            else:
                print(f"[THUMBNAIL] Notice: Passed thumbnail URLs do not match current active topics for this video. Discarding stale previous-day selection.")
        else:
            image_urls = candidates

    # 4. If no explicit valid URLs, use current active topic posters
    if not image_urls:
        if current_topic_posters:
            print(f"[THUMBNAIL] Using {len(current_topic_posters)} poster(s) from current active video topics.")
            image_urls = current_topic_posters[:6]
        elif sheet_topic_posters:
            print(f"[THUMBNAIL] Using {len(sheet_topic_posters)} poster(s) from current sheet target tabs: {target_tabs}.")
            image_urls = sheet_topic_posters[:6]

    # 5. Fallback: Scan local downloaded topic_images directory restricted to target_folders
    if not image_urls:
        topic_img_dir = OUTPUT_DIR / "topic_images"
        if topic_img_dir.exists():
            for folder_slug in target_folders:
                sec_dir = topic_img_dir / folder_slug
                if sec_dir.exists():
                    for img_file in sorted(sec_dir.glob("**/*.[jJ][pP][gG]")):
                        if str(img_file) not in image_urls:
                            image_urls.append(str(img_file))
                            if len(image_urls) >= 4:
                                break
                    for img_file in sorted(sec_dir.glob("**/*.[pP][nN][gG]")):
                        if str(img_file) not in image_urls:
                            image_urls.append(str(img_file))
                            if len(image_urls) >= 4:
                                break
                if len(image_urls) >= 4:
                    break

    # 6. Generate Automated 1280x720 YouTube Thumbnail Collage
    if image_urls:
        try:
            from thumbnail_generator import create_collage_thumbnail
            print(f"[THUMBNAIL] Generating Automated YouTube Thumbnail Collage from {len(image_urls)} image(s)...")
            print(f"    [TITLE] '{thumb_title}' | [BADGE] '{badge_text}'")
            return create_collage_thumbnail(image_urls, thumb_title, save_filename, badge_text=badge_text)
        except Exception as e:
            print(f"[!] Warning generating thumbnail collage: {e}")

    # Final Fallback: Generate template collage with dynamic branding
    try:
        from thumbnail_generator import create_collage_thumbnail
        print("[THUMBNAIL] Generating fallback YouTube Thumbnail Collage...")
        return create_collage_thumbnail([], thumb_title, save_filename, badge_text=badge_text)
    except Exception as e:
        print(f"[!] Error generating fallback thumbnail collage: {e}")
        return None


def generate_english_title(month_year: Optional[str] = None, sections: Optional[List[str]] = None) -> str:
    """Generates clean, professional English SEO YouTube video title matching active sections."""
    if not month_year:
        now = datetime.datetime.now()
        month_year = now.strftime("%B %Y")  # e.g. September 2026

    if not sections:
        # Check if metadata json contains selected_sections
        meta_candidates = list(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"))
        if meta_candidates:
            try:
                with open(meta_candidates[0], 'r', encoding='utf-8') as f:
                    m = json.load(f)
                    sections = m.get("selected_sections")
            except Exception:
                pass

    if sections:
        s_norm = [str(s).lower() for s in sections]
        has_movie = any("movie" in s for s in s_norm)
        has_release = any("release" in s or "theater" in s for s in s_norm)
        has_ott = any("ott" in s for s in s_norm)

        if has_movie and not has_release and not has_ott:
            return f"Latest Malayalam Movie Updates & Cinema News | {month_year}"
        elif has_release and not has_movie and not has_ott:
            return f"Upcoming Malayalam Theater Releases & Box Office News | {month_year}"
        elif has_ott and not has_movie and not has_release:
            return f"Latest Malayalam OTT Releases & Streaming Updates | {month_year}"
        elif has_movie and has_release and not has_ott:
            return f"Malayalam Movie News & Theater Release Updates | {month_year}"
        elif has_movie and has_ott and not has_release:
            return f"Malayalam Movie News & OTT Release Updates | {month_year}"
        elif has_release and has_ott and not has_movie:
            return f"Malayalam Theater Releases & OTT Streaming Updates | {month_year}"
        elif has_movie and has_release and has_ott:
            return f"Malayalam Movie News, Theater Releases & OTT Updates | {month_year}"

    return f"Malayalam Movie News, Theater Releases & OTT Updates | {month_year}"


def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats float seconds into M:SS or H:MM:SS YouTube chapter format."""
    secs = int(seconds)
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins}:{rem_secs:02d}"


def generate_youtube_description(
    sheet_data: Dict[str, List[Dict[str, Any]]],
    chunk_timestamps: Optional[List[Tuple[str, float]]] = None,
    sections: Optional[List[str]] = None
) -> str:
    """
    Generates YouTube video description complete with:
    - Timestamped Video Chapters
    - Topic Headline Bullet Points
    - Channel Disclaimer & Hashtags
    """
    if not sections:
        meta_candidates = list(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"))
        if meta_candidates:
            try:
                with open(meta_candidates[0], 'r', encoding='utf-8') as f:
                    m = json.load(f)
                    sections = m.get("selected_sections")
            except Exception:
                pass

    desc_lines = []
    
    desc_lines.append("Latest Malayalam Movie News, Upcoming Theater Release Dates, and OTT Streaming Updates!")
    desc_lines.append("")

    # 1. Video Chapters
    desc_lines.append("⏱️ VIDEO CHAPTERS:")
    desc_lines.append("0:00 🎬 Introduction")

    # Dynamic chapter estimates if exact timestamps aren't passed
    if not chunk_timestamps:
        s_norm = [str(s).lower() for s in (sections or [])]
        has_movie = not sections or any("movie" in s for s in s_norm)
        has_release = not sections or any("release" in s or "theater" in s for s in s_norm)
        has_ott = not sections or any("ott" in s for s in s_norm)

        est_time = 4
        if has_movie:
            desc_lines.append(f"{format_seconds_to_timestamp(est_time)} 🎭 Movie Updates")
            est_time += 99
        if has_release:
            desc_lines.append(f"{format_seconds_to_timestamp(est_time)} 📅 Theater Release Updates")
            est_time += 105
        if has_ott:
            desc_lines.append(f"{format_seconds_to_timestamp(est_time)} 🍿 OTT Streaming Updates")
            est_time += 82
        desc_lines.append(f"{format_seconds_to_timestamp(est_time)} 🎬 Conclusion & Outro")
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
        if "thumb" in str(section_name).lower() or "config" in str(section_name).lower():
            continue

        # If sections filter is active, skip sheets not in active selection
        if sections:
            s_name_low = str(section_name).lower().replace(" ", "_")
            if not any(s.lower() in s_name_low or s_name_low in s.lower() for s in sections):
                continue

        desc_lines.append(f"\n🔹 {section_name.upper()}:")
        
        # Handle both DataFrame and list of dicts
        rows_iter = topics.iterrows() if hasattr(topics, 'iterrows') else enumerate(topics, start=1)
        for idx, item in enumerate(topics if not hasattr(topics, 'iterrows') else topics.to_dict(orient="records"), start=1):
            # Prefer Column D (Topic Headline) over Column B (Malayalam News Text)
            headline = str(item.get("Topic Headline", item.get("headline", item.get("Headline", "")))).strip()
            if not headline or headline.lower() == "nan":
                # Fallback to Column B if Column D is empty
                headline = str(item.get("Malayalam News Text", item.get("text", ""))).strip()

            if not headline or headline.lower() == "nan":
                continue

            desc_lines.append(f"  {idx}. {headline}")

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
