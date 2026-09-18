import json
import re
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765

class PosterSearchHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/search':
            self.send_response(404)
            self.end_headers()
            return

        qs = urllib.parse.parse_qs(parsed.query)
        q = qs.get('q', [''])[0].strip()
        if not q:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'[]')
            return

        results = []
        seen = set()

        yt_queries = [f"{q} teaser trailer", f"{q} official movie"]
        for yq in yt_queries:
            try:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(yq)}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                
                vids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                for vid in vids[:6]:
                    if vid not in seen:
                        seen.add(vid)
                        thumb_hd = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                        results.append({
                            'url': thumb_hd,
                            'title': f"{q}",
                            'source': 'YouTube Official'
                        })
            except Exception:
                pass

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(results, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), PosterSearchHandler)
    print(f"Poster Helper Server running on http://127.0.0.1:{PORT}")
    server.serve_forever()
