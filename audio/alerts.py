"""Authoritative notification engine: profile -> effective tier -> one active cue.

Browser views and the glasses only render what this engine decides. The browser simulator
uses a line-for-line port (frontend/src/lib/alerts.ts); both run audio/alert-scenarios.json.
Times are monotonic milliseconds supplied by the caller so tests and replays are deterministic.
"""
from collections import deque
import json
from pathlib import Path
import uuid

POLICY = json.loads(Path(__file__).with_name('alert-policy.json').read_text())
FOCUS_MODES = tuple(POLICY['focus_minimum_tier'])
GESTURES = frozenset({'finger_snap'})  # control input from the wearer, never an alert
PRESETS = tuple(POLICY['presets'])
DEFAULT_PROFILE = dict(schema_version=1, profile_id='local', revision=0, display_name='',
                       name_detection=dict(enabled=False, primary_name='', aliases=[], language='en'),
                       notification_preferences=dict(mode='balanced', event_tiers={}),
                       display=dict(labels=False))


def validate_profile(value, known_types):
    """Return a normalized copy. Only fields the engine uses are interpreted; names are carried."""
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Expected profile schema_version 1')
    prefs = value.get('notification_preferences')
    if not isinstance(prefs, dict) or prefs.get('mode') not in PRESETS:
        raise ValueError(f'notification_preferences.mode must be one of {", ".join(PRESETS)}')
    tiers = prefs.get('event_tiers', {})
    if not isinstance(tiers, dict):
        raise ValueError('event_tiers must be an object')
    for kind, tier in tiers.items():
        if kind not in known_types:
            raise ValueError(f'Unknown sound in event_tiers: {kind}')
        if type(tier) is not int or not 0 <= tier <= 4:
            raise ValueError(f'Tier for {kind} must be 0..4')
    names = value.get('name_detection', DEFAULT_PROFILE['name_detection'])
    if not isinstance(names, dict):
        raise ValueError('name_detection must be an object')
    primary = names.get('primary_name', '')
    aliases = names.get('aliases', [])
    if not isinstance(primary, str) or len(primary) > 60:
        raise ValueError('primary_name must be at most 60 characters')
    if not isinstance(aliases, list) or len(aliases) > 8 or not all(
            isinstance(a, str) and 0 < len(a) <= 60 for a in aliases):
        raise ValueError('aliases must be up to 8 short strings')
    display = value.get('display', {})
    if not isinstance(display, dict) or not isinstance(display.get('labels', False), bool):
        raise ValueError('display.labels must be true or false')
    return dict(schema_version=1, profile_id=str(value.get('profile_id', 'local'))[:64],
                revision=0, display_name=str(value.get('display_name', ''))[:60],
                name_detection=dict(enabled=bool(names.get('enabled', False)), primary_name=primary,
                                    aliases=list(aliases), language=str(names.get('language', 'en'))[:12]),
                notification_preferences=dict(mode=prefs['mode'], event_tiers=dict(tiers)),
                display=dict(labels=display.get('labels', False)))


DIRECTIONS = ('front', 'right', 'behind', 'left')


def direction_bucket(degrees, confidence):
    """Which edge of the display the cue sits on, or None when unmeasured or not confident.

    0 front, +90 right, -90 left, 180 behind, each covering 90 degrees. A two-microphone array
    cannot tell front from behind; such a worker should send null rather than guess.
    """
    if degrees is None or confidence is None or confidence < POLICY['direction_min_confidence']:
        return None
    d = (degrees + 180) % 360 - 180
    if -45 <= d <= 45:
        return 'front'
    if 45 < d <= 135:
        return 'right'
    if -135 <= d < -45:
        return 'left'
    return 'behind'


def effective_tier(kind, producer_tier, profile):
    """Explicit override, then the selected preset, then the producer's legacy default."""
    prefs = profile['notification_preferences']
    if kind in prefs['event_tiers']:
        return prefs['event_tiers'][kind]
    return POLICY['presets'][prefs['mode']].get(kind, producer_tier)


class AlertEngine:
    def __init__(self, profile=None, session_id=None, on_decision=None):
        self.on_decision = on_decision
        self.session_id = session_id or uuid.uuid4().hex
        self.profile = profile or json.loads(json.dumps(DEFAULT_PROFILE))
        self.focus_mode = 'everyday'
        self.paused = False
        self.sequence = 0
        self.active = None  # dict(event, tier, started, expires, repeats)
        self.queue = []
        self.acks = {}
        self.snaps = []           # recent snap times while a cue is showing
        self.confirm = None       # brief check mark after the wearer resolves a cue
        self.seen = deque(maxlen=256)
        self.events = deque(maxlen=50)
        self.decisions = deque(maxlen=50)

    # -- internal helpers -------------------------------------------------------------
    def _decide(self, event, tier, reason, now, **extra):
        decision = dict(kind='alert_state', event_id=event['event_id'], type=event['type'],
                        priority_tier=tier, reason=reason, at_ms=round(now),
                        active_type=self.active['event']['type'] if self.active else None)
        decision.update(extra)
        self.decisions.append(decision)
        if self.on_decision:
            self.on_decision(decision)
        return decision

    def _show(self, event, tier, now):
        self.active = dict(event=event, tier=tier, started=now,
                           expires=now + POLICY['lifetime_ms'][str(tier)], repeats=0,
                           direction=direction_bucket(event.get('direction_degrees'),
                                                      event.get('direction_confidence')))
        self.sequence += 1

    def _clear(self):
        if self.active is not None:
            self.active = None
            self.sequence += 1

    def _fresh_queue(self, now):
        kept = []
        for item in self.queue:
            if now - item['received'] > POLICY['queue_fresh_ms']:
                self._decide(item['event'], item['tier'], 'expired_in_queue', now)
            else:
                kept.append(item)
        self.queue = kept

    def _blocked_by_focus(self, tier):
        return tier < POLICY['focus_minimum_tier'][self.focus_mode]

    # -- public API ------------------------------------------------------------------
    def _resolve(self, now, reason, **extra):
        """The wearer dealt with the cue: acknowledge its sound, confirm with a check, then resume."""
        shown = self.active['event']
        self.acks[shown['type']] = now + POLICY['acknowledge_hold_ms']
        decision = self._decide(shown, self.active['tier'], reason, now, **extra)
        self.confirm = dict(until=now + POLICY['confirm_ms'], direction=self.active['direction'],
                            event_id=shown['event_id'])
        self.snaps = []
        self._clear()
        self.tick(now)
        return decision

    def _snap(self, event, now):
        if self.active is None:
            return self._decide(event, 0, 'snap_ignored', now)
        window = POLICY['snap_to_dismiss']['window_ms']
        self.snaps = [t for t in self.snaps if now - t <= window] + [now]
        if len(self.snaps) < POLICY['snap_to_dismiss']['snaps']:
            return self._decide(event, 0, 'snap_waiting', now)
        return self._resolve(now, 'dismissed_snap')

    def tick(self, now):
        """Expire the active cue and resume the best fresh queued cue. Call before reading."""
        if self.active and now >= self.active['expires']:
            self._decide(self.active['event'], self.active['tier'], 'expired', now)
            self._clear()
        if self.confirm and now >= self.confirm['until']:
            self.confirm = None
            self.sequence += 1
        self._fresh_queue(now)
        if self.active is None and self.queue and self.confirm is None:
            best = max(self.queue, key=lambda item: (item['tier'], item['received']))
            self.queue.remove(best)
            self._show(best['event'], best['tier'], now)
            self._decide(best['event'], best['tier'], 'resumed_from_queue', now)

    def add(self, event, now):
        self.tick(now)
        if event['event_id'] in self.seen:
            return self._decide(event, event['priority_tier'], 'duplicate', now)
        self.seen.append(event['event_id'])
        if event['type'] in GESTURES:
            return self._snap(event, now)
        producer = event['priority_tier']
        tier = effective_tier(event['type'], producer, self.profile)
        logged = dict(event, priority_tier=tier, producer_tier=producer)
        self.events.append(logged)
        kind = event['type']
        if self.paused:
            return self._decide(logged, tier, 'paused', now)
        if tier == 0:
            return self._decide(logged, tier, 'ignored_tier_zero', now)
        if self._blocked_by_focus(tier):
            return self._decide(logged, tier, f'held_{self.focus_mode}_mode', now)
        if now < self.acks.get(kind, -1):
            # An acknowledged sound that keeps going stays acknowledged while it continues.
            self.acks[kind] = now + POLICY['acknowledge_hold_ms']
            return self._decide(logged, tier, 'acknowledged_repeat', now)
        active = self.active
        if active and active['event']['type'] == kind and tier <= active['tier']:
            # Same ongoing sound: keep the original cue, no new animation or lifetime restart.
            active['repeats'] += 1
            if active['tier'] == 4:
                cap = active['started'] + POLICY['urgent_ongoing_cap_ms']
                extended = min(cap, max(active['expires'], now + POLICY['lifetime_ms']['4']))
                if extended > active['expires']:
                    active['expires'] = extended
                    self.sequence += 1  # displays only follow a lifetime change on a new sequence
            return self._decide(logged, tier, 'merged_repeat', now, shown_event_id=active['event']['event_id'])
        if active is None or tier >= active['tier']:
            reason = 'displayed' if active is None else 'interrupted'
            self.queue = [item for item in self.queue if item['event']['type'] != kind]
            if active and active['tier'] in (2, 3) and active['event']['type'] != kind:
                # The interrupted cue may resume afterwards, but only while it is still fresh.
                self.queue.append(dict(event=active['event'], tier=active['tier'], received=active['started']))
            self._show(logged, tier, now)
            return self._decide(logged, tier, reason, now,
                                active_type=active['event']['type'] if active else None)
        if tier == 1:
            return self._decide(logged, tier, 'suppressed_lower_priority', now)
        self.queue = [item for item in self.queue if item['event']['type'] != kind]
        self.queue.append(dict(event=logged, tier=tier, received=now))
        if len(self.queue) > POLICY['queue_limit']:
            dropped = min(self.queue, key=lambda item: (item['tier'], item['received']))
            self.queue.remove(dropped)
            self._decide(dropped['event'], dropped['tier'], 'dropped_queue_full', now)
        return self._decide(logged, tier, 'queued', now)

    def dismiss(self, now, event_id=None):
        """Acknowledge the current cue. A stale click naming an older event changes nothing."""
        self.tick(now)
        if self.active is None:
            return False
        shown = self.active['event']
        if event_id is not None and event_id != shown['event_id']:
            return False
        self._resolve(now, 'dismissed')
        return True

    def look(self, now, direction):
        """The wearer turned toward the sound: the cue is resolved, like a dismiss.

        `direction` comes from a head-orientation source (none in the current hardware) or a
        simulated control. Only a cue with a measured direction can be resolved this way.
        """
        if direction not in DIRECTIONS:
            raise ValueError(f'direction must be one of {", ".join(DIRECTIONS)}')
        self.tick(now)
        if self.active is None or self.active['direction'] != direction:
            return False
        self._resolve(now, 'resolved_looked', direction=direction)
        return True

    def set_controls(self, now, focus_mode=None, paused=None):
        self.tick(now)
        if focus_mode is not None:
            if focus_mode not in FOCUS_MODES:
                raise ValueError(f'focus_mode must be one of {", ".join(FOCUS_MODES)}')
            self.focus_mode = focus_mode
        if paused is not None:
            if not isinstance(paused, bool):
                raise ValueError('paused must be true or false')
            self.paused = paused
        if self.paused:
            self.queue = []
            self._clear()
            return
        self.queue = [item for item in self.queue if not self._blocked_by_focus(item['tier'])]
        if self.active and self._blocked_by_focus(self.active['tier']):
            self._clear()
            self.tick(now)

    def set_profile(self, profile):
        """Applies to the next detections; the visible cue is not rewritten retroactively."""
        profile = dict(profile, revision=self.profile['revision'] + 1)
        self.profile = profile
        return profile

    def remaining_ms(self, now):
        return max(0, round(self.active['expires'] - now)) if self.active else 0

    def presentation(self, now):
        """Display-consumer envelope parsed by hardware.display.Presentation."""
        self.tick(now)
        active = self.active
        if active is None and self.confirm:
            return dict(schema_version=1, session_id=self.session_id, state_sequence=self.sequence,
                        event_id='resolved-' + self.confirm['event_id'], label='Done', icon_id='check',
                        effective_tier=1, remaining_ms=max(1, round(self.confirm['until'] - now)),
                        direction=self.confirm['direction'], show_labels=False)
        if active is None:
            return dict(schema_version=1, session_id=self.session_id, state_sequence=self.sequence,
                        event_id=None, label='', icon_id=None, effective_tier=0, remaining_ms=0,
                        direction=None, show_labels=self.profile['display']['labels'])
        event = active['event']
        return dict(schema_version=1, session_id=self.session_id, state_sequence=self.sequence,
                    event_id=event['event_id'], label=event['label'],
                    icon_id=POLICY['icons'].get(event['type']), effective_tier=active['tier'],
                    remaining_ms=self.remaining_ms(now), direction=active['direction'],
                    show_labels=self.profile['display']['labels'],
                    age_ms=round(now - active['started']), repeats=active['repeats'])

    def snapshot(self, now):
        self.tick(now)
        return dict(
            active=self.active['event'] if self.active else None,
            events=list(self.events), decisions=list(self.decisions),
            session_id=self.session_id, state_sequence=self.sequence,
            remaining_ms=self.remaining_ms(now), direction=self.active['direction'] if self.active else None,
            confirm=dict(direction=self.confirm['direction'], remaining_ms=round(self.confirm['until'] - now))
            if self.confirm else None,
            focus_mode=self.focus_mode, paused=self.paused,
            queue=[dict(event_id=i['event']['event_id'], type=i['event']['type'], tier=i['tier'])
                   for i in self.queue],
            profile_revision=self.profile['revision'],
            preset=self.profile['notification_preferences']['mode'],
        )
