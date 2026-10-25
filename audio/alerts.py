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
GESTURES = frozenset({'thumbs_up', 'finger_snap'})  # wearer input, never an alert
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
    categories = prefs.get('category_tiers', {})
    if not isinstance(categories, dict) or any(k not in POLICY['categories'] or type(v) is not int or not 0 <= v <= 4 for k,v in categories.items()):
        raise ValueError('Invalid category_tiers')
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
    requests = value.get('custom_sound_requests', [])
    if not isinstance(requests, list) or len(requests) > 100:
        raise ValueError('custom_sound_requests must contain at most 100 requests')
    from audio.custom_rules import LABEL_ICONS
    from audio.cue_catalog import selected_cue
    custom, seen, seen_ids = [], set(), set()
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError('Invalid custom sound request')
        label = request.get('label')
        request_id = request.get('id')
        tier = request.get('tier')
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise ValueError('Custom sound label must be 1..80 characters')
        if not isinstance(request_id, str) or not 0 < len(request_id) <= 120:
            raise ValueError('Invalid custom sound request id')
        status = request.get('status')
        if type(tier) is not int or not 0 <= tier <= 4 or status not in ('pending', 'recognized'):
            raise ValueError('Custom sound must have a valid tier and status')
        if request_id in seen_ids:
            raise ValueError('Duplicate custom sound id')
        seen_ids.add(request_id)
        key = ' '.join(label.split()).casefold()
        if key in seen:
            raise ValueError('Duplicate custom sound label')
        seen.add(key)
        entry = dict(id=request_id, label=' '.join(label.split()), tier=tier, status=status)
        if status == 'recognized':
            labels = request.get('model_labels')
            if not isinstance(labels, list) or not 1 <= len(labels) <= 4 or not all(
                    isinstance(label, str) and label in LABEL_ICONS for label in labels):
                raise ValueError('Recognized sounds need 1..4 exact catalog labels')
            from audio.custom_rules import DEFAULT_THRESHOLD
            threshold = request.get('threshold', DEFAULT_THRESHOLD)
            if type(threshold) not in (int, float) or not 0 < threshold <= 1:
                raise ValueError('Custom threshold must be greater than 0 and at most 1')
            cue = selected_cue(request)
            icon = cue['icon_id'] if cue else LABEL_ICONS[labels[0]]
            entry.update(model_labels=list(dict.fromkeys(labels)), icon=icon, icon_id=icon, threshold=threshold)
            if cue:
                entry['cue_id'] = cue['id']
        custom.append(entry)
    display = value.get('display', {})
    if not isinstance(display, dict) or not isinstance(display.get('labels', False), bool):
        raise ValueError('display.labels must be true or false')
    return dict(schema_version=1, profile_id=str(value.get('profile_id', 'local'))[:64],
                revision=0, custom_sound_requests=custom, display_name=str(value.get('display_name', ''))[:60],
                name_detection=dict(enabled=bool(names.get('enabled', False)), primary_name=primary,
                                    aliases=list(aliases), language=str(names.get('language', 'en'))[:12],
                                    **name_extras(names)),
                notification_preferences=dict(mode=prefs['mode'], event_tiers=dict(tiers), category_tiers=dict(categories)),
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


def name_extras(names):
    """John's name spotter settings (audio/names.py): kept when valid so saving preferences never drops them."""
    extras = {}
    if names.get('sensitivity') in ('low', 'balanced', 'high'):
        extras['sensitivity'] = names['sensitivity']
    if isinstance(names.get('attention_calls'), bool):
        extras['attention_calls'] = names['attention_calls']
    learned = names.get('learned_spellings')
    if isinstance(learned, list) and len(learned) <= 8 and all(isinstance(x, (str, dict)) for x in learned):
        extras['learned_spellings'] = learned
    return extras


def sound_key(event):
    """Which sound an event is, for repeats, acknowledgements and the queue. Each taught custom sound
    is its own sound; every built-in type is one sound."""
    if event['type'] == 'custom':
        return 'custom:' + str(event.get('custom_sound_id'))
    return event['type']


def effective_tier(kind, producer_tier, profile, event=None):
    """Explicit override, then the selected preset, then the producer's legacy default."""
    if kind == 'name_called' and event and str(event.get('matched_alias_id', '')).startswith('warning-'):
        return 4   # "watch out" / "look out" is a warning, not a chat
    if kind == 'custom' and event:
        chosen = next((r for r in profile.get('custom_sound_requests', []) if r['id'] == event.get('custom_sound_id')), None)
        if chosen:
            return chosen['tier']
    prefs = profile['notification_preferences']
    if kind in prefs['event_tiers']:
        return prefs['event_tiers'][kind]
    category = POLICY['event_categories'].get(kind)
    if category in prefs.get('category_tiers', {}):
        return prefs['category_tiers'][category]
    return POLICY['presets'][prefs['mode']].get(kind, producer_tier)


class AlertEngine:
    def __init__(self, profile=None, session_id=None, on_decision=None):
        self.on_decision = on_decision
        self.session_id = session_id or uuid.uuid4().hex
        self.profile = profile or json.loads(json.dumps(DEFAULT_PROFILE))
        self.focus_mode = 'everyday'
        self.paused = False
        self.repeat_suppression = True
        self.snap_to_dismiss = False
        self.sequence = 0
        self.active = None  # dict(event, tier, started, expires, repeats)
        self.queue = []
        self.acks = {}
        self.gestures = []        # recent dismiss-gesture times while a cue is showing
        self.confirm = None       # brief check mark after the wearer resolves a cue
        self.seen = deque(maxlen=256)
        self.events = deque(maxlen=50)
        self.decisions = deque(maxlen=50)

    # -- internal helpers -------------------------------------------------------------
    def _decide(self, event, tier, reason, now, **extra):
        decision = dict(kind='alert_state', event_id=event['event_id'], type=event['type'],
                        priority_tier=tier, reason=reason, at_ms=round(now),
                        active_type=self.active['event']['type'] if self.active else None,
                        repeat_suppression=self.repeat_suppression,
                        label=event.get('label'),   # custom sounds are named by the user, not the type
                        active_label=self.active['event'].get('label') if self.active else None)
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

    def _bound_queue(self, now):
        while len(self.queue) > POLICY['queue_limit']:
            dropped = min(self.queue, key=lambda item: (item['tier'], item['received']))
            self.queue.remove(dropped)
            self._decide(dropped['event'], dropped['tier'], 'dropped_queue_full', now)

    def _blocked_by_focus(self, tier):
        return tier < POLICY['focus_minimum_tier'][self.focus_mode]

    # -- public API ------------------------------------------------------------------
    def _resolve(self, now, reason, **extra):
        """The wearer dealt with the cue: acknowledge its sound, confirm with a check, then resume."""
        shown = self.active['event']
        self.acks[sound_key(shown)] = now + POLICY['acknowledge_hold_ms']
        decision = self._decide(shown, self.active['tier'], reason, now, **extra)
        self.confirm = dict(until=now + POLICY['confirm_ms'], direction=self.active['direction'],
                            event_id=shown['event_id'])
        self.gestures = []
        self._clear()
        self.tick(now)
        return decision

    def _gesture(self, event, now):
        """A thumbs-up (camera) or snap dismisses the showing cue; with nothing showing it does nothing."""
        if self.active is None or (event.get('target_event_id') is not None and event['target_event_id'] != self.active['event']['event_id']):
            return self._decide(event, 0, 'gesture_ignored', now, gesture=event['type'])
        rule = POLICY['gesture_to_dismiss']
        self.gestures = [t for t in self.gestures if now - t <= rule['window_ms']] + [now]
        if len(self.gestures) < rule['count']:
            return self._decide(event, 0, 'gesture_waiting', now, gesture=event['type'])
        return self._resolve(now, 'dismissed_gesture', gesture=event['type'])

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
            return self._gesture(event, now)
        producer = event['priority_tier']
        tier = effective_tier(event['type'], producer, self.profile, event)
        logged = dict(event, priority_tier=tier, producer_tier=producer)
        self.events.append(logged)
        kind = sound_key(event)
        if self.paused:
            return self._decide(logged, tier, 'paused', now)
        if tier == 0:
            return self._decide(logged, tier, 'ignored_tier_zero', now)
        if self._blocked_by_focus(tier):
            return self._decide(logged, tier, f'held_{self.focus_mode}_mode', now)
        if self.repeat_suppression and now < self.acks.get(kind, -1):
            # An acknowledged sound that keeps going stays acknowledged while it continues.
            self.acks[kind] = now + POLICY['acknowledge_hold_ms']
            return self._decide(logged, tier, 'acknowledged_repeat', now)
        active = self.active
        if self.repeat_suppression and active and sound_key(active['event']) == kind and tier <= active['tier']:
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
            self.queue = [item for item in self.queue if sound_key(item['event']) != kind]
            if active and active['tier'] in (2, 3) and sound_key(active['event']) != kind:
                # The interrupted cue may resume afterwards, but only while it is still fresh.
                self.queue.append(dict(event=active['event'], tier=active['tier'], received=active['started']))
            self._bound_queue(now)
            self._show(logged, tier, now)
            return self._decide(logged, tier, reason, now,
                                active_type=active['event']['type'] if active else None,
                                active_label=active['event'].get('label') if active else None)
        if tier == 1:
            return self._decide(logged, tier, 'suppressed_lower_priority', now)
        self.queue = [item for item in self.queue if sound_key(item['event']) != kind]
        self.queue.append(dict(event=logged, tier=tier, received=now))
        self._bound_queue(now)
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

    def observe_sound(self, kind, present, source, now):
        """Clear an ongoing alarm only on continued negative evidence from its own capture source.

        No observation (capture disconnected) is not evidence of quiet. A new beep resets the hold.
        """
        self.tick(now)
        active = self.active
        hold = POLICY.get('ongoing_sound_quiet_ms', {}).get(kind)
        if not hold or not active or active['event']['type'] != kind or active['event']['source'] != source:
            return
        if present:
            active.pop('quiet_since', None)
            return
        previous = active.get('quiet_last')
        if previous is not None and (now < previous or now - previous > 2000):
            active.pop('quiet_since', None)
        active['quiet_last'] = now
        active.setdefault('quiet_since', now)
        if now - active['quiet_since'] >= hold:
            self._decide(active['event'], active['tier'], 'sound_stopped', now)
            self._clear()
            self.tick(now)

    def set_controls(self, now, focus_mode=None, paused=None, repeat_suppression=None, snap_to_dismiss=None):
        # Validate the whole request before applying any part.
        if focus_mode is not None and focus_mode not in FOCUS_MODES:
            raise ValueError(f'focus_mode must be one of {", ".join(FOCUS_MODES)}')
        if paused is not None and not isinstance(paused, bool):
            raise ValueError('paused must be true or false')
        if snap_to_dismiss is not None and not isinstance(snap_to_dismiss, bool):
            raise ValueError('snap_to_dismiss must be true or false')
        if repeat_suppression is not None and not isinstance(repeat_suppression, bool):
            raise ValueError('repeat_suppression must be true or false')
        self.tick(now)
        if snap_to_dismiss is not None:
            self.snap_to_dismiss = snap_to_dismiss
        if repeat_suppression is not None:
            self.repeat_suppression = repeat_suppression
            self.acks.clear()
            self.confirm = None
        if focus_mode is not None:
            self.focus_mode = focus_mode
        if paused is not None:
            self.paused = paused
        if self.paused:
            self.queue = []
            if self.confirm:
                self.confirm = None
                self.sequence += 1
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
                    icon_id=event.get('icon_id') or POLICY['icons'].get(event['type']), effective_tier=active['tier'],
                    remaining_ms=self.remaining_ms(now), direction=active['direction'],
                    bearing_degrees=event.get('direction_degrees') if active['direction'] is not None else None,
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
            focus_mode=self.focus_mode, paused=self.paused, repeat_suppression=self.repeat_suppression, snap_to_dismiss=self.snap_to_dismiss,
            queue=[dict(event_id=i['event']['event_id'], type=i['event']['type'], tier=i['tier'])
                   for i in self.queue],
            profile_revision=self.profile['revision'],
            preset=self.profile['notification_preferences']['mode'],
        )
