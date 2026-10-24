"""Local receiver: validated events in, one authoritative alert state out. No audio is received here.

Endpoints (JSON):
  GET  /state     companion/mirror snapshot (backward compatible active/events/decisions + engine state)
  GET  /display   display-consumer envelope for the glasses (hardware.display.Presentation)
  GET  /health    receiver, capture, display and worker availability
  GET  /profile   saved preferences;  PUT /profile  validate, apply and persist atomically
  POST /events    detection events;   POST /dismiss {event_id?};  POST /controls {focus_mode?, paused?}
  POST /look      {direction} or {heading_degrees}: the wearer turned toward the sound, resolving it
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading
import time
from urllib.parse import urlsplit, parse_qs
from audio.alerts import AlertEngine, DEFAULT_PROFILE, direction_bucket, validate_profile
from audio.events import EVENT_TYPES, validate_event

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_SOURCES = ('microphone', 'replay', 'simulation')


def now_ms():
    return time.monotonic() * 1000


class AlertState:
    """Thread-safe receiver state around AlertEngine. `now` arguments are monotonic seconds."""

    def __init__(self, decision_log=None, profile_path=None):
        self.lock = threading.Lock()
        self.decision_log = decision_log
        self.profile_path = Path(profile_path) if profile_path else None
        self.engine = AlertEngine(profile=self._load_profile(),
                                  on_decision=decision_log.write if decision_log else None)
        self.last_event = {}       # source -> monotonic ms
        self.display_clients = {}  # client name -> monotonic ms of last /display poll

    @property
    def decisions(self):
        return self.engine.decisions

    def _load_profile(self):
        try:
            saved = json.loads(self.profile_path.read_text())
            profile = validate_profile(saved, EVENT_TYPES)
            profile['revision'] = int(saved.get('revision', 0))
            return profile
        except (AttributeError, OSError, ValueError, TypeError):
            return json.loads(json.dumps(DEFAULT_PROFILE))

    @staticmethod
    def _ms(now):
        return now_ms() if now is None else now * 1000

    def add(self, event, now=None):
        with self.lock:
            self.last_event[event['source']] = self._ms(now)
            return self.engine.add(event, self._ms(now))

    def dismiss(self, event_id=None, now=None):
        with self.lock:
            return self.engine.dismiss(self._ms(now), event_id)

    def look(self, direction, now=None):
        with self.lock:
            return self.engine.look(self._ms(now), direction)

    def controls(self, now=None, **changes):
        with self.lock:
            self.engine.set_controls(self._ms(now), **changes)

    def profile(self):
        with self.lock:
            return self.engine.profile

    def save_profile(self, value):
        profile = validate_profile(value, EVENT_TYPES)
        with self.lock:
            profile = self.engine.set_profile(profile)
            if self.profile_path:
                self.profile_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.profile_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(profile, indent=2))
                os.replace(temporary, self.profile_path)
            return profile

    def presentation(self, client=None, now=None):
        with self.lock:
            if client:
                self.display_clients[client[:40]] = self._ms(now)
            return self.engine.presentation(self._ms(now))

    def health(self, now=None):
        with self.lock:
            return self._health(self._ms(now))

    def _health(self, at):
        displays = {name: round(at - seen) for name, seen in self.display_clients.items() if at - seen < 3000}
        recent = {source: round(at - seen) for source, seen in self.last_event.items()}
        return dict(
            receiver='ok', session_id=self.engine.session_id,
            # Receiver health never implies a listening microphone: only recent capture events do.
            capture=dict(last_event_ms_ago=recent, live=any(
                recent.get(source, 1e12) < 10000 for source in CAPTURE_SOURCES)),
            display=dict(connected=bool(displays), clients=displays),
            name_worker='unavailable', spatial='unavailable')

    def snapshot(self, now=None):
        with self.lock:
            at = self._ms(now)
            return dict(self.engine.snapshot(at), health=self._health(at),
                        display=self.engine.presentation(at))


state = AlertState()


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
        url = urlsplit(self.path)
        if url.path == '/':
            self.reply(200, Path(__file__).with_name('monitor.html').read_bytes(), 'text/html; charset=utf-8')
        elif url.path == '/state':
            self.reply(200, state.snapshot())
        elif url.path == '/display':
            client = parse_qs(url.query).get('client', [None])[0]
            self.reply(200, state.presentation(client))
        elif url.path == '/health':
            self.reply(200, state.health())
        elif url.path == '/profile':
            self.reply(200, state.profile())
        else:
            self.reply(404, {'error': 'Not found'})

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 8192:
            raise ValueError('Expected body of 1..8192 bytes')
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise ValueError('Expected application/json')
        return json.loads(self.rfile.read(length))

    def do_PUT(self):
        if urlsplit(self.path).path != '/profile':
            return self.reply(404, {'error': 'Not found'})
        try:
            self.reply(200, state.save_profile(self.read_json()))
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in ('/events', '/dismiss', '/controls', '/look'):
            return self.reply(404, {'error': 'Not found'})
        try:
            payload = self.read_json()
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            if path == '/dismiss':
                event_id = payload.get('event_id')
                if event_id is not None and not isinstance(event_id, str):
                    raise ValueError('event_id must be a string')
                return self.reply(200, {'ok': True, 'dismissed': state.dismiss(event_id)})
            if path == '/look':
                direction = payload.get('direction')
                if direction is None and payload.get('heading_degrees') is not None:
                    heading = payload['heading_degrees']
                    if type(heading) not in (int, float):
                        raise ValueError('heading_degrees must be a number')
                    direction = direction_bucket(heading, 1.0)
                return self.reply(200, {'ok': True, 'resolved': state.look(direction)})
            if path == '/controls':
                state.controls(focus_mode=payload.get('focus_mode'), paused=payload.get('paused'))
                return self.reply(200, {'ok': True})
            decision = state.add(validate_event(payload))
            self.reply(200, {'ok': True, 'reason': decision['reason'], 'priority_tier': decision['priority_tier']})
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})

    def log_message(self, *args):
        pass


def create_server(port=8765, host='127.0.0.1', profile_path=None):
    global state
    from audio.decision_log import DecisionLog
    server = ThreadingHTTPServer((host, port), Handler)
    state = AlertState(decision_log=DecisionLog(ROOT / '.cache' / 'alert-decisions.jsonl'),
                       profile_path=profile_path or ROOT / '.cache' / 'profile.json')
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Local alert receiver')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--host', default='127.0.0.1',
                        help='Use 0.0.0.0 only on a trusted network so the glasses Pi can poll /display')
    args = parser.parse_args()
    server = create_server(args.port, args.host)
    print(f'Alert receiver: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.decision_log.close()
