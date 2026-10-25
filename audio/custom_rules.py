"""Alert on any sound the model already knows, chosen by the person in Preferences.

Recognized custom sounds live in the shared profile (.cache/profile.json, written by the receiver's
PUT /profile) as custom_sound_requests entries with status "recognized" and the model labels they map
to (audio/sound-catalog.json). This reloads the profile within ~2 s of a change, so a sound picked in
Preferences starts alerting without restarting anything, and emits John's custom event shape
(type "custom", custom_sound_id, the person's own label) plus the category icon for the glasses.
"""
import json
import math
import time
import uuid
from pathlib import Path
from audio.cue_catalog import selected_cue

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / '.cache' / 'profile.json'
CATALOG = json.loads(Path(__file__).with_name('sound-catalog.json').read_text())['sounds']
LABEL_ICONS = {s['label']: s['icon'] for s in CATALOG}
DEFAULT_THRESHOLD = 0.25   # untuned for most classes: tighten per sound with the signal panel
COOLDOWN_SECONDS = 5
RELOAD_SECONDS = 2


class CustomRules:
    def __init__(self, profile_path=PROFILE):
        self.path = Path(profile_path)
        self.rules = []
        self.last = {}
        self.decisions = []
        self._mtime = None
        self._checked = -math.inf
        self.reload(force=True)

    def reload(self, force=False):
        now = time.monotonic()
        if not force and now - self._checked < RELOAD_SECONDS:
            return
        self._checked = now
        try:
            mtime = self.path.stat().st_mtime
            if not force and mtime == self._mtime:
                return
            self._mtime = mtime
            requests = json.loads(self.path.read_text()).get('custom_sound_requests', [])
        except (OSError, ValueError):
            requests = []
        requests = requests if isinstance(requests, list) else []
        requests = [r for r in requests if isinstance(r, dict) and isinstance(r.get('id'), str)
                    and isinstance(r.get('label'), str) and type(r.get('tier')) is int
                    and 0 <= r['tier'] <= 4 and isinstance(r.get('model_labels', []), list)
                    and type(r.get('threshold', DEFAULT_THRESHOLD)) in (int, float)
                    and math.isfinite(r.get('threshold', DEFAULT_THRESHOLD))
                    and 0 < r.get('threshold', DEFAULT_THRESHOLD) <= 1]
        self.rules = []
        for r in requests:
            if r.get('status') != 'recognized':
                continue
            try:
                cue = selected_cue(r)
            except ValueError:
                continue  # A hand-edited/stale group cannot silently change what a cue means.
            labels = [l for l in r.get('model_labels', []) if isinstance(l, str) and l in LABEL_ICONS]
            if not labels:
                continue
            self.rules.append(dict(id=r['id'], label=r['label'], tier=r['tier'], labels=labels,
                icon=cue['icon_id'] if cue else LABEL_ICONS[labels[0]],
                threshold=float(r.get('threshold', DEFAULT_THRESHOLD))))

    def detect(self, scores, source, now=None, timestamp_ms=None):
        """Events for picked sounds in this window; decisions are kept for the signal panel."""
        self.reload()
        now = time.monotonic() if now is None else now
        events, self.decisions = [], []
        for rule in self.rules:
            score = max(float(scores.get(label, 0)) for label in rule['labels'])
            decision = dict(type='custom', custom_sound_id=rule['id'], raw_score=score,
                            threshold=rule['threshold'], reason='below_threshold')
            if score >= rule['threshold']:
                if getattr(self, 'repeat_suppression', True) and now - self.last.get(rule['id'], -math.inf) < COOLDOWN_SECONDS:
                    decision['reason'] = 'cooldown'
                else:
                    self.last[rule['id']] = now
                    decision['reason'] = 'emitted'
                    events.append(dict(
                        schema_version=1, event_id=str(uuid.uuid4()), type='custom',
                        custom_sound_id=rule['id'], label=rule['label'], icon_id=rule['icon'],
                        confidence=round(score, 4), source=source, priority_tier=rule['tier'],
                        timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
                        direction_degrees=None, direction_confidence=None, distance_meters=None,
                        proximity='unknown'))
            self.decisions.append(decision)
        return events
