"""Let a phone on the same Wi-Fi send direction readings to the local receiver, and nothing else.

Run: .venv/bin/python scripts/phone_spatial_relay.py --host YOUR_WIFI_IP --receiver http://127.0.0.1:8766
Enter the printed address and pairing code in the iPhone probe. The receiver itself stays on
127.0.0.1; this relay accepts only POST /spatial (and GET /ping) carrying the code. HTTP is not
encrypted, so use it only on a network you are willing to share readings over; the code expires
when the relay stops.
"""
import argparse
import hmac
import json
import secrets
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # no look-alike characters, easy to type on a phone


class RelayHandler(BaseHTTPRequestHandler):
    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        code = self.headers.get('X-Aware-Code', '').strip().upper()
        return hmac.compare_digest(code.encode(), self.server.code.encode())

    def do_GET(self):
        if self.path != '/ping':
            return self.reply(404, {'error': 'Not found'})
        if not self.authorized():
            return self.reply(403, {'error': 'Wrong pairing code'})
        self.reply(200, {'ok': True})

    def do_POST(self):
        if self.path != '/spatial':
            return self.reply(404, {'error': 'Not found'})
        if not self.authorized():
            return self.reply(403, {'error': 'Wrong pairing code'})
        now = time.monotonic()
        self.server.sent = [t for t in self.server.sent if now - t < 1] + [now]
        if len(self.server.sent) > 25:
            return self.reply(429, {'error': 'Too many readings'})
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 512:
            return self.reply(400, {'error': 'Expected a small JSON body'})
        body = self.rfile.read(length)
        try:
            request = Request(self.server.receiver + '/spatial', data=body,
                              headers={'Content-Type': 'application/json'})
            with urlopen(request, timeout=2) as response:
                self.reply(response.status, json.loads(response.read(4096)))
        except HTTPError as error:
            self.reply(error.code, {'error': 'Receiver rejected the reading'})
        except (URLError, TimeoutError, OSError):
            self.reply(503, {'error': 'Receiver unavailable'})

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='This Mac\'s Wi-Fi address, e.g. 10.0.0.12')
    parser.add_argument('--port', type=int, default=5177)
    parser.add_argument('--receiver', default='http://127.0.0.1:8766')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), RelayHandler)
    server.receiver = args.receiver.rstrip('/')
    server.code = ''.join(secrets.choice(ALPHABET) for _ in range(6))
    server.sent = []
    print(f'Phone direction relay: http://{args.host}:{args.port}  pairing code: {server.code}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
