"""Local receiver: validated events in, one authoritative alert state out. No audio is received here.

Endpoints (JSON):
  GET  /state     companion/mirror snapshot (backward compatible active/events/decisions + engine state)
  GET  /display   display-consumer envelope for the glasses (hardware.display.Presentation)
  GET  /health    receiver, capture, display and worker availability
  GET  /profile   saved preferences;  PUT /profile  validate, apply and persist atomically
  POST /events    detection events;   POST /dismiss {event_id?};  POST /controls {focus_mode?, paused?}
  POST /look      {direction} or {heading_degrees}: the wearer turned toward the sound, resolving it
  POST /spatial   phone FOA reading {bearing_degrees, coherence, rms, calibrated, device}; matched to sounds

Audio features (loopback clients only, so a network display client can never record or upload):
  GET  /teach                      reference page: room background, custom sounds, your name
  GET  /observations?since=&limit= per-window "what it heard" stream;  POST /observations (recognizer)
  /custom-sounds[/{id}[/clips|/train|/test]], /background[/clips]   see docs/custom-sounds.md
  POST /profile/name-samples (WAV), DELETE /profile/name-samples    see docs/name-detection.md
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import math
import os
import threading
import time
import re
from collections import deque
from urllib.parse import urlsplit, parse_qs
from audio.alerts import AlertEngine, DEFAULT_PROFILE, direction_bucket, validate_profile
from audio.events import EVENT_TYPES, validate_event
from audio.observations import MAX_BYTES as MAX_OBSERVATION_BYTES, validate_observation
from audio.spatial import SpatialBuffer, validate_reading

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_SOURCES = ('microphone', 'replay', 'simulation')
LOOPBACK = ('127.0.0.1', '::1', '::ffff:127.0.0.1')
MAX_AUDIO_BYTES = 8 * 1024 * 1024   # 30 s of 48 kHz stereo 16-bit WAV is ~5.8 MB


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
        self.spatial = SpatialBuffer()

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
            at = self._ms(now)
            self.last_event[event['source']] = at
            if event.get('direction_degrees') is None and event['source'] in CAPTURE_SOURCES:
                reading = self.spatial.match(at)
                if reading:
                    # Same moment, separate device: direction comes from the phone's FOA microphones.
                    event = dict(event, direction_degrees=reading['bearing_degrees'],
                                 direction_confidence=round(reading['coherence'], 3),
                                 direction_source=f"{reading['device']}_foa")
            return self.engine.add(event, at)

    def spatial_reading(self, value, now=None):
        reading = validate_reading(value)
        with self.lock:
            self.spatial.add(reading, self._ms(now))
        return reading

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
        with self.lock:
            value = carry_name_fields(value, self.engine.profile)
        profile = validate_profile(value, EVENT_TYPES)
        with self.lock:
            profile = dict(profile, revision=self.engine.profile['revision'] + 1)
            if self.profile_path:
                self.profile_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = self.profile_path.with_suffix('.tmp')
                temporary.write_text(json.dumps(profile, indent=2))
                os.replace(temporary, self.profile_path)
            # Apply only after persistence succeeds: a rejected save must not change live behavior.
            self.engine.set_profile(profile)
            return self.engine.profile

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
            name_worker=self._name_worker(recent), spatial=self.spatial.status(at))

    def _name_worker(self, recent):
        """'off' unless enabled in the profile; 'listening' only while a capture source is live."""
        names = self.engine.profile.get('name_detection', {})
        if not names.get('enabled') or not names.get('primary_name'):
            return 'off'
        from audio.names import KWS_DIR
        if not (KWS_DIR / 'tokens.txt').exists():
            return 'model_missing'
        live = any(recent.get(source, 1e12) < 10000 for source in CAPTURE_SOURCES)
        return 'listening' if live else 'idle'

    def snapshot(self, now=None):
        with self.lock:
            at = self._ms(now)
            return dict(self.engine.snapshot(at), health=self._health(at),
                        display=self.engine.presentation(at))


def carry_name_fields(value, current):
    """Clients that don't know the name worker's own fields (the companion's onboarding) must not erase
    them: keep sensitivity, and keep learned spellings while the name itself is unchanged."""
    if not isinstance(value, dict) or not isinstance(value.get('name_detection'), dict):
        return value
    incoming, saved = dict(value['name_detection']), current.get('name_detection', {})
    if 'sensitivity' not in incoming and 'sensitivity' in saved:
        incoming['sensitivity'] = saved['sensitivity']
    if 'learned_spellings' not in incoming:
        same_name = ' '.join(str(incoming.get('primary_name', '')).split()).casefold() == \
            ' '.join(str(saved.get('primary_name', '')).split()).casefold()
        incoming['learned_spellings'] = list(saved.get('learned_spellings', [])) if same_name else []
    return dict(value, name_detection=incoming)


state = AlertState()


class ObservationStore:
    """Last two minutes of per-window observations, each numbered with an increasing `seq`."""

    def __init__(self, maxlen=120):
        self.items = deque(maxlen=maxlen)
        self.seq = 0
        self.lock = threading.Lock()
        self.started_ms = int(time.time() * 1000)   # changes on restart, so clients can reset `since`

    def add(self, observation):
        with self.lock:
            self.seq += 1
            self.items.append(dict(observation, seq=self.seq, received_ms=int(time.time() * 1000)))
            return self.seq

    def since(self, after=0, limit=20):
        with self.lock:
            selected = [o for o in self.items if o['seq'] > after][-limit:]
            return dict(latest_seq=self.seq, server_started_ms=self.started_ms, observations=selected)


class Embedder:
    """Loads the embedding model on the first audio request, so the receiver itself still needs only
    the standard library; one lock serializes training and room-background updates."""

    def __init__(self):
        self.lock = threading.Lock()
        self.model = None

    def get(self):
        if self.model is None:
            try:
                from audio.embeddings import ZipformerEmbedder
                self.model = ZipformerEmbedder()
            except ImportError as exc:
                raise RuntimeError(f'{exc.name} not installed; install requirements-audio.txt') from None
        return self.model


observations = ObservationStore()
embedder = Embedder()


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def audio_route(method, parts, handler):
    """/custom-sounds, /background and /profile/name-samples. Returns (status, payload)."""
    from audio import custom_sounds as cs
    if parts == ['profile', 'name-samples']:
        from audio import names
        receiver = handler.receiver_state
        if method == 'POST':
            with embedder.lock:
                try:
                    updated, report = names.learn_spelling(handler.read_audio(), receiver.profile())
                except (ImportError, FileNotFoundError) as exc:
                    raise RuntimeError(f'name model missing ({exc}); run python -m audio.download_model --names') from None
            profile = receiver.save_profile(updated) if updated else receiver.profile()
            return 200, dict(report, profile=profile)
        if method == 'DELETE':
            profile = json.loads(json.dumps(receiver.profile()))
            profile['name_detection']['learned_spellings'] = []
            return 200, receiver.save_profile(profile)
    if parts == ['background']:
        if method == 'GET':
            return 200, cs.background_status()
        if method == 'DELETE':
            with embedder.lock:
                cs.clear_room_background()
                retrained = cs.retrain_trained(embedder.get()) if cs.background_status()['ready'] else []
            return 200, dict(cs.background_status(), retrained=[m['id'] for m in retrained])
    if parts == ['background', 'clips'] and method == 'POST':
        with embedder.lock:
            windows = cs.add_room_background(embedder.get(), handler.read_audio())
            retrained = cs.retrain_trained(embedder.get())
        return 200, dict(cs.background_status(), added_windows=windows,
                         retrained=[dict(id=m['id'], status=m['status']) for m in retrained])
    if parts == ['custom-sounds']:
        if method == 'GET':
            return 200, dict(sounds=cs.list_sounds(), background=cs.background_status())
        if method == 'POST':
            payload = handler.read_json()
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            return 201, cs.create_sound(payload.get('label'), payload.get('priority_tier', 2))
    if len(parts) in (2, 3) and parts[0] == 'custom-sounds':
        sound_id = parts[1]
        if not re.fullmatch(r'[a-z0-9-]{1,64}', sound_id) or not (cs.STORE / sound_id / 'meta.json').exists():
            raise HttpError(404, 'Unknown custom sound')
        action = parts[2] if len(parts) == 3 else None
        if action is None:
            if method == 'GET':
                return 200, cs.read_meta(sound_id)
            if method == 'PATCH':
                payload = handler.read_json()
                if not isinstance(payload, dict):
                    raise ValueError('Expected a JSON object')
                return 200, cs.update_sound(sound_id, payload)
            if method == 'DELETE':
                with embedder.lock:
                    cs.remove_sound(sound_id)
                return 200, {'ok': True}
        elif action == 'clips' and method == 'POST':
            with embedder.lock:
                return 200, cs.add_clip(sound_id, handler.read_audio())
        elif action == 'clips' and method == 'DELETE':
            with embedder.lock:
                return 200, cs.clear_clips(sound_id)
        elif action == 'train' and method == 'POST':
            with embedder.lock:
                return 200, cs.train_sound(sound_id, embedder.get())
        elif action == 'test' and method == 'POST':
            with embedder.lock:
                return 200, cs.test_clip(sound_id, embedder.get(), handler.read_audio())
    raise HttpError(404, 'Not found')


def is_audio_route(parts):
    return bool(parts) and (parts[0] in ('custom-sounds', 'background') or parts[:2] == ['profile', 'name-samples'])


class Handler(BaseHTTPRequestHandler):
    @property
    def receiver_state(self):
        return self.server.alert_state

    @property
    def observation_store(self):
        return getattr(self.server, 'observations', observations)

    def parts(self):
        return [p for p in urlsplit(self.path).path.split('/') if p]

    def from_loopback(self):
        return self.client_address[0] in LOOPBACK

    def read_audio(self):
        from audio.custom_sounds import decode_audio
        kind = self.headers.get('Content-Type', '').split(';')[0].strip()
        if kind not in ('audio/wav', 'audio/x-wav', 'audio/wave', 'audio/flac', 'audio/ogg', 'application/octet-stream'):
            raise ValueError('Expected audio/wav (16 kHz mono recommended)')
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= MAX_AUDIO_BYTES:
            raise ValueError(f'Expected audio of 1..{MAX_AUDIO_BYTES} bytes')
        return decode_audio(self.rfile.read(length))

    def audio(self, method):
        """Dispatch an audio route; recording, training and uploads are refused off the laptop."""
        if not self.from_loopback():
            return self.reply(403, {'error': 'Audio routes are only available on the laptop running the receiver'})
        try:
            status, payload = audio_route(method, self.parts(), self)
            self.reply(status, payload)
        except HttpError as exc:
            self.reply(exc.status, {'error': str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.reply(400, {'error': str(exc)})
        except RuntimeError as exc:   # missing model, dependency or background bank
            self.reply(503, {'error': str(exc)})
        except OSError:
            self.reply(503, {'error': 'Could not save; previous settings remain active'})

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
        if is_audio_route(self.parts()):
            return self.audio('GET')
        if url.path == '/':
            self.reply(200, Path(__file__).with_name('monitor.html').read_bytes(), 'text/html; charset=utf-8')
        elif url.path == '/teach':
            if not self.from_loopback():
                return self.reply(403, {'error': 'The teach page is only available on the laptop'})
            self.reply(200, Path(__file__).with_name('teach.html').read_bytes(), 'text/html; charset=utf-8')
        elif url.path == '/observations':
            query = parse_qs(url.query)
            try:
                after = int(query.get('since', ['0'])[0])
                limit = min(max(int(query.get('limit', ['20'])[0]), 1), 120)
            except ValueError:
                return self.reply(400, {'error': 'since and limit must be integers'})
            self.reply(200, self.observation_store.since(after, limit))
        elif url.path == '/state':
            self.reply(200, self.receiver_state.snapshot())
        elif url.path == '/display':
            client = parse_qs(url.query).get('client', [None])[0]
            self.reply(200, self.receiver_state.presentation(client))
        elif url.path == '/health':
            self.reply(200, self.receiver_state.health())
        elif url.path == '/profile':
            self.reply(200, self.receiver_state.profile())
        else:
            self.reply(404, {'error': 'Not found'})

    def read_json(self):
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 8192:
            raise ValueError('Expected body of 1..8192 bytes')
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            raise ValueError('Expected application/json')
        return json.loads(self.rfile.read(length))

    def do_PATCH(self):
        if is_audio_route(self.parts()):
            return self.audio('PATCH')
        self.reply(404, {'error': 'Not found'})

    def do_DELETE(self):
        if is_audio_route(self.parts()):
            return self.audio('DELETE')
        self.reply(404, {'error': 'Not found'})

    def do_PUT(self):
        if urlsplit(self.path).path != '/profile':
            return self.reply(404, {'error': 'Not found'})
        try:
            self.reply(200, self.receiver_state.save_profile(self.read_json()))
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})
        except OSError:
            self.reply(503, {'error': 'Preferences could not be saved; previous settings remain active'})

    def do_POST(self):
        path = urlsplit(self.path).path
        if is_audio_route(self.parts()):
            return self.audio('POST')
        if path == '/observations':
            if not self.from_loopback():
                return self.reply(403, {'error': 'Observations are accepted only from the laptop'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_OBSERVATION_BYTES:
                    raise ValueError(f'Expected body of 1..{MAX_OBSERVATION_BYTES} bytes')
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    raise ValueError('Expected application/json')
                observation = validate_observation(json.loads(self.rfile.read(length)))
                return self.reply(200, {'ok': True, 'seq': self.observation_store.add(observation)})
            except (ValueError, TypeError) as exc:
                return self.reply(400, {'error': str(exc)})
        if path not in ('/events', '/dismiss', '/controls', '/look', '/spatial'):
            return self.reply(404, {'error': 'Not found'})
        try:
            payload = self.read_json()
            if not isinstance(payload, dict):
                raise ValueError('Expected a JSON object')
            if path == '/dismiss':
                event_id = payload.get('event_id')
                if event_id is not None and not isinstance(event_id, str):
                    raise ValueError('event_id must be a string')
                return self.reply(200, {'ok': True, 'dismissed': self.receiver_state.dismiss(event_id)})
            if path == '/look':
                direction = payload.get('direction')
                if direction is None and payload.get('heading_degrees') is not None:
                    heading = payload['heading_degrees']
                    if type(heading) not in (int, float) or not math.isfinite(heading):
                        raise ValueError('heading_degrees must be a finite number')
                    direction = direction_bucket(heading, 1.0)
                return self.reply(200, {'ok': True, 'resolved': self.receiver_state.look(direction)})
            if path == '/spatial':
                self.receiver_state.spatial_reading(payload)
                return self.reply(200, {'ok': True})
            if path == '/controls':
                self.receiver_state.controls(focus_mode=payload.get('focus_mode'), paused=payload.get('paused'))
                return self.reply(200, {'ok': True})
            decision = self.receiver_state.add(validate_event(payload))
            self.reply(200, {'ok': True, 'reason': decision['reason'], 'priority_tier': decision['priority_tier']})
        except (ValueError, TypeError) as exc:
            self.reply(400, {'error': str(exc)})

    def log_message(self, *args):
        pass


def create_server(port=8765, host='127.0.0.1', profile_path=None):
    global state
    from audio.decision_log import DecisionLog
    server = ThreadingHTTPServer((host, port), Handler)
    server.alert_state = AlertState(decision_log=DecisionLog(ROOT / '.cache' / 'alert-decisions.jsonl'),
                                    profile_path=profile_path or ROOT / '.cache' / 'profile.json')
    server.observations = ObservationStore()
    state = server.alert_state  # legacy callers; each HTTP handler uses its own server's state
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
