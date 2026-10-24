"""Serve the built phone mirror on a trusted LAN without exposing receiver controls.

Build frontend first. Run: python3 scripts/phone_mirror.py --host YOUR_WIFI_IP --receiver http://127.0.0.1:8766
"""
import argparse
import hmac
import secrets
from http.cookies import SimpleCookie
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit, parse_qs
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


class ViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        key = parse_qs(urlsplit(self.path).query).get('key', [''])[0]
        if path == '/' and hmac.compare_digest(key.encode(), self.server.access_key.encode()):
            self.send_response(302)
            self.send_header('Set-Cookie', f'aware_viewer={key}; HttpOnly; SameSite=Strict; Path=/')
            self.send_header('Location', '/index.html?viewer=1')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            self.send_error(403)
            return
        token = cookie.get('aware_viewer')
        if not token or not hmac.compare_digest(token.value.encode(), self.server.access_key.encode()):
            self.send_error(403, 'Open the access link from the companion Mac')
            return
        if path == '/api/state':
            try:
                with urlopen(self.server.receiver + '/state', timeout=2) as response:
                    body = response.read(2_000_000)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (URLError, TimeoutError, OSError):
                self.send_error(503, 'Receiver unavailable')
        elif path == '/':
            self.send_response(302)
            self.send_header('Location', '/index.html?viewer=1')
            self.end_headers()
        elif path == '/index.html' or path.startswith('/assets/'):
            super().do_GET()
        else:
            self.send_error(404)

    def do_HEAD(self):
        # Avoid SimpleHTTPRequestHandler's directory/file discovery on other paths.
        self.send_error(405)

    def reject_write(self):
        self.send_error(405, 'Read-only viewer')

    do_POST = do_PUT = do_PATCH = do_DELETE = reject_write

    def log_message(self, format, *args):
        # Access links contain a temporary key; never put request URLs in logs.
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5176)
    parser.add_argument('--receiver', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    build = ROOT / 'frontend/dist'
    if not (build / 'index.html').exists():
        parser.error('Run npm run build --prefix frontend first')
    server = ThreadingHTTPServer((args.host, args.port), partial(ViewerHandler, directory=str(build)))
    server.receiver = args.receiver.rstrip('/')
    server.access_key = secrets.token_urlsafe(32)
    print(f'Phone access link: http://{args.host}:{args.port}/?key={server.access_key}', flush=True)
    print('Same trusted Wi-Fi required. Link expires when this process stops. HTTP is not encrypted.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
