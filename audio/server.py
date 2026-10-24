"""Local-only integration monitor plus custom-sound onboarding routes.

Alert routes never receive audio. The /custom-sounds and /background routes receive short WAV
recordings from the onboarding UI and keep them in .cache/custom-sounds/ (see docs/custom-sounds.md).
Bound to loopback; CORS is allowed only for localhost / 127.0.0.1 origins (local dev servers).
"""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import threading
import time
from audio.events import validate_event
from audio.observations import MAX_BYTES as MAX_OBSERVATION_BYTES, validate_observation

class AlertState:
    def __init__(self, decision_log=None):
        self.events = deque(maxlen=50)
        self.active = None
        self.expires = 0
        self.lock = threading.Lock()
        self.decisions=deque(maxlen=50)
        self.decision_log=decision_log

    def add(self, event, now=None):
        with self.lock:
            self.events.append(event)
            now = time.monotonic() if now is None else now
            if self.expires <= now:
                self.active = None
            tier = event['priority_tier']
            reason='ignored_tier_zero' if tier==0 else 'suppressed_lower_priority'
            if tier and (self.active is None or tier >= self.active['priority_tier']):
                self.active = event
                self.expires = now + {1:2, 2:3, 3:5, 4:30}[tier]
                reason='displayed'
            decision=dict(kind='alert_state',event_id=event['event_id'],type=event['type'],
                          priority_tier=tier,reason=reason,
                          active_type=self.active['type'] if self.active else None)
            self.decisions.append(decision)
            if self.decision_log:
                self.decision_log.write(decision)

    def snapshot(self, now=None):
        with self.lock:
            if (time.monotonic() if now is None else now) >= self.expires:
                self.active = None
            return {'active':self.active, 'events':list(self.events),'decisions':list(self.decisions)}

state = AlertState()

class ObservationStore:
    """Last two minutes of per-window observations, each numbered with an increasing `seq`."""
    def __init__(self, maxlen=120):
        self.items = deque(maxlen=maxlen)
        self.seq = 0
        self.lock = threading.Lock()
        self.started_ms = int(time.time()*1000)   # changes on restart, so clients can reset `since`

    def add(self, observation):
        with self.lock:
            self.seq += 1
            observation = dict(observation, seq=self.seq, received_ms=int(time.time()*1000))
            self.items.append(observation)
            return self.seq

    def since(self, after=0, limit=20):
        with self.lock:
            selected = [o for o in self.items if o['seq'] > after][-limit:]
            return dict(latest_seq=self.seq, server_started_ms=self.started_ms, observations=selected)

observations = ObservationStore()

MAX_JSON_BYTES = 8192
MAX_AUDIO_BYTES = 8*1024*1024   # 30 s of 48 kHz stereo 16-bit WAV is ~5.8 MB
LOCAL_ORIGIN = re.compile(r'^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d{1,5})?$')
EXTRA_ORIGINS = {o.strip() for o in os.environ.get('CALHACKS_CORS_ORIGINS', '').split(',') if o.strip()}

class CustomSounds:
    """Lazy-loads the embedding model on the first audio request, so the mock/UI path still
    needs only the Python standard library."""
    def __init__(self):
        self.lock = threading.Lock()
        self.embedder = None

    def get_embedder(self):
        if self.embedder is None:
            try:
                from audio.embeddings import ZipformerEmbedder
                self.embedder = ZipformerEmbedder()
            except ImportError as exc:
                raise RuntimeError(f'{exc.name} not installed; install requirements-audio.txt') from None
        return self.embedder

custom = CustomSounds()

class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status

def custom_route(method, parts, body_json, body_audio):
    """Dispatch /custom-sounds and /background. Returns (status, payload)."""
    from audio import custom_sounds as cs
    if parts == ['background']:
        if method == 'GET':
            return 200, cs.background_status()
        if method == 'DELETE':
            with custom.lock:
                cs.clear_room_background()
                retrained = cs.retrain_trained(custom.get_embedder()) if cs.background_status()['ready'] else []
            return 200, dict(cs.background_status(), retrained=[m['id'] for m in retrained])
    if parts == ['background', 'clips'] and method == 'POST':
        with custom.lock:
            windows = cs.add_room_background(custom.get_embedder(), body_audio())
            retrained = cs.retrain_trained(custom.get_embedder())
        return 200, dict(cs.background_status(), added_windows=windows,
                         retrained=[dict(id=m['id'], status=m['status']) for m in retrained])
    if parts == ['custom-sounds']:
        if method == 'GET':
            return 200, dict(sounds=cs.list_sounds(), background=cs.background_status())
        if method == 'POST':
            payload = body_json()
            return 201, cs.create_sound(payload.get('label'), payload.get('priority_tier', 2))
    if len(parts) >= 2 and parts[0] == 'custom-sounds':
        sound_id = parts[1]
        if not re.fullmatch(r'[a-z0-9-]{1,64}', sound_id) or not (cs.STORE/sound_id/'meta.json').exists():
            raise HttpError(404, 'Unknown custom sound')
        action = parts[2] if len(parts) == 3 else None
        if len(parts) == 2:
            if method == 'GET':
                return 200, cs.read_meta(sound_id)
            if method == 'PATCH':
                return 200, cs.update_sound(sound_id, body_json())
            if method == 'DELETE':
                with custom.lock:
                    cs.remove_sound(sound_id)
                return 200, {'ok': True}
        elif method == 'POST' and action == 'clips':
            with custom.lock:
                return 200, cs.add_clip(sound_id, body_audio())
        elif method == 'DELETE' and action == 'clips':
            with custom.lock:
                return 200, cs.clear_clips(sound_id)
        elif method == 'POST' and action == 'train':
            with custom.lock:
                meta = cs.train_sound(sound_id, custom.get_embedder())
            return 200, meta
        elif method == 'POST' and action == 'test':
            with custom.lock:
                return 200, cs.test_clip(sound_id, custom.get_embedder(), body_audio())
    raise HttpError(404 if method in ('GET', 'POST', 'PATCH', 'DELETE') else 405, 'Not found')

class Handler(BaseHTTPRequestHandler):
    def cors_headers(self):
        origin = self.headers.get('Origin')
        if origin and (LOCAL_ORIGIN.match(origin) or origin in EXTRA_ORIGINS):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Max-Age', '600')

    def reply(self, status, payload, content_type='application/json'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_body(self, limit):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= limit:
            raise ValueError(f'Expected body of 1..{limit} bytes')
        return self.rfile.read(length)

    def body_json(self):
        if (self.headers.get('Content-Type') or '').split(';')[0].strip() != 'application/json':
            raise ValueError('Expected application/json')
        payload = json.loads(self.read_body(MAX_JSON_BYTES))
        if not isinstance(payload, dict):
            raise ValueError('Expected a JSON object')
        return payload

    def body_audio(self):
        from audio.custom_sounds import decode_audio
        kind = (self.headers.get('Content-Type') or '').split(';')[0].strip()
        if kind not in ('audio/wav', 'audio/x-wav', 'audio/wave', 'audio/flac', 'audio/ogg', 'application/octet-stream'):
            raise ValueError('Expected audio/wav (16 kHz mono recommended)')
        return decode_audio(self.read_body(MAX_AUDIO_BYTES))

    def custom(self, method):
        parts = [p for p in self.path.split('?')[0].split('/') if p]
        try:
            status, payload = custom_route(method, parts, self.body_json, self.body_audio)
            self.reply(status, payload)
        except HttpError as exc:
            self.reply(exc.status, {'error': str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.reply(400, {'error': str(exc)})
        except RuntimeError as exc:   # missing model, dependency or background bank
            self.reply(503, {'error': str(exc)})

    def is_custom(self):
        first = self.path.split('?')[0].strip('/').split('/')[0]
        return first in ('custom-sounds', 'background')

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors_headers()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_PATCH(self):
        self.custom('PATCH') if self.is_custom() else self.reply(404, {'error':'Not found'})

    def do_DELETE(self):
        self.custom('DELETE') if self.is_custom() else self.reply(404, {'error':'Not found'})

    def do_GET(self):
        if self.path == '/':
            self.reply(200, Path(__file__).with_name('monitor.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/teach':
            self.reply(200, Path(__file__).with_name('teach.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/state':
            self.reply(200, state.snapshot())
        elif self.path.split('?')[0] == '/observations':
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            try:
                after = int(query.get('since', ['0'])[0])
                limit = min(max(int(query.get('limit', ['20'])[0]), 1), 120)
            except ValueError:
                return self.reply(400, {'error': 'since and limit must be integers'})
            self.reply(200, observations.since(after, limit))
        elif self.is_custom():
            self.custom('GET')
        else:
            self.reply(404, {'error':'Not found'})

    def do_POST(self):
        if self.is_custom():
            return self.custom('POST')
        if self.path == '/observations':
            try:
                payload = json.loads(self.read_body(MAX_OBSERVATION_BYTES))
                if (self.headers.get('Content-Type') or '').split(';')[0].strip() != 'application/json':
                    raise ValueError('Expected application/json')
                return self.reply(200, {'ok': True, 'seq': observations.add(validate_observation(payload))})
            except (ValueError, TypeError) as exc:
                return self.reply(400, {'error': str(exc)})
        if self.path not in ('/events', '/dismiss'):
            return self.reply(404, {'error':'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                raise ValueError('Expected body of 1..8192 bytes')
            if self.headers.get('Content-Type') != 'application/json':
                raise ValueError('Expected application/json')
            payload = json.loads(self.rfile.read(length))
            if self.path == '/dismiss':
                with state.lock:
                    state.active = None
                    state.expires = 0
            else:
                state.add(validate_event(payload))
            self.reply(200, {'ok':True})
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error':str(exc)})

    def log_message(self, *args):
        pass

def create_server(port=8765):
    global state
    from audio.decision_log import DecisionLog
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    state=AlertState(decision_log=DecisionLog(Path(__file__).resolve().parent.parent/'.cache'/'alert-decisions.jsonl'))
    return server

if __name__ == '__main__':
    server=create_server()
    print('Alert monitor: http://127.0.0.1:8765  ·  Teach a sound: http://127.0.0.1:8765/teach', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.decision_log.close()
