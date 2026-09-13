"""
GitHub Actions Workflow Trigger Helper Module
Triggers the 24/7 Cloud Video Render & YouTube Upload workflow on GitHub Actions.
Supports privacy_status ('unlisted', 'private', 'public') and optional drive_thumbnail_url.
"""

import os
import sys
import subprocess
import requests
from typing import Dict, Any

REPO_OWNER = "YoutubeVideoUploader"
REPO_NAME = "auto-youtube-poster"
WORKFLOW_FILE = "auto_youtube_poster.yml"


def trigger_github_workflow(privacy_status: str = "unlisted", drive_thumbnail_url: str = "") -> Dict[str, Any]:
    """
    Triggers GitHub Actions workflow auto_youtube_poster.yml on main branch.
    
    Parameters:
        privacy_status: 'unlisted', 'private', or 'public'
        drive_thumbnail_url: Optional shareable link to custom thumbnail on Google Drive
        
    Returns:
        Dict with status, message, privacy_status, and actions_url.
    """
    privacy_status = (privacy_status or "unlisted").lower().strip()
    if privacy_status not in ["unlisted", "private", "public"]:
        privacy_status = "unlisted"

    drive_thumbnail_url = (drive_thumbnail_url or "").strip()
    actions_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/actions"

    # Strategy 1: Attempt triggering via installed GitHub CLI (gh)
    try:
        cmd = [
            "gh", "workflow", "run", WORKFLOW_FILE,
            "-f", f"privacy_status={privacy_status}"
        ]
        if drive_thumbnail_url:
            cmd.extend(["-f", f"drive_thumbnail_url={drive_thumbnail_url}"])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            output_msg = res.stdout.strip() or res.stderr.strip()
            run_link = output_msg if "https://github.com" in output_msg else actions_url
            return {
                "status": "success",
                "method": "gh_cli",
                "privacy_status": privacy_status,
                "drive_thumbnail_url": drive_thumbnail_url,
                "actions_url": run_link,
                "message": f"Successfully triggered 24/7 Cloud Render & Upload! (Privacy: '{privacy_status}')"
            }
    except Exception as e:
        print(f"[!] GH CLI trigger note: {e}")

    # Strategy 2: Fallback to GitHub REST API repository_dispatch / workflow_dispatch
    github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if github_token:
        try:
            url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "ref": "main",
                "inputs": {
                    "privacy_status": privacy_status,
                    "drive_thumbnail_url": drive_thumbnail_url
                }
            }
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code in [200, 204]:
                return {
                    "status": "success",
                    "method": "github_api",
                    "privacy_status": privacy_status,
                    "drive_thumbnail_url": drive_thumbnail_url,
                    "actions_url": actions_url,
                    "message": f"Successfully triggered 24/7 Cloud Render via GitHub REST API! (Privacy: '{privacy_status}')"
                }
            else:
                print(f"[!] GitHub API returned status code {r.status_code}: {r.text}")
        except Exception as e:
            print(f"[!] GitHub REST API dispatch warning: {e}")

    return {
        "status": "error",
        "method": "failed",
        "privacy_status": privacy_status,
        "actions_url": actions_url,
        "message": (
            "Failed to trigger GitHub Actions directly. "
            "Please ensure `gh` CLI is logged in (`gh auth login`) or a GITHUB_TOKEN environment variable is set."
        )
    }


if __name__ == "__main__":
    priv = sys.argv[1] if len(sys.argv) > 1 else "unlisted"
    url = sys.argv[2] if len(sys.argv) > 2 else ""
    result = trigger_github_workflow(privacy_status=priv, drive_thumbnail_url=url)
    print(result)
