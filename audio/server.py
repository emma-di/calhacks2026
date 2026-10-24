"""Local receiver: validated events in, one authoritative alert state out. No audio is received here.

Endpoints (JSON):
  GET  /state     companion/mirror snapshot (backward compatible active/events/decisions + engine state)
  GET  /display   display-consumer envelope for the glasses (hardware.display.Presentation)
  GET  /health    receiver, capture, display and worker availability
  GET  /profile   saved preferences;  PUT /profile  validate, apply and persist atomically
  POST /events    detection events;   POST /dismiss {event_id?};  POST /controls {focus_mode?, paused?}
  POST /look      {direction} or {heading_degrees}: the wearer turned toward the sound, resolving it
  POST /observations, GET /observations?since=  per-window recognizer reports (John's format): signal panel + heartbeat
  POST /spatial   phone FOA reading {bearing_degrees, coherence, rms, calibrated, device}; matched to sounds
  POST /spatial/calibrate {examples: {front: [...], right: [...], behind: [...], left: [...]}}: phone bearings heard per side
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import math
import os
import threading
import time
from urllib.parse import urlsplit, parse_qs
from audio.alerts import AlertEngine, DEFAULT_PROFILE, direction_bucket, validate_profile
from audio.events import EVENT_TYPES, validate_event
from audio.spatial import SpatialBuffer, validate_reading
from collections import deque
from audio.observations import MAX_BYTES as MAX_OBSERVATION_BYTES, validate_observation


class ObservationStore:
    """Last two minutes of per-window observations, each numbered with an increasing `seq`.

    Ported from John's johnaou/observations branch (8a440e1) into the current receiver.
    """
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
        self.spatial = SpatialBuffer(Path(profile_path).with_name('spatial-calibration.json') if profile_path else None)

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
                    event = dict(event, direction_degrees=round(reading['bearing_degrees'], 1),
                                 phone_degrees=reading['phone_degrees'],
                                 direction_confidence=round(reading['coherence'], 3),
                                 direction_source=f"{reading['device']}_foa")
            return self.engine.add(event, at)

    def spatial_calibrate(self, examples):
        with self.lock:
            self.spatial.calibrate(examples)
            return dict(calibration=self.spatial.points)

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
        latest = observations.since(0, 1)['observations']
        heard = latest[0] if latest and time.time() * 1000 - latest[0]['received_ms'] < 3000 else None
        return dict(
            receiver='ok', session_id=self.engine.session_id,
            # Receiver health never implies a listening microphone: only recent capture events do.
            capture=dict(last_event_ms_ago=recent, live=any(
                recent.get(source, 1e12) < 10000 for source in CAPTURE_SOURCES),
                # Heartbeat: a recognizer reporting windows is listening, even in silence.
                listening=bool(heard), listening_source=heard['source'] if heard else None),
            display=dict(connected=bool(displays), clients=displays),
            name_worker='unavailable', spatial=self.spatial.status(at))

    def snapshot(self, now=None):
        with self.lock:
            at = self._ms(now)
            return dict(self.engine.snapshot(at), health=self._health(at),
                        observations=observations.since(0, 10)['observations'],
                        display=self.engine.presentation(at))


state = AlertState()


class Handler(BaseHTTPRequestHandler):
    @property
    def receiver_state(self):
        return self.server.alert_state

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
            self.reply(200, self.receiver_state.snapshot())
        elif url.path == '/display':
            client = parse_qs(url.query).get('client', [None])[0]
            self.reply(200, self.receiver_state.presentation(client))
        elif url.path == '/health':
            self.reply(200, self.receiver_state.health())
        elif url.path == '/observations':
            query = parse_qs(url.query)
            try:
                after = int(query.get('since', ['0'])[0])
                limit = min(max(int(query.get('limit', ['20'])[0]), 1), 120)
            except ValueError:
                return self.reply(400, {'error': 'since and limit must be integers'})
            self.reply(200, observations.since(after, limit))
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
        if path == '/observations':
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_OBSERVATION_BYTES:
                    raise ValueError(f'Expected body of 1..{MAX_OBSERVATION_BYTES} bytes')
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    raise ValueError('Expected application/json')
                payload = json.loads(self.rfile.read(length))
                return self.reply(200, {'ok': True, 'seq': observations.add(validate_observation(payload))})
            except (ValueError, TypeError) as exc:
                return self.reply(400, {'error': str(exc)})
        if path not in ('/events', '/dismiss', '/controls', '/look', '/spatial', '/spatial/calibrate'):
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
            if path == '/spatial/calibrate':
                return self.reply(200, dict(ok=True, **self.receiver_state.spatial_calibrate(
                    payload.get('examples', {}))))
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
