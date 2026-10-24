"""Local sound-map simulator: python3 -m spatial.server, then open http://127.0.0.1:8766

New events from the audio program (audio.server on port 8765) appear as sounds at
simulated positions. Events can also be posted here directly, using the same schema:
python3 -m audio.cli fake knock --endpoint http://127.0.0.1:8766/events
"""
import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

from audio.events import validate_event
from spatial.scene import Scene

scene = Scene()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, payload, content_type='application/json'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, Path(__file__).with_name('radar.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/state':
            self.reply(200, scene.snapshot())
        else:
            self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        routes = {'/sources': self.add_source, '/events': self.add_event, '/head': self.head,
                  '/mics': self.mics, '/noise': self.noise, '/motion': self.motion, '/clear': self.clear}
        if self.path not in routes:
            return self.reply(404, {'error': 'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                raise ValueError('Expected body of 1..8192 bytes')
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Expected application/json')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            self.reply(200, routes[self.path](payload) or {'ok': True})
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})

    def add_source(self, body):
        return scene.add(body.get('type', 'knock'), body.get('x'), body.get('y'), origin='map')

    def add_event(self, body):
        event = validate_event(body)
        return scene.add(event['type'], origin='audio program', label=event['label'], event_id=event['event_id'])

    def head(self, body):
        if 'turn' not in body and 'yaw' not in body:
            raise ValueError('Send {"turn": degrees} or {"yaw": degrees}')
        scene.turn(delta=body.get('turn'), yaw=body.get('yaw'))

    def mics(self, body):
        scene.set_mic_count(body.get('count'))

    def noise(self, body):
        scene.set_noise(body.get('snr_db'))

    def motion(self, body):
        scene.set_motion(body.get('mode'))

    def clear(self, body):
        scene.clear()

    def log_message(self, *args):
        pass


def follow_audio_program(url, stop, interval=0.5):
    """Poll the audio receiver and add each new event as a sound at a simulated position."""
    seen = None
    scene.audio.update(url=url, status='connecting')
    while not stop.is_set():
        try:
            with urlopen(url.rstrip('/') + '/state', timeout=1) as response:
                events = json.load(response).get('events', [])
            ids = [e.get('event_id') for e in events]
            if seen is None:
                seen = set(ids)  # don't replay events from before the map started
            for event in events:
                if event.get('event_id') not in seen:
                    seen.add(event['event_id'])
                    try:
                        scene.add(event['type'], origin='audio program', label=event.get('label'),
                                  event_id=event['event_id'])
                    except (KeyError, ValueError):
                        pass
            scene.audio['status'] = 'connected'
        except (OSError, ValueError):
            scene.audio['status'] = 'not running'
        stop.wait(interval)


def run_ticks(stop):
    """Advance head motion and take mic readings of playing sounds, ten times a second."""
    from spatial.scene import TICK_SECONDS
    while not stop.wait(TICK_SECONDS):
        scene.tick()


def main():
    parser = argparse.ArgumentParser(description='Simulated sound map for the glasses')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--audio-url', default='http://127.0.0.1:8765',
                        help='audio receiver to follow for new events')
    parser.add_argument('--no-audio', action='store_true', help='do not follow the audio program')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    stop = threading.Event()
    threading.Thread(target=run_ticks, args=(stop,), daemon=True).start()
    if not args.no_audio:
        threading.Thread(target=follow_audio_program, args=(args.audio_url, stop), daemon=True).start()
    print(f'Sound map: http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
