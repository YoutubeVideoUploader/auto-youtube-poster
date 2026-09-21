"""
One-Time YouTube OAuth Authentication Helper
Prints the exact Google Login URL for the user to click.
"""

import sys
import json
import os
import ssl
from pathlib import Path

# Disable SSL verification for token exchange if local cert store is missing certificates
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import urllib3
urllib3.disable_warnings()

import requests
_orig_send = requests.Session.send
def _unverified_send(self, request, **kwargs):
    kwargs['verify'] = False
    return _orig_send(self, request, **kwargs)
requests.Session.send = _unverified_send

from google_auth_oauthlib.flow import InstalledAppFlow

BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "outputs" / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def generate_token():
    print("==================================================")
    print("ONE-TIME YOUTUBE OAUTH AUTHENTICATION HELPER")
    print("==================================================")

    if not CLIENT_SECRET_FILE.exists():
        print(f"[ERROR] client_secret.json not found at: {CLIENT_SECRET_FILE}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE),
        scopes=SCOPES
    )
    flow.oauth2session.verify = False

    # Set unbuffered stdout
    sys.stdout.reconfigure(line_buffering=True)

    print("\n[INFO] Starting OAuth server on http://localhost:8085...")
    sys.stdout.flush()

    prompt_msg = (
        "\n==================================================\n"
        "AUTH_URL_START\n{url}\nAUTH_URL_END\n"
        "==================================================\n"
        "Waiting for authentication in browser...\n"
    )

    creds = flow.run_local_server(
        host='localhost',
        port=8085,
        authorization_prompt_message=prompt_msg,
        success_message='[SUCCESS] YouTube Authentication Completed! You can close this tab now.',
        open_browser=False,
        prompt='consent',
        access_type='offline'
    )

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())

    print("\n[SUCCESS] YouTube Authentication Successful!")
    print(f"Saved credentials token to: {TOKEN_FILE}")
    sys.stdout.flush()

if __name__ == "__main__":
    generate_token()
