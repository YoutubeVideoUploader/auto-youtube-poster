"""
Google Sheet Multi-Sheet Malayalam Movie News Voice Presenter v4.0
Parses 3 Google Spreadsheet Worksheets ('Movie Updates', 'Release Updates', 'OTT Updates'),
downloads ordered topic images, constructs structured section presenter markup scripts,
and synthesizes broadcast-quality audio with single Intro, section intros, and single Outro.
"""

import sys
import os
import re
import io
import time
import urllib.parse
import requests
import urllib3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Force UTF-8 stdout encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from synthesis.tts_engine import MalayalamVoiceEngine
from config import OUTPUT_DIR, DEFAULT_SAMPLE_RATE, SHEET_ORDER, GLOBAL_INTRO, GLOBAL_OUTRO, TEST_MODE

DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/15xkauNiB27ytehTI5XHgmLm5QmJvudnEegrGSmnx5_g/edit?gid=183267360#gid=183267360"
IMAGES_DIR = OUTPUT_DIR / "topic_images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.bing.com/',
}


def convert_sheet_url_to_xlsx_url(sheet_url: str) -> str:
    """Converts a standard Google Sheet edit/sharing URL into an export Excel (.xlsx) download URL."""
    doc_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
    if not doc_id_match:
        raise ValueError(f"Could not extract Document ID from Google Sheet URL: {sheet_url}")
    doc_id = doc_id_match.group(1)
    return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=xlsx"


def convert_sheet_url_to_csv_url(sheet_url: str) -> str:
    """Converts a standard Google Sheet edit/sharing URL into an export CSV download URL."""
    doc_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
    gid_match = re.search(r'gid=([0-9]+)', sheet_url)
    if not doc_id_match:
        raise ValueError(f"Could not extract Document ID from Google Sheet URL: {sheet_url}")
    doc_id = doc_id_match.group(1)
    gid = gid_match.group(1) if gid_match else "0"
    return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"


def _is_valid_image_bytes(content: bytes) -> bool:
    """Returns True if content bytes are a valid image (PIL-verifiable)."""
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        return True
    except Exception:
        return False


def extract_og_image_from_html(html: str) -> str:
    """Extracts og:image URL from HTML meta tags if present."""
    match = re.search(r'<meta[^>]+property=[\"\']og:image[\"\'][^>]+content=[\"\']([^\"\'\s>]+)[\"\']', html, re.IGNORECASE)
    if not match:
        match = re.search(r'<meta[^>]+content=[\"\']([^\"\'\s>]+)[\"\'][^>]+property=[\"\']og:image[\"\']', html, re.IGNORECASE)
    return match.group(1) if match else ''


def upgrade_url_to_hd(url: str) -> str:
    """Upgrades web image URLs (e.g. CinemaExpress/Assettype CDN parameters or Wikipedia thumbnails) to Full HD 1920p original images."""
    if not url or not isinstance(url, str):
        return url
    url_str = url.strip()
    if '/upload.wikimedia.org/' in url_str and '/thumb/' in url_str:
        url_str = re.sub(r'/thumb/(.+)/[^/]+$', r'/\1', url_str)
    if 'w=480' in url_str or 'w=300' in url_str or 'w=600' in url_str or 'w=350' in url_str or 'w=400' in url_str:
        url_str = re.sub(r'w=\d+', 'w=1920', url_str)
    return url_str


def clean_malayalam_initial_dots(text: str) -> str:
    """Removes dots from names, initials, acronyms, and abbreviations in Malayalam text while keeping sentence full stops."""
    if not text:
        return ""
    s = str(text)
    # 1. Remove dots between letters: e.g. എ.ഡി -> എഡി, എ.ഡിയെ -> എഡിയെ, K.G.F -> KGF
    s = re.sub(r'([\u0D00-\u0D7FA-Za-z])\.([\u0D00-\u0D7FA-Za-z])', r'\1\2', s)
    s = re.sub(r'([\u0D00-\u0D7FA-Za-z])\.([\u0D00-\u0D7FA-Za-z])', r'\1\2', s)
    # 2. Remove dots from initials with space: e.g. " എ. ഡി. " -> " എ ഡി "
    # Python re requires fixed-width lookbehind, so handle (?<=\s) and start of string ^ separately
    s = re.sub(r'(?<=\s)([\u0D00-\u0D7FA-Za-z]{1,2})\.\s*(?=[\u0D00-\u0D7FA-Za-z])', r'\1 ', s)
    s = re.sub(r'^([\u0D00-\u0D7FA-Za-z]{1,2})\.\s*(?=[\u0D00-\u0D7FA-Za-z])', r'\1 ', s)
    s = re.sub(r'(?<=\s)([\u0D00-\u0D7FA-Za-z]{1,2})\.(?=\s)', r'\1', s)
    s = re.sub(r'^([\u0D00-\u0D7FA-Za-z]{1,2})\.(?=\s)', r'\1', s)
    # 3. Clean up multiple spaces
    s = re.sub(r' +', ' ', s).strip()
    return s


def download_single_target(target_str: str, save_path: str) -> bool:
    """
    Downloads an image target URL into save_path with Full HD resolution upgrading.
    """
    target_clean = target_str.strip()
    if not target_clean or target_clean.lower() == 'nan':
        return False

    if target_clean.startswith(('http://', 'https://')):
        if 'google.com/imgres' in target_clean or 'imgurl=' in target_clean:
            parsed = urllib.parse.urlparse(target_clean)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'imgurl' in qs:
                target_clean = qs['imgurl'][0]

        target_clean = upgrade_url_to_hd(target_clean)

        try:
            r = requests.get(target_clean, headers=HTTP_HEADERS, verify=False, timeout=15)
            if r.status_code == 200:
                if _is_valid_image_bytes(r.content):
                    with open(save_path, 'wb') as f:
                        f.write(r.content)
                    return True
                else:
                    og_img = extract_og_image_from_html(r.text)
                    if og_img:
                        r_og = requests.get(og_img, headers=HTTP_HEADERS, verify=False, timeout=15)
                        if r_og.status_code == 200 and _is_valid_image_bytes(r_og.content):
                            with open(save_path, 'wb') as f:
                                f.write(r_og.content)
                            return True
        except Exception:
            pass

    return False


def get_filtered_sheet_order(sections_arg: str = "all") -> List[Dict[str, Any]]:
    """Filters SHEET_ORDER based on comma-separated section slugs or keywords."""
    if not sections_arg:
        return SHEET_ORDER

    sections_str = str(sections_arg).strip()
    if "#sections=" in sections_str:
        sections_str = sections_str.split("#sections=")[1].strip()
    if "__SECTIONS__:" in sections_str:
        m = re.search(r'__SECTIONS__:([a-zA-Z0-9_,]+)', sections_str)
        if m:
            sections_str = m.group(1).strip()

    if sections_str.lower() in ["all", "*", "", "all_sections", "all_3"]:
        return SHEET_ORDER

    raw_keys = [k.strip().lower().replace("-", "_").replace(" ", "_") for k in re.split(r'[,+\s]+', sections_str) if k.strip()]
    if any(k in ["all", "*", "all_sections", "all_3"] for k in raw_keys):
        return SHEET_ORDER

    filtered = []
    for s_cfg in SHEET_ORDER:
        slug = s_cfg["slug"].lower()
        name_slug = s_cfg["name"].lower().replace(" ", "_")

        matched = False
        for req in raw_keys:
            if req == slug or req == name_slug:
                matched = True
                break
            if req in ["movie", "movies", "movie_news"] and "movie" in slug:
                matched = True
                break
            if req in ["release", "releases", "theater", "theatre", "theater_releases", "theatre_releases"] and "release" in slug:
                matched = True
                break
            if req in ["ott", "otts", "ott_releases", "streaming"] and "ott" in slug:
                matched = True
                break

        if matched:
            filtered.append(s_cfg)

    if not filtered or len(filtered) == 3:
        return SHEET_ORDER

    return filtered


def fetch_all_sheets_data(sheet_url: str = DEFAULT_SHEET_URL, active_sheet_order: Optional[List[Dict[str, Any]]] = None) -> Tuple[Dict[str, List[Dict[str, Any]]], int, int, List[str]]:
    """
    Downloads multi-tab Google Spreadsheet (.xlsx) and parses topics for SHEET_ORDER sections.
    Strictly preserves sheet order and comma-separated image URLs per topic.
    """
    print("\n" + "=" * 60)
    print("MALAYALAM MOVIE NEWS VIDEO GENERATOR")
    print("=" * 60)
    print("\nLoading Google Spreadsheet...")

    if active_sheet_order is None:
        active_sheet_order = SHEET_ORDER

    xlsx_url = convert_sheet_url_to_xlsx_url(sheet_url)
    headers = HTTP_HEADERS.copy()
    resp = None

    for attempt in range(1, 4):
        try:
            resp = requests.get(xlsx_url, headers=headers, verify=False, timeout=25)
            if resp.status_code == 200:
                break
        except Exception as e:
            if attempt == 3:
                print(f"[!] Warning downloading XLSX workbook: {e}")
            time.sleep(1)

    sheets_dict = {}
    if resp and resp.status_code == 200:
        try:
            excel_bytes = io.BytesIO(resp.content)
            sheets_dict = pd.read_excel(excel_bytes, sheet_name=None)
        except Exception as e:
            print(f"[!] Warning reading Excel workbook bytes: {e}")

    # Fallback to CSV if pd.read_excel failed or returned empty
    if not sheets_dict:
        csv_url = convert_sheet_url_to_csv_url(sheet_url)
        r_csv = requests.get(csv_url, headers=headers, verify=False, timeout=20)
        if r_csv.status_code == 200:
            sheets_dict["Movie Updates"] = pd.read_csv(io.StringIO(r_csv.text))

    available_sheets = {str(k).strip().lower(): k for k in sheets_dict.keys()}

    parsed_sections = {}
    total_images_downloaded = 0
    total_images_failed = 0
    warning_logs = []

    for s_cfg in active_sheet_order:
        sec_name = s_cfg["name"]
        sec_slug = s_cfg["slug"]
        if sec_name.lower() in available_sheets:
            actual_tab_key = available_sheets[sec_name.lower()]
            df = sheets_dict[actual_tab_key]
        else:
            print(f"[!] Note: Tab '{sec_name}' not found in sheet workbook. Initializing empty section.")
            df = pd.DataFrame(columns=["Title", "Details", "Image_URL"])

        cols = [str(c).strip() for c in df.columns]
        if not cols:
            parsed_sections[sec_name] = []
            print(f"✓ {sec_name} loaded: 0 topics")
            continue

        # Column A (index 0) = Topic Number
        # Column B (index 1) = Topic Text
        # Column C (index 2) = Image URLs

        # 1. Topic Text Column: Default Column B (index 1)
        topic_col = cols[1] if len(cols) >= 2 else cols[0]
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['number', 'sl', 'no', 'id', 'num']):
                continue
            if c_low == 'topic' or 'news' in c_low or 'headline' in c_low or 'text' in c_low:
                topic_col = c
                break

        # 2. Image URLs Column: Default Column C (index 2)
        img_col = cols[2] if len(cols) >= 3 else (cols[1] if len(cols) >= 2 else None)
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['image', 'url', 'people', 'person', 'link', 'photo', 'unnamed: 2']):
                img_col = c
                break

        headline_col = None
        if len(cols) >= 4:
            headline_col = cols[3]
        for c in cols:
            c_low = c.lower()
            if 'headline' in c_low or 'title' in c_low or 'col d' in c_low or 'column d' in c_low:
                headline_col = c
                break

        rel_date_col = None
        if len(cols) >= 5:
            rel_date_col = cols[4]
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['release', 'streaming', 'date', 'col e', 'column e']):
                rel_date_col = c
                break

        ott_plat_col = None
        if len(cols) >= 6:
            ott_plat_col = cols[5]
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['ott', 'platform', 'col f', 'column f']):
                ott_plat_col = c
                break

        topics_data = []
        valid_topic_idx = 0

        from preprocessing.pronunciation_dictionary import PronunciationDictionary
        pron_dict = PronunciationDictionary()

        for row_idx, (df_idx, row) in enumerate(df.iterrows(), start=2): # 1-based header row
            topic_val = str(row[topic_col]).strip() if pd.notna(row[topic_col]) else ""
            img_val = str(row[img_col]).strip() if img_col and pd.notna(row[img_col]) else ""
            headline_val = str(row[headline_col]).strip() if headline_col and pd.notna(row[headline_col]) else ""
            rel_date_val = str(row[rel_date_col]).strip() if rel_date_col and pd.notna(row[rel_date_col]) else ""
            ott_plat_val = str(row[ott_plat_col]).strip() if ott_plat_col and pd.notna(row[ott_plat_col]) else ""

            if headline_val.lower() == "nan": headline_val = ""
            if rel_date_val.lower() == "nan": rel_date_val = ""
            if ott_plat_val.lower() == "nan": ott_plat_val = ""

            if not topic_val or topic_val.lower() == "nan":
                w_log = f"[WARNING] {sec_name} - Row {row_idx} skipped: Topic is empty"
                warning_logs.append(w_log)
                print(f"  {w_log}")
                continue

            # Convert any English words/acronyms in Google Sheet topic text into clean Malayalam script
            topic_val = pron_dict.replace_english_words(topic_val)
            # Remove dots from names, initials, and acronyms (keeps sentence full stops)
            topic_val = clean_malayalam_initial_dots(topic_val)

            valid_topic_idx += 1

            # Isolated per-topic image directory: outputs/topic_images/{sec_slug}/topic_{valid_topic_idx:02d}
            topic_dir = IMAGES_DIR / sec_slug / f"topic_{valid_topic_idx:02d}"
            topic_dir.mkdir(parents=True, exist_ok=True)

            # Comma-separated URL parser
            image_urls = [u.strip() for u in re.split(r'[\r\n,]+', img_val) if u.strip() and u.strip().lower() != 'nan']

            downloaded_paths = []
            for u_idx, url_str in enumerate(image_urls, start=1):
                save_path = str(topic_dir / f"image_{u_idx:02d}.jpg")
                if download_single_target(url_str, save_path):
                    downloaded_paths.append(save_path)
                    total_images_downloaded += 1
                else:
                    total_images_failed += 1
                    w_msg = f"[WARNING] {sec_name} Topic {valid_topic_idx} Image {u_idx} failed to download"
                    warning_logs.append(w_msg)

            topics_data.append({
                "section": sec_name,
                "section_slug": sec_slug,
                "topic_number": valid_topic_idx,
                "source_row": row_idx,
                "topic_text": topic_val,
                "topic_headline": headline_val,
                "release_date": rel_date_val,
                "ott_platform": ott_plat_val,
                "image_urls": image_urls,
                "image_paths": downloaded_paths,
                "movie_poster_path": downloaded_paths[0] if downloaded_paths else None,
                "actor_photo_paths": downloaded_paths[1:] if len(downloaded_paths) > 1 else downloaded_paths
            })

        parsed_sections[sec_name] = topics_data
        print(f"✓ {sec_name} loaded: {len(topics_data)} topics")

    return parsed_sections, total_images_downloaded, total_images_failed, warning_logs


def get_ordinal_prefix(idx: int) -> str:
    """Returns Malayalam ordinal transition text for topic index."""
    ordinals = {
        1: "ഒന്നാമതായി...",
        2: "രണ്ടാമതായി...",
        3: "മൂന്നാമതായി...",
        4: "നാലാമതായി...",
        5: "അഞ്ചാമതായി...",
        6: "ആറാമതായി...",
        7: "ഏഴാമതായി...",
        8: "എട്ടാമതായി...",
        9: "ഒമ്പതാമതായി...",
        10: "പത്താമതായി...",
        11: "പതിനൊന്നാമതായി...",
        12: "പന്ത്രണ്ടാമതായി...",
        13: "പതിമൂന്നാമതായി...",
        14: "പതിനാലാമതായി...",
        15: "പതിനഞ്ചാമതായി..."
    }
    return ordinals.get(idx, f"{idx}-ാമതായി...")


def build_presenter_markup_script(parsed_sections: Dict[str, List[Dict[str, Any]]], active_sheet_order: Optional[List[Dict[str, Any]]] = None) -> str:
    """Wraps multi-sheet sections into Presenter XML Markup script with global intro/outro and section intros."""
    if active_sheet_order is None:
        active_sheet_order = SHEET_ORDER

    markup_parts = []

    # 1. Global Intro (Occurs ONCE at beginning)
    markup_parts.append("<intro>")
    markup_parts.append(GLOBAL_INTRO)
    markup_parts.append("</intro>\n")

    # Find non-empty sections
    active_non_empty = [s for s in active_sheet_order if parsed_sections.get(s["name"], [])]

    # 2. Sequential Sections
    for idx, s_cfg in enumerate(active_non_empty):
        sec_name = s_cfg["name"]
        sec_slug = s_cfg.get("slug", "")
        topics = parsed_sections.get(sec_name, [])

        if not topics:
            continue

        # Choose natural intro phrasing depending on whether this is the first section or a follow-up
        if idx == 0:
            if sec_slug == "release_updates":
                sec_intro = "പുതിയ തിയേറ്റർ റിലീസ് വിശേഷങ്ങളിലേക്ക്."
            elif sec_slug == "ott_updates":
                sec_intro = "പുതിയ ഒടിടി റിലീസുകളുടെയും സ്ട്രീമിംഗ് വിശേഷങ്ങളിലേക്ക്."
            elif sec_slug == "movie_updates":
                sec_intro = s_cfg.get("intro", "ആദ്യം, പുതിയ സിനിമാ അപ്ഡേറ്റുകളിലേക്ക്.")
            else:
                sec_intro = s_cfg.get("intro", "")
        else:
            if sec_slug == "release_updates":
                sec_intro = "ഇനി അടുത്തതായി, റിലീസിന് ഒരുങ്ങുന്ന സിനിമകളുടെ അപ്ഡേറ്റുകളിലേക്ക്."
            elif sec_slug == "ott_updates":
                sec_intro = "ഇനി അടുത്തതായി, ഒടിടി റിലീസുകളുടെയും സ്ട്രീമിംഗ് അപ്ഡേറ്റുകളുടെയും വിശേഷങ്ങളിലേക്ക്."
            elif sec_slug == "movie_updates":
                sec_intro = "ഇനി അടുത്തതായി, പുതിയ സിനിമാ അപ്ഡേറ്റുകളിലേക്ക്."
            else:
                sec_intro = s_cfg.get("intro", "")

        markup_parts.append("<section_intro>")
        markup_parts.append(sec_intro)
        markup_parts.append("</section_intro>\n")

        for item in topics:
            topic = item["topic_text"]
            ordinal = get_ordinal_prefix(item["topic_number"])

            if ";" in topic:
                parts = topic.split(";", 1)
                headline_text = parts[0].strip()
                detail_text = parts[1].strip()
            else:
                # If no semicolon, split at the first sentence boundary so headline is punchy and detail follows smoothly
                first_period = re.search(r'([\.\?!])\s+', topic)
                if first_period and first_period.end() < len(topic) - 10:
                    split_idx = first_period.end()
                    headline_text = topic[:split_idx].strip()
                    detail_text = topic[split_idx:].strip()
                else:
                    headline_text = topic
                    detail_text = ""

            markup_parts.append(f"<headline>\n{ordinal} {headline_text}\n</headline>\n")
            if detail_text:
                markup_parts.append(f"<detail>\n{detail_text}\n</detail>\n")

    # 3. Global Outro (Occurs ONCE at end)
    markup_parts.append("<outro>")
    markup_parts.append(GLOBAL_OUTRO)
    markup_parts.append("</outro>")

    return "\n".join(markup_parts)


def generate_audio_from_sheet(sheet_url: str = DEFAULT_SHEET_URL, model_key: str = "edge_female", is_test_mode: bool = False, sections_arg: str = "all"):
    """Main workflow function to fetch multi-sheet topics, download images, and generate audio."""
    active_sheet_order = get_filtered_sheet_order(sections_arg)
    print(f"[SECTIONS] Active rendering sections: {[s['name'] for s in active_sheet_order]}")

    parsed_sections, img_downloaded, img_failed, warning_logs = fetch_all_sheets_data(sheet_url, active_sheet_order=active_sheet_order)

    active_test_mode = is_test_mode or TEST_MODE or ("--test" in sys.argv or "-t" in sys.argv)
    if active_test_mode:
        print("\n[!] TEST_MODE Active: Filtering to 1 topic per non-empty worksheet...")
        for sec_name in parsed_sections:
            if parsed_sections[sec_name]:
                parsed_sections[sec_name] = parsed_sections[sec_name][:1]

    # Combine all topic items in order for metadata JSON
    all_flat_topics = []
    for s_cfg in active_sheet_order:
        all_flat_topics.extend(parsed_sections.get(s_cfg["name"], []))

    if not all_flat_topics:
        print("[!] No topics found across all active worksheets.")
        return None

    markup_script = build_presenter_markup_script(parsed_sections, active_sheet_order=active_sheet_order)

    print("\n--------------------------------------------------")
    print("INTRO & SCRIPT GENERATED")
    print("--------------------------------------------------")
    print(markup_script[:400] + "\n... [truncated] ...\n")
    sys.stdout.flush()

    engine = MalayalamVoiceEngine(default_model_key=model_key)
    output_filename = f"GoogleSheet_Malayalam_Movie_News_{model_key}_v4.0.wav"
    output_path = str(OUTPUT_DIR / output_filename)

    res = engine.generate_from_markup(
        markup_text=markup_script,
        output_filepath=output_path,
        output_format="wav"
    )

    duration_sec = round(len(res["waveform"]) / DEFAULT_SAMPLE_RATE, 2)

    # Attach all topic items metadata
    res["topic_items"] = all_flat_topics
    res["parsed_sections"] = parsed_sections
    if "metadata_path" in res and os.path.exists(res["metadata_path"]):
        import json
        try:
            with open(res["metadata_path"], 'r', encoding='utf-8') as f:
                meta_data = json.load(f)
            meta_data["topic_items"] = all_flat_topics
            meta_data["parsed_sections"] = {k: len(v) for k, v in parsed_sections.items()}
            meta_data["selected_sections"] = [s["slug"] for s in active_sheet_order]
            meta_data["active_sections"] = [s["name"] for s in active_sheet_order]
            with open(res["metadata_path"], 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"[!] Warning updating metadata JSON: {e}")

    # Generate Final Report Card
    print("\n" + "=" * 50)
    print("FINAL REPORT")
    print("=" * 50)
    total_topics_count = 0
    total_completed = 0
    total_failed = 0

    for s_cfg in active_sheet_order:
        s_name = s_cfg["name"]
        t_list = parsed_sections.get(s_name, [])
        t_count = len(t_list)
        total_topics_count += t_count
        comp = sum(1 for t in t_list if len(t["image_paths"]) > 0 or len(t["image_urls"]) == 0)
        fail = t_count - comp
        total_completed += comp
        total_failed += fail

        print(f"{s_name}:")
        print(f"    Topics: {t_count}")
        print(f"    Completed: {comp}")
        print(f"    Failed: {fail}\n")

    print("Images:")
    print(f"    Downloaded: {img_downloaded}")
    print(f"    Failed: {img_failed}\n")

    print("Final video:")
    print(f"    Generated with {total_topics_count} topics")

    if warning_logs:
        print("\nWarnings:")
        for w in warning_logs:
            print(f"    {w}")
    print("=" * 50)

    return res['audio_path']


if __name__ == "__main__":
    url_arg = DEFAULT_SHEET_URL
    model_arg = "edge_female"
    is_test = False
    sections_arg = os.environ.get("SECTIONS", "all")

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("http://") or arg.startswith("https://"):
            url_arg = arg
        elif arg in ["--test", "-t"]:
            is_test = True
        elif arg in ["--sections", "-s", "--section"]:
            if i + 1 < len(args):
                sections_arg = args[i + 1]
                i += 1
        elif arg.startswith("--sections="):
            sections_arg = arg.split("=", 1)[1]
        elif not arg.startswith("-"):
            model_arg = arg
        i += 1

    generate_audio_from_sheet(sheet_url=url_arg, model_key=model_arg, is_test_mode=is_test, sections_arg=sections_arg)
