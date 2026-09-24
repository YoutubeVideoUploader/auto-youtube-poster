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

    # 3. Priority A: Explicit image URLs passed in drive_url (from Thumbnail Studio or parameters)
    image_urls = []
    custom_brief = {}
    if drive_url and "__THUMB_" in drive_url:
        import urllib.parse

        def _dec(pattern):
            m = re.search(pattern, drive_url)
            if not m:
                return ""
            val = m.group(1).strip()
            try:
                return urllib.parse.unquote(val)
            except Exception:
                return val

        m_hook = _dec(r'__THUMB_HOOK__:([^|]+)')
        m_sub = _dec(r'__THUMB_SUB__:([^|]+)')
        m_badge = _dec(r'__THUMB_BADGE__:([^|]+)')
        m_theme = _dec(r'__THUMB_THEME__:([^|]+)')
        m_layout = _dec(r'__THUMB_LAYOUT__:([^|]+)')
        m_center = _dec(r'__THUMB_CENTER__:([^|]+)')

        m_s1_t = _dec(r'__THUMB_S1_TEXT__:([^|]+)')
        m_s1_b = _dec(r'__THUMB_S1_BADGE__:([^|]+)')
        m_s2_t = _dec(r'__THUMB_S2_TEXT__:([^|]+)')
        m_s2_b = _dec(r'__THUMB_S2_BADGE__:([^|]+)')
        m_s3_t = _dec(r'__THUMB_S3_TEXT__:([^|]+)')
        m_s3_b = _dec(r'__THUMB_S3_BADGE__:([^|]+)')
        m_s4_t = _dec(r'__THUMB_S4_TEXT__:([^|]+)')
        m_s4_b = _dec(r'__THUMB_S4_BADGE__:([^|]+)')

        if m_s1_t or m_hook:
            custom_brief = {
                "main_hook": (m_s1_t or m_hook).strip(),
                "sub_text": m_sub.strip() if m_sub else "CINEMA EXCLUSIVE",
                "badge": m_badge.strip() if m_badge else "BREAKING NEWS",
                "center_badge": m_center.strip() if m_center else "TOP 4",
                "color_theme": m_theme.strip().lower() if m_theme else "crimson",
                "layout_style": m_layout.strip().lower() if m_layout else "quad",
                "slot1_text": m_s1_t or m_hook,
                "slot1_badge": m_s1_b or "BREAKING NEWS",
                "slot2_text": m_s2_t,
                "slot2_badge": m_s2_b or "SHOCKING SPLIT",
                "slot3_text": m_s3_t,
                "slot3_badge": m_s3_b or "EXCLUSIVE",
                "slot4_text": m_s4_t,
                "slot4_badge": m_s4_b or "MASS UPDATE",
            }
            print(f"[THUMBNAIL] Unpacked user-customized quad brief from workflow payload: {custom_brief}")


    if drive_url and "http" in drive_url:
        # Strip all tags before extracting URLs
        clean_drive_str = re.sub(r'\|*__SECTIONS__:[a-zA-Z0-9_,]+', '', drive_url)
        clean_drive_str = re.sub(r'\|*__THUMB_[A-Z]+__:[^|]+', '', clean_drive_str)
        candidates = [u.strip() for u in re.split(r'[\r\n,]+', clean_drive_str)]
        candidates = [u for u in candidates if u.startswith("http")]
        if candidates:
            print(f"[THUMBNAIL] Using {len(candidates)} explicit image URL(s) passed from user selection.")
            image_urls = candidates[:6]

    # 4. Priority B: Check Google Sheet 'Thumbnail Config' tab (from sheet_data or sheet_cache.json)
    if not image_urls:
        thumb_config_urls = []
        if sheet_data and isinstance(sheet_data, dict) and "Thumbnail Config" in sheet_data:
            raw_tc = sheet_data["Thumbnail Config"]
            tc_rows = raw_tc.to_dict(orient="records") if hasattr(raw_tc, 'to_dict') else (raw_tc if isinstance(raw_tc, list) else [])
            for r in tc_rows:
                if isinstance(r, dict):
                    raw_u = r.get("Selected Image URLs", "") or r.get("Image URLs", "") or r.get("URL", "")
                    clean_u = re.sub(r'\|*__SECTIONS__:[a-zA-Z0-9_,]+', '', str(raw_u)).strip()
                    if clean_u.startswith("http") and clean_u not in thumb_config_urls:
                        thumb_config_urls.append(clean_u)

        if not thumb_config_urls:
            cache_file = OUTPUT_DIR / "sheet_cache.json"
            if cache_file.exists():
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        sc = json.load(f)
                        if "Thumbnail Config" in sc and isinstance(sc["Thumbnail Config"], list):
                            for r in sc["Thumbnail Config"]:
                                if isinstance(r, dict):
                                    raw_u = r.get("Selected Image URLs", "") or r.get("Image URLs", "") or r.get("URL", "")
                                    clean_u = re.sub(r'\|*__SECTIONS__:[a-zA-Z0-9_,]+', '', str(raw_u)).strip()
                                    if clean_u.startswith("http") and clean_u not in thumb_config_urls:
                                        thumb_config_urls.append(clean_u)
                except Exception:
                    pass

        if thumb_config_urls:
            print(f"[THUMBNAIL] Using {len(thumb_config_urls)} user-selected poster(s) from 'Thumbnail Config' sheet tab.")
            image_urls = thumb_config_urls[:6]

    # 5. Priority C: Fallback to current active topic posters
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

    # 6. Generate Next-Gen AI-powered 1280x720 YouTube Thumbnail
    if image_urls:
        try:
            from thumbnail_generator import create_nextgen_thumbnail
            print(f"[THUMBNAIL] Generating AI-powered Next-Gen YouTube Thumbnail from {len(image_urls)} image(s)...")
            brief = generate_ai_thumbnail_brief(sheet_data=sheet_data, sections=sections, custom_brief=custom_brief or None)
            print(f"    [AI BRIEF] main_hook='{brief.get('main_hook')}' | badge='{brief.get('badge')}' | theme='{brief.get('color_theme')}'")
            return create_nextgen_thumbnail(image_urls, brief, save_filename)
        except Exception as e:
            print(f"[!] Warning generating next-gen thumbnail: {e}")

    # Final Fallback: Generate template thumbnail with dynamic branding
    try:
        from thumbnail_generator import create_nextgen_thumbnail
        print("[THUMBNAIL] Generating fallback Next-Gen YouTube Thumbnail (no images)...")
        brief = generate_ai_thumbnail_brief(sheet_data=sheet_data, sections=sections, custom_brief=custom_brief or None)
        return create_nextgen_thumbnail([], brief, save_filename)
    except Exception as e:
        print(f"[!] Error generating fallback next-gen thumbnail: {e}")
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
            return f"Latest Movie News & Cinema News | {month_year}"
        elif has_release and not has_movie and not has_ott:
            return f"Upcoming Theater Releases & Box Office News | {month_year}"
        elif has_ott and not has_movie and not has_release:
            return f"Latest OTT Releases & Streaming Updates | {month_year}"
        elif has_movie and has_release and not has_ott:
            return f"Movie News & Theater Release Updates | {month_year}"
        elif has_movie and has_ott and not has_release:
            return f"Movie News & OTT Release Updates | {month_year}"
        elif has_release and has_ott and not has_movie:
            return f"Theater Releases & OTT Streaming Updates | {month_year}"
        elif has_movie and has_release and has_ott:
            return f"Latest Movie News, Theater Releases & OTT Updates | {month_year}"

    return f"Latest Movie News, Theater Releases & OTT Updates | {month_year}"


def format_seconds_to_timestamp(seconds: float) -> str:
    """Formats float seconds into M:SS or H:MM:SS YouTube chapter format."""
    secs = int(seconds)
    mins = secs // 60
    rem_secs = secs % 60
    return f"{mins}:{rem_secs:02d}"


_AI_METADATA_CACHE: Optional[Dict[str, Any]] = None
_AI_THUMBNAIL_BRIEF_CACHE: Optional[Dict[str, Any]] = None


def normalize_youtube_chapters(raw_chapters: List[Dict[str, Any]], total_duration: float = 0.0) -> List[Dict[str, Any]]:
    """
    Enforces YouTube's strict chapter requirements:
    1. First timestamp must be 00:00.
    2. Minimum chapter length must be at least 10 seconds.
    3. Minimum 3 chapters.
    4. Two-digit minute formatting (00:00).
    5. Omit trailing outro if under 10 seconds before video end.
    """
    if not raw_chapters:
        return []

    clean = []
    last_sec = -10.0

    for i, c in enumerate(raw_chapters):
        t_sec = float(c.get("time_sec", 0.0))
        if t_sec == 0.0 and "timestamp" in c:
            # parse seconds from timestamp string like '0:08' or '00:10'
            try:
                parts = str(c["timestamp"]).split(":")
                t_sec = float(parts[0]) * 60 + float(parts[1])
            except Exception:
                t_sec = 0.0

        title = str(c.get("title", "")).strip()
        ctype = c.get("type", "topic")
        if not title:
            continue

        if i == 0 or ctype == "intro":
            clean.append({"timestamp": "00:00", "time_sec": 0.0, "title": title or "Introduction", "type": "intro"})
            last_sec = 0.0
            continue

        # Force at least 10 seconds gap between chapters
        target_sec = max(last_sec + 10.0, t_sec)

        # Skip outro if it is under 10 seconds from total duration
        if ctype == "outro" and total_duration > 0 and (total_duration - target_sec) < 10.0:
            continue

        mins = int(target_sec) // 60
        secs = int(target_sec) % 60
        clean.append({
            "timestamp": f"{mins:02d}:{secs:02d}",
            "time_sec": round(target_sec, 2),
            "title": title,
            "section": c.get("section", ""),
            "type": ctype
        })
        last_sec = target_sec

    return clean


def get_specific_video_chapters(sections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Loads specific topic-level chapters with exact timestamps, strictly enforcing YouTube's 10-second rule and 00:00 format."""
    chapters_file = OUTPUT_DIR / "video_chapters.json"
    if chapters_file.exists():
        try:
            with open(chapters_file, "r", encoding="utf-8") as f:
                ch = json.load(f)
                if isinstance(ch, list) and len(ch) >= 2:
                    return normalize_youtube_chapters(ch)
        except Exception:
            pass

    # Extract from latest metadata JSON
    meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"), reverse=True)
    if not meta_candidates:
        meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*.json"), reverse=True)

    if meta_candidates:
        try:
            with open(meta_candidates[0], "r", encoding="utf-8") as f:
                d = json.load(f)
                tot_dur = float(d.get("total_duration", 0.0))
                if "specific_chapters" in d and isinstance(d["specific_chapters"], list) and len(d["specific_chapters"]) >= 2:
                    return normalize_youtube_chapters(d["specific_chapters"], total_duration=tot_dur)

                script_meta = d.get("script_metadata", [])
                topic_items = d.get("topic_items", [])
                if script_meta and topic_items:
                    raw_ch = [{"timestamp": "00:00", "time_sec": 0.0, "title": "Introduction", "type": "intro"}]
                    cur_time = 0.0
                    t_idx = 0
                    for seg in script_meta:
                        stype = seg.get("type", "")
                        dur = float(seg.get("duration", 0.0))
                        if stype == "headline":
                            item = topic_items[t_idx] if t_idx < len(topic_items) else {}
                            t_idx += 1
                            hl = str(item.get("topic_headline", f"Topic {t_idx}")).strip()
                            raw_ch.append({
                                "time_sec": cur_time,
                                "title": hl,
                                "section": item.get("section", ""),
                                "type": "topic"
                            })
                        elif stype == "outro":
                            raw_ch.append({"time_sec": cur_time, "title": "Conclusion & Outro", "type": "outro"})
                        cur_time += dur

                    return normalize_youtube_chapters(raw_ch, total_duration=cur_time)
        except Exception as e:
            print(f"[!] Warning reading metadata chapters: {e}")

    # Fallback chapters (strictly >= 10s gap)
    return [
        {"timestamp": "00:00", "title": "Introduction", "type": "intro"},
        {"timestamp": "00:10", "title": "Movie Updates & News", "type": "topic"},
        {"timestamp": "01:30", "title": "Upcoming Theater Releases", "type": "topic"},
        {"timestamp": "02:45", "title": "Latest OTT Streaming Arrivals", "type": "topic"},
        {"timestamp": "04:30", "title": "Conclusion & Outro", "type": "outro"}
    ]


def extract_active_topics_flat(sheet_data: Any, sections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Flattens sheet_data topics into a clean list of topic dictionaries with cache fallback."""
    flat = []
    if isinstance(sheet_data, dict):
        for sec_name, topics in sheet_data.items():
            if topics is None:
                continue
            if hasattr(topics, "empty") and topics.empty:
                continue
            if isinstance(topics, (list, tuple)) and len(topics) == 0:
                continue

            sec_lower = str(sec_name).lower()
            if any(k in sec_lower for k in ["thumb", "config", "upload", "key", "setting"]):
                continue

            if sections:
                s_name_low = str(sec_name).lower().replace(" ", "_")
                if not any(s.lower() in s_name_low or s_name_low in s.lower() for s in sections):
                    continue

            rows = topics.to_dict(orient="records") if hasattr(topics, "to_dict") else (topics if isinstance(topics, list) else [])
            for r in rows:
                if isinstance(r, dict):
                    hl = str(r.get("Topic Headline") or r.get("Movie Name") or r.get("headline") or "").strip()
                    txt = str(r.get("Malayalam News Text") or r.get("text") or "").strip()
                    rdate = str(r.get("Release Date") or "").strip()
                    plat = str(r.get("OTT Platform") or "").strip()
                    if hl or txt:
                        flat.append({
                            "section": sec_name,
                            "topic_headline": hl if hl and hl.lower() != "nan" else txt[:50],
                            "topic_text": txt if txt.lower() != "nan" else "",
                            "release_date": rdate if rdate.lower() != "nan" else "",
                            "ott_platform": plat if plat.lower() != "nan" else ""
                        })

    if not flat:
        cache_p = OUTPUT_DIR / "sheet_cache.json"
        if cache_p.exists():
            try:
                with open(cache_p, "r", encoding="utf-8") as f:
                    sc = json.load(f)
                    flat = extract_active_topics_flat(sc, sections=sections)
            except Exception:
                pass

    if not flat:
        meta_candidates = sorted(OUTPUT_DIR.glob("GoogleSheet_Malayalam_Movie_News_*_v4.0.json"), reverse=True)
        if meta_candidates:
            try:
                with open(meta_candidates[0], "r", encoding="utf-8") as f:
                    m = json.load(f)
                    flat = m.get("topic_items", [])
            except Exception:
                pass

    return flat


def sanitize_youtube_tags(raw_tags: List[Any], max_total_chars: int = 400) -> List[str]:
    """
    Sanitizes tags for YouTube Data API v3 snippet.tags:
    - Strips invalid characters (<, >, #, commas, quotes, control characters).
    - Ensures each tag is 2-40 characters.
    - Dedupes case-insensitively.
    - Caps total combined length to strictly under max_total_chars (default 400, YouTube limit 500).
    """
    clean_list = []
    seen = set()
    current_len = 0

    for t in raw_tags:
        if not t:
            continue
        cleaned = re.sub(r'[#<>"\',`]', '', str(t)).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        if len(cleaned) < 2 or len(cleaned) > 40:
            continue
        cleaned_lower = cleaned.lower()
        if cleaned_lower in seen:
            continue

        tag_cost = len(cleaned) + (1 if clean_list else 0)
        if current_len + tag_cost > max_total_chars:
            break

        seen.add(cleaned_lower)
        clean_list.append(cleaned)
        current_len += tag_cost

    if not clean_list:
        clean_list = ["Movie News", "Cinema Updates", "Mollywood", "Film Trailers", "OTT Releases"]

    return clean_list


def generate_ai_thumbnail_brief(
    sheet_data: Optional[Dict[str, Any]] = None,
    sections: Optional[List[str]] = None,
    gemini_key: Optional[str] = None,
    custom_brief: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Uses Gemini API as Creative Art Director to analyze active video topics and generate
    a broadcast-quality thumbnail creative brief:
      - main_hook:    2-4 word punchy power phrase (e.g. "FAHADH MASS BLAST!")
      - sub_text:     supporting star/movie callout (e.g. "BIJU MENON • SHRUTI HAASAN")
      - badge:        high-urgency ribbon badge (e.g. "OFFICIAL TRAILER", "BREAKING")
      - color_theme:  mood color ("crimson", "gold", or "cyan")
      - layout_style: composition ("diagonal_clash", "hero_focus", or "cinematic_duo")

    Prioritizes user-edited fields from custom_brief or the 'Thumbnail Config' sheet tab!
    Falls back to deterministic extraction if Gemini is unavailable.
    """
    global _AI_THUMBNAIL_BRIEF_CACHE
    if custom_brief and custom_brief.get("main_hook"):
        _AI_THUMBNAIL_BRIEF_CACHE = custom_brief
        return _AI_THUMBNAIL_BRIEF_CACHE

    if _AI_THUMBNAIL_BRIEF_CACHE is not None:
        return _AI_THUMBNAIL_BRIEF_CACHE

    # ── Check Google Sheet 'Thumbnail Config' tab for user custom text ──────
    if sheet_data and isinstance(sheet_data, dict) and "Thumbnail Config" in sheet_data:
        raw_tc = sheet_data["Thumbnail Config"]
        tc_rows = raw_tc.to_dict(orient="records") if hasattr(raw_tc, 'to_dict') else (raw_tc if isinstance(raw_tc, list) else [])
        for r in tc_rows:
            if isinstance(r, dict):
                hook = str(r.get("Main Hook") or r.get("main_hook") or "").strip()
                sub = str(r.get("Sub Text") or r.get("sub_text") or "").strip()
                badge = str(r.get("Badge Label") or r.get("badge") or "").strip()
                theme = str(r.get("Color Theme") or r.get("color_theme") or "").strip()
                layout = str(r.get("Layout Style") or r.get("layout_style") or "").strip()

                s1_t = str(r.get("Slot 1 Text") or r.get("slot1_text") or "").strip()
                s1_b = str(r.get("Slot 1 Badge") or r.get("slot1_badge") or "").strip()
                s2_t = str(r.get("Slot 2 Text") or r.get("slot2_text") or "").strip()
                s2_b = str(r.get("Slot 2 Badge") or r.get("slot2_badge") or "").strip()
                s3_t = str(r.get("Slot 3 Text") or r.get("slot3_text") or "").strip()
                s3_b = str(r.get("Slot 3 Badge") or r.get("slot3_badge") or "").strip()
                s4_t = str(r.get("Slot 4 Text") or r.get("slot4_text") or "").strip()
                s4_b = str(r.get("Slot 4 Badge") or r.get("slot4_badge") or "").strip()
                center = str(r.get("Center Badge") or r.get("center_badge") or "").strip()

                if s1_t or hook:
                    print(f"[THUMBNAIL] Using user-customized brief from Google Sheet: s1='{s1_t}', hook='{hook}'")
                    _AI_THUMBNAIL_BRIEF_CACHE = {
                        "main_hook": (s1_t or hook).strip(),
                        "sub_text": sub.strip() if sub else "CINEMA EXCLUSIVE",
                        "badge": badge.strip() if badge else "BREAKING NEWS",
                        "center_badge": center.strip() if center else "TOP 4",
                        "color_theme": theme.lower() or "crimson",
                        "layout_style": layout.lower() or "quad",
                        "slot1_text": s1_t or hook,
                        "slot1_badge": s1_b or "BREAKING NEWS",
                        "slot2_text": s2_t,
                        "slot2_badge": s2_b or "SHOCKING SPLIT",
                        "slot3_text": s3_t,
                        "slot3_badge": s3_b or "EXCLUSIVE",
                        "slot4_text": s4_t,
                        "slot4_badge": s4_b or "MASS UPDATE"
                    }
                    return _AI_THUMBNAIL_BRIEF_CACHE


    # ── Extract active topics ──────────────────────────────────────────────
    topics_list = extract_active_topics_flat(sheet_data, sections=sections)

    # Build topic summary for prompt
    topic_summaries = []
    for i, t in enumerate(topics_list[:15], 1):
        sec = t.get("section", "")
        hl = t.get("topic_headline", "")
        plat = t.get("ott_platform", "")
        rdate = t.get("release_date", "")
        extra = f" (Platform: {plat})" if plat else (f" (Release: {rdate})" if rdate else "")
        if hl:
            topic_summaries.append(f"{i}. [{sec}] {hl}{extra}")

    topics_text = "\n".join(topic_summaries) if topic_summaries else "Latest Malayalam cinema news and OTT updates."

    # Determine active section types for fallback
    has_ott = any("ott" in str(t.get("section", "")).lower() for t in topics_list)
    has_release = any("release" in str(t.get("section", "")).lower() or "theater" in str(t.get("section", "")).lower() for t in topics_list)

    # ── Try Gemini API ─────────────────────────────────────────────────────
    try:
        from models.gemini_tts_engine import GeminiTTSEngine
        keys = GeminiTTSEngine()._resolve_api_keys(gemini_key)
        active_key = keys[0] if keys else None
    except Exception:
        active_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")

    if active_key:
        prompt = f"""You are a viral YouTube thumbnail creative director for a Malayalam cinema entertainment channel.
Analyze these cinema news topics:
{topics_text}

Create a viral 1280x720 YouTube thumbnail creative brief. Return ONLY a valid JSON with exactly these 5 keys:
{{
  "main_hook": "2-4 WORD PUNCHY POWER PHRASE IN ENGLISH CAPS (e.g. FAHADH MASS BLAST! or BREAKING TRAILER DROP!)",
  "sub_text": "ACTOR NAMES or MOVIE NAMES separated by bullet dots • (max 40 chars, e.g. BIJU MENON • SHRUTI HAASAN)",
  "badge": "ONE URGENT BADGE LABEL (e.g. OFFICIAL TRAILER, BREAKING, EXCLUSIVE, OTT DROP, FIRST LOOK)",
  "color_theme": "crimson OR gold OR cyan (crimson=action/drama, gold=awards/major release, cyan=OTT/streaming)",
  "layout_style": "diagonal_clash OR hero_focus OR cinematic_duo"
}}
RULES:
- main_hook must be max 24 chars, ALL CAPS English only, punchy and emotion-driven
- sub_text max 45 chars, English only
- badge max 25 chars
- color_theme: choose cyan if mostly OTT topics, gold if major theatrical release, else crimson
- layout_style: diagonal_clash for 2 stars clash, hero_focus for 1 main star + 2 secondary, cinematic_duo for side-by-side
"""
        for model_name in ["gemini-flash-latest", "gemini-2.0-flash", "gemini-pro-latest"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}
            }
            try:
                res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
                if res.status_code == 200:
                    body = res.json()
                    text_resp = body["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text_resp)
                    required_keys = {"main_hook", "sub_text", "badge", "color_theme", "layout_style"}
                    if required_keys.issubset(data.keys()):
                        print(f"[Gemini AI] ({model_name}) Generated thumbnail brief: {data}")
                        _AI_THUMBNAIL_BRIEF_CACHE = data
                        return _AI_THUMBNAIL_BRIEF_CACHE
                else:
                    print(f"[!] Gemini thumbnail brief ({model_name}) returned {res.status_code}: {res.text[:80]}")
            except Exception as e:
                print(f"[!] Warning calling Gemini for thumbnail brief ({model_name}): {e}")

    # ── Deterministic Fallback ─────────────────────────────────────────────
    print("[*] Using deterministic thumbnail brief fallback")
    # Pick biggest star from first topic headline
    top_headline = topics_list[0].get("topic_headline", "CINEMA") if topics_list else "CINEMA"
    second_headline = topics_list[1].get("topic_headline", "") if len(topics_list) > 1 else ""

    # Shorten to star/movie name: extract first N clean alpha-only words
    def shorten(s: str, words: int = 2) -> str:
        # Strip possessives ('s, 's) and special chars
        cleaned = re.sub(r"['\u2019\u2018`]s?\b", "", str(s))
        cleaned = re.sub(r"[^A-Za-z0-9\s\-]", " ", cleaned)
        parts = [p for p in cleaned.strip().split() if len(p) > 1][:words]
        return " ".join(parts).upper() if parts else "CINEMA"

    hook_star = shorten(top_headline, 2)
    sub_star = shorten(second_headline, 2) if second_headline else ""

    main_hook = f"{hook_star} EXCLUSIVE!"[:24]
    sub_text = f"{hook_star} • {sub_star}"[:45] if sub_star else hook_star[:45]

    if has_ott:
        badge, theme, layout = "OTT DROP", "cyan", "diagonal_clash"
    elif has_release:
        badge, theme, layout = "IN THEATERS", "gold", "diagonal_clash"
    else:
        badge, theme, layout = "BREAKING NEWS", "crimson", "hero_focus"

    _AI_THUMBNAIL_BRIEF_CACHE = {
        "main_hook": main_hook,
        "sub_text": sub_text,
        "badge": badge,
        "color_theme": theme,
        "layout_style": layout
    }
    return _AI_THUMBNAIL_BRIEF_CACHE


def generate_ai_metadata(
    sheet_data: Optional[Dict[str, Any]] = None,
    sections: Optional[List[str]] = None,
    gemini_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uses Google Gemini API (gemini-flash-latest / gemini-pro-latest) to generate:
    - 100% English YouTube description with engaging hook, specific topic chapters, and highlights.
    - 12-18 high-ranking English SEO tags (strictly under 400 chars).
    """
    global _AI_METADATA_CACHE
    if _AI_METADATA_CACHE is not None:
        return _AI_METADATA_CACHE

    chapters = get_specific_video_chapters(sections=sections)
    topics_list = extract_active_topics_flat(sheet_data, sections=sections)

    # Format chapters block (clean YouTube standard format)
    chapter_lines = ["Chapters:"]
    for c in chapters:
        chapter_lines.append(f"{c['timestamp']} - {c['title']}")
    chapters_block = "\n".join(chapter_lines)

    # Format topic summaries for prompt
    topic_summaries = []
    for i, t in enumerate(topics_list, 1):
        sec = t.get("section", "")
        hl = t.get("topic_headline", "")
        plat = t.get("ott_platform", "")
        rdate = t.get("release_date", "")
        extra = f" (Platform: {plat})" if plat else (f" (Release Date: {rdate})" if rdate else "")
        topic_summaries.append(f"{i}. [{sec}] {hl}{extra}")

    topics_prompt_text = "\n".join(topic_summaries) if topic_summaries else "Latest cinema releases, trailers, and OTT updates."

    # 1. Resolve Gemini Key
    from models.gemini_tts_engine import GeminiTTSEngine
    keys = GeminiTTSEngine()._resolve_api_keys(gemini_key)
    active_key = keys[0] if keys else None

    if active_key:
        prompt = f"""You are an elite YouTube SEO strategist for a cinema entertainment channel.
Create video metadata based on these cinema news topics:
{topics_prompt_text}

Specific Video Chapters:
{chapters_block}

CRITICAL RULES:
1. Output strictly in 100% English. DO NOT output any Malayalam script or letters anywhere.
2. Return a valid JSON object with exactly two keys:
   "description": A comprehensive, beautifully formatted English description containing:
      - Catchy 2-3 sentence opening overview of today's cinema news
      - Include the exact "Chapters:" block provided above (preserve the exact 00:00 timestamps and titles)
      - "📌 TODAY'S CINEMA HIGHLIGHTS:" bullet points summarizing each topic in English
      - Call to action (Like, Share, Subscribe)
      - Top trending hashtags (e.g. #MovieNews #CinemaUpdates #OTTRelease #NewMovies #BoxOffice)
   "tags": An array of 12 to 18 concise English SEO keywords (each 1-3 words, NO hashtags #, NO commas, NO quotes, e.g. "Movie News", "Basil Joseph", "OTT Release"). Total combined length MUST be strictly under 400 characters.
"""
        # Try candidate models with fallback
        for model_name in ["gemini-flash-latest", "gemini-pro-latest"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "responseMimeType": "application/json"
                }
            }
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=20)
                if res.status_code == 200:
                    body = res.json()
                    text_resp = body["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text_resp)
                    if "description" in data and "tags" in data and isinstance(data["tags"], list):
                        safe_tags = sanitize_youtube_tags(data["tags"])
                        print(f"[Gemini AI] ({model_name}) Successfully generated dynamic English description & {len(safe_tags)} tags!")
                        _AI_METADATA_CACHE = {
                            "description": data["description"],
                            "tags": safe_tags,
                            "chapters": chapters_block
                        }
                        return _AI_METADATA_CACHE
                else:
                    print(f"[!] Gemini AI ({model_name}) returned {res.status_code}: {res.text[:100]}")
            except Exception as e:
                print(f"[!] Warning calling Gemini AI ({model_name}): {e}")

    # Fallback: Clean Deterministic English Metadata
    print("[*] Using deterministic English metadata generator (fallback)")
    desc_parts = [
        "Welcome to today's cinema news roundup! Catch all the latest movie announcements, upcoming theatrical release dates, and brand new OTT streaming updates right here.",
        "",
        chapters_block,
        "",
        "=" * 50,
        "📌 TODAY'S CINEMA HIGHLIGHTS:",
        "=" * 50
    ]
    for i, t in enumerate(topics_list, 1):
        hl = t.get("topic_headline", f"Topic {i}")
        sec = t.get("section", "")
        desc_parts.append(f"• [{sec}] {hl}")

    desc_parts.extend([
        "",
        "=" * 50,
        "🔔 Subscribe to our channel for daily movie news, trailers, and streaming updates!",
        "",
        "#MovieNews #CinemaUpdates #OTTRelease #BoxOffice #NewMovies #TrailerAlert"
    ])

    # Dynamic fallback tags
    raw_fallback_tags = ["Movie News", "Cinema Updates", "Movie Trailer", "OTT Releases", "Box Office News", "New Releases 2026"]
    for t in topics_list:
        hl = t.get("topic_headline", "")
        if hl and len(hl) < 40 and hl not in raw_fallback_tags:
            raw_fallback_tags.append(hl)
        plat = t.get("ott_platform", "")
        if plat and plat not in raw_fallback_tags:
            raw_fallback_tags.append(plat)

    safe_fallback_tags = sanitize_youtube_tags(raw_fallback_tags)
    _AI_METADATA_CACHE = {
        "description": "\n".join(desc_parts),
        "tags": safe_fallback_tags,
        "chapters": chapters_block
    }
    return _AI_METADATA_CACHE


def generate_youtube_description(
    sheet_data: Optional[Dict[str, Any]] = None,
    chunk_timestamps: Optional[List[Tuple[str, float]]] = None,
    sections: Optional[List[str]] = None
) -> str:
    """Generates dynamic English YouTube video description powered by Gemini AI with specific topic chapters."""
    ai_meta = generate_ai_metadata(sheet_data=sheet_data, sections=sections)
    return ai_meta.get("description", "")


def generate_youtube_tags(
    sheet_data: Optional[Dict[str, Any]] = None,
    sections: Optional[List[str]] = None
) -> List[str]:
    """Returns dynamic, high-ranking English SEO keywords list generated by Gemini AI (sanitized for YouTube API)."""
    ai_meta = generate_ai_metadata(sheet_data=sheet_data, sections=sections)
    return sanitize_youtube_tags(ai_meta.get("tags", [
        "Movie News",
        "Cinema Updates",
        "Box Office News",
        "OTT Release",
        "New Movie Trailers",
        "Latest Movie Releases 2026"
    ]))


def generate_youtube_chapters(
    sheet_data: Optional[Dict[str, Any]] = None,
    sections: Optional[List[str]] = None
) -> str:
    """Returns formatted English topic-level chapters block generated by Gemini AI / topic timestamps."""
    ai_meta = generate_ai_metadata(sheet_data=sheet_data, sections=sections)
    return ai_meta.get("chapters", "")

