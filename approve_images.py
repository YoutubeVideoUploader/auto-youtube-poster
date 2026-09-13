"""
Image Approval & Preview Report Generator
Generates an interactive HTML preview report (outputs/image_approval_preview.html)
displaying downloaded candidate images for each topic item (Movie Posters, Actor Portraits, Movie Stills)
and allows committing verified candidates to the persistent Local Image Library (image_library/).
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PREVIEW_FILE = OUTPUT_DIR / "image_approval_preview.html"


def generate_approval_preview_html(metadata_json_path: str) -> str:
    """Reads topic metadata JSON and generates visual HTML preview report for image approval."""
    if not os.path.exists(metadata_json_path):
        raise FileNotFoundError(f"Metadata JSON not found: {metadata_json_path}")

    with open(metadata_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    topic_items = data.get("topic_items", [])

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Malayalam Movie News — Image Approval & Verification Report</title>",
        "<style>",
        "body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #121212; color: #f0f0f0; margin: 0; padding: 20px; }",
        "h1 { text-align: center; color: #00e676; margin-bottom: 5px; }",
        ".subtitle { text-align: center; color: #aaa; margin-bottom: 30px; }",
        ".card { background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 25px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }",
        ".topic-title { color: #ffab40; font-size: 1.2rem; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 8px; }",
        ".meta-info { display: flex; gap: 20px; font-size: 0.95rem; color: #888; margin-bottom: 15px; }",
        ".meta-item { background: #2a2a2a; padding: 5px 12px; border-radius: 6px; }",
        ".meta-item strong { color: #ddd; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; }",
        ".img-container { background: #282828; border-radius: 8px; overflow: hidden; border: 2px solid #3d3d3d; text-align: center; }",
        ".img-container img { width: 100%; height: 220px; object-fit: cover; display: block; }",
        ".img-label { padding: 10px; font-size: 0.85rem; color: #ccc; word-break: break-word; }",
        ".tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; margin-top: 5px; }",
        ".tag-poster { background: #ab47bc; color: white; }",
        ".tag-actor { background: #29b6f6; color: black; }",
        ".tag-still { background: #66bb6a; color: black; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>🎬 Malayalam Movie News — Image Verification & Approval Report</h1>",
        f"<div class='subtitle'>Total Topics Analyzed: {len(topic_items)} | Status: READY FOR VERIFICATION</div>"
    ]

    for item in topic_items:
        t_idx = item.get("topic_index", "")
        t_text = item.get("topic_text", "")
        movie = item.get("movie_name", "N/A")
        people = item.get("people_names", [])
        people_str = ", ".join(people) if isinstance(people, list) else str(people)

        poster_path = item.get("movie_poster_path")
        actor_paths = item.get("actor_photo_paths", [])

        html_parts.append("<div class='card'>")
        html_parts.append(f"<div class='topic-title'>Topic #{t_idx}: {t_text[:120]}...</div>")
        html_parts.append("<div class='meta-info'>")
        html_parts.append(f"<div class='meta-item'><strong>Movie:</strong> {movie}</div>")
        html_parts.append(f"<div class='meta-item'><strong>People:</strong> {people_str}</div>")
        html_parts.append("</div>")

        html_parts.append("<div class='grid'>")

        # Movie Poster
        if poster_path and os.path.exists(poster_path):
            rel_url = Path(poster_path).as_uri()
            html_parts.append(f"<div class='img-container'><img src='{rel_url}'><div class='img-label'><span class='tag tag-poster'>MOVIE POSTER</span><br>{movie}</div></div>")

        # Actor Photos
        for ap in actor_paths:
            if ap and os.path.exists(ap):
                rel_url = Path(ap).as_uri()
                name_stem = Path(ap).parent.name.replace("_", " ")
                html_parts.append(f"<div class='img-container'><img src='{rel_url}'><div class='img-label'><span class='tag tag-actor'>ACTOR PORTRAIT</span><br>{name_stem}</div></div>")

        html_parts.append("</div>")  # end grid
        html_parts.append("</div>")  # end card

    html_parts.append("</body></html>")

    full_html = "\n".join(html_parts)
    with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"[+] Image Approval Preview Report generated: {PREVIEW_FILE}")
    return str(PREVIEW_FILE)


if __name__ == "__main__":
    import sys
    latest_json = str(OUTPUT_DIR / "GoogleSheet_Malayalam_Movie_News_edge_female_v3.4.json")
    if len(sys.argv) > 1:
        latest_json = sys.argv[1]
    if os.path.exists(latest_json):
        generate_approval_preview_html(latest_json)
    else:
        print(f"[!] Metadata file not found at: {latest_json}")
