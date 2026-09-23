"""
YouTube Video Uploader Module
Implements Google YouTube Data API v3 Resumable Chunked Video Upload,
OAuth 2.0 Token Persistence, and Automated Custom Thumbnail Attachment.
"""

import os
import ssl
import urllib3
urllib3.disable_warnings()

# Disable SSL verification for token refresh if local cert store is missing certificates
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'

import requests
_orig_send = requests.Session.send
def _unverified_send(self, request, **kwargs):
    kwargs['verify'] = False
    return _orig_send(self, request, **kwargs)
requests.Session.send = _unverified_send

from pathlib import Path
from typing import Dict, Any, List, Optional

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
TOKEN_FILE = OUTPUT_DIR / "youtube_token.json"
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    def __init__(self, client_secrets_file: Optional[str] = None, token_file: Optional[str] = None):
        self.client_secrets_file = Path(client_secrets_file) if client_secrets_file else CLIENT_SECRET_FILE
        self.token_file = Path(token_file) if token_file else TOKEN_FILE

    def get_authenticated_service(self):
        """Authenticates with YouTube Data API v3 using OAuth 2.0 and returns service instance."""
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        creds = None

        # Load existing token credentials if available
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
            except Exception as e:
                print(f"[!] Warning loading token file: {e}")

        # Refresh or prompt new OAuth login if credentials expired or missing
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("[OK] Successfully refreshed YouTube OAuth access token.")
                except Exception as refresh_err:
                    print(f"[!] Warning: Failed to refresh YouTube OAuth token: {refresh_err}")
                    creds = None

            if not creds:
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"YouTube OAuth authentication failed: No valid token available and client_secret.json not found at: {self.client_secrets_file}\n"
                        f"If running in GitHub Actions, your 'YOUTUBE_TOKEN_JSON' repository secret is either expired, missing, or invalid.\n"
                        f"Note: Google expires refresh tokens after 7 days if your Google Cloud project is in 'Testing' mode.\n"
                        f"Please generate a fresh token using 'python get_youtube_token.py' and update the YOUTUBE_TOKEN_JSON secret in your GitHub repository settings."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(str(self.client_secrets_file), SCOPES)
                creds = flow.run_local_server(port=8080, prompt='consent')

            # Save token for future automatic uploads
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        return build("youtube", "v3", credentials=creds)

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        category_id: str = "24",  # 24 = Entertainment
        privacy_status: str = "unlisted",  # private, unlisted, public
        thumbnail_path: Optional[str] = None,
        chapters: Optional[str] = None,
        sheet_mgr: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Uploads an MP4 video file to YouTube via resumable chunked upload.
        Sets thumbnail if thumbnail_path is provided.
        Returns dict with video_id and video_url.
        """
        from googleapiclient.http import MediaFileUpload

        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video file to upload not found: {video_path}")

        youtube = self.get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube title limit 100 chars
                "description": description[:5000],  # Description limit 5000 chars
                "tags": tags or ["Malayalam Movie News", "Mollywood"],
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status.lower(),
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024 * 5,  # 5MB chunks
            resumable=True,
            mimetype="video/mp4"
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        print(f"\n[🚀] Initiating YouTube Video Upload: {title}...")
        response = None
        try:
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"  - Upload Progress: {progress}%")
        except Exception as e:
            err_str = str(e)
            if "uploadLimitExceeded" in err_str or "exceeded the number of videos" in err_str:
                print("\n" + "!" * 75)
                print("⚠️ YOUTUBE DAILY UPLOAD LIMIT REACHED (uploadLimitExceeded)")
                print("YouTube enforces a 24-hour limit on the number of videos a channel can upload.")
                print("Your channel has reached YouTube's maximum daily upload limit for today.")
                print("👉 Solution: Please wait 24 hours for YouTube's daily quota to reset.")
                print("!" * 75 + "\n")
                return {
                    "status": "limit_exceeded",
                    "error": "Daily YouTube video upload limit reached for this channel. Resets in 24 hours."
                }
            raise e

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        print(f"[✓] Video Upload Complete! Video ID: {video_id} | URL: {video_url}")

        # Set custom thumbnail if provided
        thumbnail_uploaded = False
        if thumbnail_path and Path(thumbnail_path).exists() and video_id:
            import time
            print(f"[THUMBNAIL] Uploading Custom Thumbnail: {thumbnail_path}...")
            thumb_media = MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg")

            max_thumb_attempts = 5
            for attempt in range(1, max_thumb_attempts + 1):
                try:
                    initial_delay = 3 if attempt == 1 else (attempt * 3)
                    print(f"[THUMBNAIL] Waiting {initial_delay}s for YouTube video registration before setting thumbnail (attempt {attempt}/{max_thumb_attempts})...")
                    time.sleep(initial_delay)
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=thumb_media
                    ).execute()
                    thumbnail_uploaded = True
                    print(f"[✓] Custom Thumbnail Applied Successfully on attempt {attempt}!")
                    break
                except Exception as e:
                    err_str = str(e)
                    print(f"[!] Warning: Thumbnail upload attempt {attempt}/{max_thumb_attempts} failed: {err_str}")
                    if "uploadRateLimitExceeded" in err_str or "429" in err_str:
                        if attempt < max_thumb_attempts:
                            rate_sleep = attempt * 15
                            print(f"[THUMBNAIL] ⏳ YouTube Thumbnail Rate Limit (429 / uploadRateLimitExceeded) hit. Backing off {rate_sleep}s before retry...")
                            time.sleep(rate_sleep)
                    elif "403" in err_str and "uploadRateLimitExceeded" not in err_str:
                        if attempt == max_thumb_attempts:
                            print("[!] Notice: If YouTube returned 403 Forbidden, please ensure your YouTube channel has 'Intermediate Features' (phone verification) enabled in YouTube Studio Settings > Channel > Feature Eligibility.")

        # Log to Google Sheets ('Video Uploads' tab) and local outputs/upload_history.json
        try:
            import re
            from google_sheet_manager import GoogleSheetManager
            from metadata_generator import generate_youtube_chapters

            actual_chapters = (chapters or "").strip()
            if not actual_chapters:
                try:
                    actual_chapters = generate_youtube_chapters()
                except Exception:
                    actual_chapters = ""
            if not actual_chapters and "CHAPTERS:" in description:
                try:
                    c_part = description.split("CHAPTERS:")[1]
                    if "=" * 10 in c_part:
                        c_part = c_part.split("=" * 10)[0]
                    actual_chapters = c_part.strip()
                except Exception:
                    pass
            elif not actual_chapters and "0:00" in description:
                c_lines = [l.strip() for l in description.splitlines() if re.match(r'^\d{1,2}:\d{2}', l.strip())]
                if c_lines:
                    actual_chapters = "\n".join(c_lines)

            target_mgr = sheet_mgr or GoogleSheetManager()
            target_mgr.log_upload_to_google_sheet(
                title=title,
                video_url=video_url,
                privacy_status=privacy_status,
                chapters=actual_chapters,
                description=description,
                tags=tags or []
            )
        except Exception as log_err:
            print(f"[!] Warning: Failed to log upload to Google Sheet: {log_err}")

        return {
            "status": "success",
            "video_id": video_id,
            "video_url": video_url,
            "privacy_status": privacy_status,
            "thumbnail_uploaded": thumbnail_uploaded,
            "title": title
        }
