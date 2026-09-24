"""
Google Sheet Manager Module
Handles downloading, parsing, editing, bulk tab pasting, local caching,
and syncing live Google Spreadsheet tabs (Movie Updates, Release Updates, OTT Updates).
"""

import os
import re
import io
import json
import time
import datetime
import urllib.parse
import requests
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


def format_cell_value(val: Any) -> str:
    """Formats a cell value into a clean, JSON-serializable string, handling Timestamps, datetimes, and NaNs."""
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, (pd.Timestamp, datetime.datetime)):
        if val.hour == 0 and val.minute == 0 and val.second == 0:
            return val.strftime("%Y-%m-%d")
        return val.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(val, datetime.date):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def json_serial_fallback(obj: Any) -> Any:
    """Fallback JSON serializer for Timestamps, datetimes, dates, NaNs, and custom types."""
    if obj is None or pd.isna(obj):
        return ""
    if isinstance(obj, (pd.Timestamp, datetime.datetime)):
        if obj.hour == 0 and obj.minute == 0 and obj.second == 0:
            return obj.strftime("%Y-%m-%d")
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(obj, datetime.date):
        return obj.strftime("%Y-%m-%d")
    return str(obj)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
CACHE_FILE = OUTPUT_DIR / "sheet_cache.json"
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/15xkauNiB27ytehTI5XHgmLm5QmJvudnEegrGSmnx5_g/edit?gid=183267360#gid=183267360"
DEFAULT_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyKFgRsYYCX69wM7_INBD7kWWUc3O9ah-HrPOjXf_Z_rigXZwWzt5qVWPMPiNE6PQ-nWQ/exec"

SHEET_CONFIGS = [
    {"name": "Movie Updates", "slug": "movie_updates", "gid": "183267360"},
    {"name": "Release Updates", "slug": "release_updates", "gid": "0"},
    {"name": "OTT Updates", "slug": "ott_updates", "gid": "1"}
]

STANDARD_COLUMNS = ["Topic Number", "Malayalam News Text", "Image URLs"]


class GoogleSheetManager:
    def __init__(self, sheet_url: str = DEFAULT_SHEET_URL, web_app_url: Optional[str] = DEFAULT_WEB_APP_URL):
        self.sheet_url = sheet_url
        self.web_app_url = web_app_url or DEFAULT_WEB_APP_URL
        self.data_cache: Dict[str, pd.DataFrame] = {}

    def get_document_id(self) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', self.sheet_url)
        return match.group(1) if match else "15xkauNiB27ytehTI5XHgmLm5QmJvudnEegrGSmnx5_g"

    def get_export_xlsx_url(self) -> str:
        doc_id = self.get_document_id()
        return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=xlsx"

    def get_export_csv_url(self, gid: str = "0") -> str:
        doc_id = self.get_document_id()
        return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"

    def fetch_all_tabs(self, force_refresh: bool = False) -> Dict[str, pd.DataFrame]:
        """
        Fetches data for all 3 tabs: Movie Updates, Release Updates, OTT Updates.
        Uses local JSON cache if available unless force_refresh is True.
        """
        if not force_refresh and self.data_cache:
            return self.data_cache

        # Try loading local cache file first if available and not forcing refresh
        if not force_refresh and CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache_json = json.load(f)
                loaded_cache = {}
                for tab_k, tab_rows in cache_json.items():
                    if isinstance(tab_rows, list):
                        loaded_cache[tab_k] = pd.DataFrame(tab_rows)
                if all(cfg["name"] in loaded_cache for cfg in SHEET_CONFIGS):
                    self.data_cache = loaded_cache
                    return self.data_cache
            except Exception as e:
                print(f"[!] Warning reading local cache: {e}")

        # Fetch live online XLSX workbook from Google Sheet
        xlsx_url = self.get_export_xlsx_url()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        sheets_raw = {}
        try:
            r = requests.get(xlsx_url, headers=headers, verify=False, timeout=20)
            if r.status_code == 200:
                excel_bytes = io.BytesIO(r.content)
                sheets_raw = pd.read_excel(excel_bytes, sheet_name=None)
        except Exception as e:
            print(f"[!] Warning downloading XLSX workbook: {e}")

        parsed_tabs = {}
        avail_lower = {str(k).strip().lower(): k for k in sheets_raw.keys()}

        for cfg in SHEET_CONFIGS:
            name = cfg["name"]
            df_tab = None

            if name.lower() in avail_lower:
                actual_key = avail_lower[name.lower()]
                raw_df = sheets_raw[actual_key]
                df_tab = self.normalize_dataframe(raw_df)

            if df_tab is None or df_tab.empty:
                # Fallback to CSV export for that tab
                csv_url = self.get_export_csv_url(cfg["gid"])
                try:
                    r_csv = requests.get(csv_url, headers=headers, verify=False, timeout=15)
                    if r_csv.status_code == 200:
                        raw_df = pd.read_csv(io.StringIO(r_csv.text))
                        df_tab = self.normalize_dataframe(raw_df)
                except Exception:
                    pass

            if df_tab is None or df_tab.empty:
                # Default empty structure
                df_tab = pd.DataFrame(columns=STANDARD_COLUMNS)

            parsed_tabs[name] = df_tab

        # Preserve any additional worksheets like 'Thumbnail Config', 'Serper Keys', etc.
        for sheet_key in sheets_raw.keys():
            key_clean = str(sheet_key).strip()
            if key_clean not in parsed_tabs:
                extra_df = sheets_raw[sheet_key]
                if isinstance(extra_df, pd.DataFrame):
                    extra_clean = extra_df.copy()
                    extra_clean.columns = [str(c).strip() for c in extra_clean.columns]
                    for c in extra_clean.columns:
                        extra_clean[c] = extra_clean[c].apply(format_cell_value)
                    parsed_tabs[key_clean] = extra_clean
                else:
                    parsed_tabs[key_clean] = extra_df

        self.data_cache = parsed_tabs
        self.save_local_cache()
        return self.data_cache

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes DataFrame columns: Topic Number, Malayalam News Text, Image URLs, Topic Headline, Release Date, OTT Platform."""
        if df.empty:
            return pd.DataFrame(columns=["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date", "OTT Platform"])

        cols = [str(c).strip() for c in df.columns]
        
        # Identify Topic Text col (usually index 1)
        topic_col = cols[1] if len(cols) >= 2 else cols[0]
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['number', 'sl', 'no', 'id', 'num']):
                continue
            if c_low == 'topic' or 'news' in c_low or 'text' in c_low:
                topic_col = c
                break

        # Identify Image URL col (usually index 2)
        img_col = cols[2] if len(cols) >= 3 else (cols[1] if len(cols) >= 2 else None)
        for c in cols:
            c_low = c.lower()
            if any(k in c_low for k in ['image', 'url', 'people', 'person', 'link', 'photo', 'unnamed: 2']):
                img_col = c
                break

        # Identify Headline / Title col (Column D or index 3 if available)
        headline_col = cols[3] if len(cols) >= 4 else None
        for c in cols:
            c_low = c.lower()
            if 'headline' in c_low or 'title' in c_low or 'movie' in c_low or 'col d' in c_low:
                headline_col = c
                break

        # Identify Release Date col (Column E or index 4 if available)
        rel_date_col = cols[4] if len(cols) >= 5 else None
        for c in cols:
            c_low = c.lower()
            if 'release date' in c_low or 'streaming date' in c_low or 'col e' in c_low:
                rel_date_col = c
                break

        # Identify OTT Platform col (Column F or index 5 if available)
        ott_plat_col = cols[5] if len(cols) >= 6 else None
        for c in cols:
            c_low = c.lower()
            if 'ott' in c_low or 'platform' in c_low or 'col f' in c_low:
                ott_plat_col = c
                break

        clean_rows = []
        for idx, (df_idx, row) in enumerate(df.iterrows(), start=1):
            text_val = format_cell_value(row[topic_col]) if topic_col and topic_col in row else ""
            img_val = format_cell_value(row[img_col]) if img_col and img_col in row else ""
            headline_val = format_cell_value(row[headline_col]) if headline_col and headline_col in row else ""
            rel_date_val = format_cell_value(row[rel_date_col]) if rel_date_col and rel_date_col in row else ""
            ott_plat_val = format_cell_value(row[ott_plat_col]) if ott_plat_col and ott_plat_col in row else ""
            
            if not text_val or text_val.lower() == "nan":
                continue
            if img_val.lower() == "nan": img_val = ""
            if headline_val.lower() == "nan": headline_val = ""
            if rel_date_val.lower() == "nan": rel_date_val = ""
            if ott_plat_val.lower() == "nan": ott_plat_val = ""

            clean_rows.append({
                "Topic Number": str(idx),
                "Malayalam News Text": text_val,
                "Image URLs": img_val,
                "Topic Headline": headline_val,
                "Release Date": rel_date_val,
                "OTT Platform": ott_plat_val
            })

        return pd.DataFrame(clean_rows, columns=["Topic Number", "Malayalam News Text", "Image URLs", "Topic Headline", "Release Date", "OTT Platform"])

    def parse_pasted_table(self, pasted_text: str) -> pd.DataFrame:
        """
        Parses multi-row tab-separated (TSV) or comma-separated (CSV) pasted table string
        from Excel / Google Sheets into a clean DataFrame.
        """
        clean_text = pasted_text.strip()
        if not clean_text:
            return pd.DataFrame(columns=STANDARD_COLUMNS)

        # Detect separator (tab vs comma vs pipe)
        lines = [line for line in clean_text.splitlines() if line.strip()]
        if not lines:
            return pd.DataFrame(columns=STANDARD_COLUMNS)

        first_line = lines[0]
        sep = '\t' if '\t' in first_line else (',' if ',' in first_line else None)

        try:
            if sep:
                df_raw = pd.read_csv(io.StringIO(clean_text), sep=sep, header=None)
            else:
                df_raw = pd.DataFrame(lines, columns=[0])
        except Exception:
            # Simple line splitter fallback
            rows = []
            for line in lines:
                parts = line.split('\t') if '\t' in line else line.split(',')
                rows.append([p.strip() for p in parts])
            df_raw = pd.DataFrame(rows)

        # Convert raw parsed grid into standard 3 columns
        num_cols = df_raw.shape[1]
        clean_rows = []

        # Check if row 0 looks like header
        start_row = 0
        r0_str = " ".join([str(x).lower() for x in df_raw.iloc[0].values])
        if any(k in r0_str for k in ['topic', 'news', 'text', 'image', 'url', 'sl', 'no', 'headline']):
            start_row = 1

        valid_idx = 1
        for row_i in range(start_row, len(df_raw)):
            row = df_raw.iloc[row_i]
            if num_cols == 1:
                t_num = str(valid_idx)
                text_val = str(row[0]).strip()
                img_val = ""
            elif num_cols == 2:
                t_num = str(valid_idx)
                text_val = str(row[0]).strip()
                img_val = str(row[1]).strip()
            else:
                t_num = str(row[0]).strip() if str(row[0]).strip().isdigit() else str(valid_idx)
                text_val = str(row[1]).strip()
                img_val = str(row[2]).strip() if pd.notna(row[2]) else ""

            if not text_val or text_val.lower() in ["nan", "none"]:
                continue
            if img_val.lower() in ["nan", "none"]:
                img_val = ""

            clean_rows.append({
                "Topic Number": str(valid_idx),
                "Malayalam News Text": text_val,
                "Image URLs": img_val
            })
            valid_idx += 1

        return pd.DataFrame(clean_rows, columns=STANDARD_COLUMNS)

    def update_tab_data(self, tab_name: str, new_df: pd.DataFrame) -> bool:
        """Updates internal cache for a specific sheet tab and persists locally & remotely."""
        clean_df = self.normalize_dataframe(new_df)
        self.data_cache[tab_name] = clean_df
        self.save_local_cache()

        # If Apps Script Web App URL is configured, push update directly to Google Sheet online
        if self.web_app_url:
            return self.sync_to_google_apps_script(tab_name, clean_df)

        return True

    def save_local_cache(self):
        """Saves current data_cache to JSON file on disk."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {}
        for tab_name, df in self.data_cache.items():
            if isinstance(df, pd.DataFrame):
                records = []
                for row_dict in df.to_dict(orient="records"):
                    clean_dict = {
                        str(k): format_cell_value(v) if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)) or pd.isna(v) else v
                        for k, v in row_dict.items()
                    }
                    records.append(clean_dict)
                cache_data[tab_name] = records
            elif isinstance(df, list):
                cache_data[tab_name] = df
            else:
                cache_data[tab_name] = []

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2, default=json_serial_fallback)

    def sync_to_google_apps_script(self, tab_name: str, df: pd.DataFrame) -> bool:
        """Pushes table updates to Google Sheet using a Google Apps Script Web App webhook."""
        if not self.web_app_url:
            return False

        if isinstance(df, pd.DataFrame):
            records = []
            for row_dict in df.to_dict(orient="records"):
                clean_dict = {
                    str(k): format_cell_value(v) if isinstance(v, (pd.Timestamp, datetime.datetime, datetime.date)) or pd.isna(v) else v
                    for k, v in row_dict.items()
                }
                records.append(clean_dict)
        elif isinstance(df, list):
            records = df
        else:
            records = []

        payload = {
            "tab_name": tab_name,
            "rows": records
        }

        try:
            headers = {"Content-Type": "application/json"}
            r = requests.post(self.web_app_url, data=json.dumps(payload, default=json_serial_fallback), headers=headers, verify=False, timeout=20, allow_redirects=True)
            print(f"[SUCCESS] WebApp Sync Response Code: {r.status_code}")
            return r.status_code in [200, 302]
        except Exception as e:
            print(f"[!] WebApp Sync Error: {e}")
            return False

    def export_as_excel_bytes(self) -> bytes:
        """Exports all 3 tabs into an Excel workbook file in-memory."""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for tab_name, df in self.data_cache.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        output.seek(0)
        return output.getvalue()

    def get_groq_api_key(self) -> str:
        """Reads GROQ_API_KEY from Google Sheet 'Config' worksheet tab or environment."""
        if not self.web_app_url:
            return os.getenv("GROQ_API_KEY", "")

        try:
            r = requests.get(f"{self.web_app_url}?action=get_data", verify=False, timeout=10)
            if r.status_code == 200:
                data = r.json()
                config = data.get("config", {})
                if config.get("groq_api_key"):
                    return config["groq_api_key"]
                
                # Check Config sheet directly if present in JSON
                config_rows = data.get("Config") or data.get("Settings") or []
                for row in config_rows:
                    kname = str(row.get("Key Name", "")).strip().lower()
                    kval = str(row.get("Key Value", "")).strip()
                    if "groq" in kname and kval:
                        return kval
        except Exception as e:
            print(f"[!] Warning reading Groq key from Config sheet: {e}")

        return os.getenv("GROQ_API_KEY", "")

    def get_gemini_api_key(self) -> str:
        """Reads GEMINI_API_KEY from Google Sheet 'Config' worksheet tab or environment."""
        if not self.web_app_url:
            return os.getenv("GEMINI_API_KEY", "")

        try:
            r = requests.get(f"{self.web_app_url}?action=get_data", verify=False, timeout=10)
            if r.status_code == 200:
                data = r.json()
                config = data.get("config", {})
                if config.get("gemini_api_key"):
                    return config["gemini_api_key"]
                
                # Check Config sheet directly if present in JSON
                config_rows = data.get("Config") or data.get("Settings") or []
                for row in config_rows:
                    kname = str(row.get("Key Name", "")).strip().lower()
                    kval = str(row.get("Key Value", "")).strip()
                    if "gemini" in kname and kval:
                        return kval
        except Exception as e:
            print(f"[!] Warning reading Gemini key from Config sheet: {e}")

        return os.getenv("GEMINI_API_KEY", "")

    def log_upload_to_google_sheet(
        self,
        title: str,
        video_url: str,
        privacy_status: str,
        chapters: str,
        description: str,
        tags: Any
    ) -> bool:
        """Logs video upload details, YouTube URL, chapters, and metadata to Google Sheets 'Video Uploads' tab and local history."""
        tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        payload = {
            "action": "log_video_metadata",
            "title": title,
            "video_url": video_url,
            "privacy_status": privacy_status,
            "chapters": chapters,
            "description": description,
            "tags": tags_str
        }

        # 1. Append locally to outputs/upload_history.json
        try:
            history_file = OUTPUT_DIR / "upload_history.json"
            history = []
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                **payload
            })
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            print(f"[✓] Saved upload record to local {history_file.name}")
        except Exception as e:
            print(f"[!] Warning writing local upload history: {e}")

        # 2. Sync to Google Sheet Web App
        if not self.web_app_url:
            return False

        try:
            r = requests.post(
                self.web_app_url,
                data=json.dumps(payload),
                headers={"Content-Type": "text/plain;charset=utf-8"},
                timeout=15,
                verify=False
            )
            if r.status_code == 200:
                print(f"[✓] Successfully logged video upload metadata to Google Sheets 'Video Uploads' tab!")
                return True
            else:
                print(f"[!] Note: Google Sheet Web App returned {r.status_code} on log_video_metadata")
        except Exception as e:
            print(f"[!] Warning logging upload to Google Sheet Web App: {e}")

        return False
