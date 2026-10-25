"""Raw per-window observations: everything the classifier heard, before any alert decision.

Every analysis window (2 s of audio, every 1 s) becomes one observation with the top-k AudioSet
labels and scores, how each built-in rule and custom sound evaluated it, the audio level, and which
events (if any) were emitted. The recognizer POSTs them to the local server; consumers (live site,
"what the glasses hear" meter, future preference/post-processing stage) poll GET /observations.

No audio, embeddings or transcripts are included.
"""
import json
import math
import queue
import sys
import threading
import time
from urllib.request import Request, urlopen

SCHEMA_VERSION = 1
DEFAULT_TOP_K = 10
MAX_TOP_K = 25
MAX_BYTES = 16384
SOURCES = {'mock', 'replay', 'simulation', 'microphone'}

def level_dbfs(window_rms):
    """RMS level in dBFS (0 = full scale), floored at -100 for silence."""
    return round(20*math.log10(window_rms), 1) if window_rms > 1e-5 else -100.0

def build_observation(scores, *, source, model, timestamp_ms, inference_ms, window_rms,
                      rule_decisions=(), custom_decisions=(), custom_labels=None, events=(),
                      top_k=DEFAULT_TOP_K, window_seconds=2.0, hop_seconds=1.0):
    top = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    rules = {}
    for decision in rule_decisions:
        rules[decision['type']] = dict(score=round(float(decision.get('raw_score', 0)), 4),
                                       threshold=float(decision.get('threshold', 0)),
                                       reason=decision.get('reason', 'unknown'))
    custom = []
    for decision in custom_decisions:
        sound_id = decision['custom_sound_id']
        custom.append(dict(id=sound_id, label=(custom_labels or {}).get(sound_id, sound_id),
                           score=round(float(decision.get('raw_score', 0)), 4),
                           threshold=round(float(decision.get('threshold', 0)), 4),
                           reason=decision.get('reason', 'unknown'),
                           **{key:decision[key] for key in ('matched_label', 'match_kind') if key in decision}))
    return dict(schema_version=SCHEMA_VERSION, kind='observation', source=source, model=model,
                timestamp_ms=int(timestamp_ms if timestamp_ms is not None else time.time()*1000),
                window_seconds=window_seconds, hop_seconds=hop_seconds,
                inference_ms=round(float(inference_ms), 1), level_dbfs=level_dbfs(window_rms),
                top=[dict(label=label, score=round(float(score), 4)) for label, score in top],
                rules=rules, custom=custom,
                emitted=[dict(event_id=e['event_id'], type=e['type'], label=e['label']) for e in events])

def _score(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f'{name} must be a finite number within 0..1')

def _text(value, name, limit=120):
    if not isinstance(value, str) or not 0 < len(value) <= limit:
        raise ValueError(f'invalid {name}')

def validate_observation(obs):
    if not isinstance(obs, dict) or obs.get('kind') != 'observation':
        raise ValueError('expected an observation')
    if obs.get('schema_version') != SCHEMA_VERSION:
        raise ValueError(f'expected schema_version {SCHEMA_VERSION}')
    if obs.get('source') not in SOURCES:
        raise ValueError(f'source must be one of {sorted(SOURCES)}')
    _text(obs.get('model'), 'model', 40)
    if type(obs.get('timestamp_ms')) is not int or obs['timestamp_ms'] < 0:
        raise ValueError('timestamp_ms must be a nonnegative integer')
    for key in ('inference_ms', 'level_dbfs', 'window_seconds', 'hop_seconds'):
        if type(obs.get(key)) not in (int, float) or not math.isfinite(obs[key]):
            raise ValueError(f'{key} must be a finite number')
    top = obs.get('top')
    if not isinstance(top, list) or len(top) > MAX_TOP_K:
        raise ValueError(f'top must be a list of at most {MAX_TOP_K}')
    for item in top:
        if not isinstance(item, dict):
            raise ValueError('invalid top entry')
        _text(item.get('label'), 'top label')
        _score(item.get('score'), 'top score')
    rules = obs.get('rules')
    if not isinstance(rules, dict) or len(rules) > 50:
        raise ValueError('rules must be an object')
    for kind, rule in rules.items():
        _text(kind, 'rule type', 40)
        if not isinstance(rule, dict):
            raise ValueError('invalid rule entry')
        _score(rule.get('score'), 'rule score')
        _text(rule.get('reason'), 'rule reason', 40)
    for key, item_keys in (('custom', ('id', 'label', 'reason')), ('emitted', ('event_id', 'type', 'label'))):
        items = obs.get(key)
        if not isinstance(items, list) or len(items) > 50:
            raise ValueError(f'{key} must be a list')
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f'invalid {key} entry')
            for item_key in item_keys:
                _text(item.get(item_key), f'{key} {item_key}')
            if key == 'custom':
                _score(item.get('score'), 'custom score')
                for optional in ('matched_label', 'match_kind'):
                    if optional in item:
                        _text(item[optional], f'custom {optional}')
    return obs

class ObservationPublisher:
    """Posts observations from a background thread so a slow or stopped server never stalls audio.
    Keeps at most a few pending; when behind, the oldest are dropped (observations are a live view)."""
    def __init__(self, url, max_pending=8, timeout=1.0):
        self.url, self.timeout = url, timeout
        self.pending = queue.Queue(maxsize=max_pending)
        self.sent = self.failed = self.dropped = 0
        self.failing = False
        threading.Thread(target=self._run, daemon=True).start()

    def publish(self, observation):
        try:
            self.pending.put_nowait(observation)
        except queue.Full:
            try:
                self.pending.get_nowait()
                self.dropped += 1
            except queue.Empty:
                pass
            self.pending.put_nowait(observation)

    def _run(self):
        while True:
            observation = self.pending.get()
            payload = json.dumps(observation, allow_nan=False).encode()
            try:
                with urlopen(Request(self.url, data=payload, headers={'Content-Type': 'application/json'}),
                             timeout=self.timeout) as response:
                    response.read()
                self.sent += 1
                if self.failing:
                    print('Observation stream reconnected', file=sys.stderr)
                self.failing = False
            except Exception as exc:
                self.failed += 1
                if not self.failing:   # report once per outage, not every second
                    print(f'Observation delivery failed ({exc}); will keep retrying', file=sys.stderr)
                self.failing = True

    def flush(self, timeout=3.0):
        deadline = time.monotonic()+timeout
        while not self.pending.empty() and time.monotonic() < deadline:
            time.sleep(0.05)
        time.sleep(0.1)
