"""Local-only integration monitor. No audio is received or stored here."""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import threading
import time
from audio.events import validate_event

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
            self.reply(200, Path(__file__).with_name('monitor.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/state':
            self.reply(200, state.snapshot())
        else:
            self.reply(404, {'error':'Not found'})

    def do_POST(self):
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
    print('Alert monitor: http://127.0.0.1:8765', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.decision_log.close()
