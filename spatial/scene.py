"""Simulated sound map: true sound positions, head yaw, and what the mics estimate.

Everything here is a simulation. Sound positions come from map clicks or are picked at
random for events from the audio program (which has no direction yet). Mic signals are
synthesized from the geometry in frame_geometry.json and then localized for real.
"""
import math
import threading
import time
from collections import deque

import numpy as np

from audio.events import TARGETS
from spatial.front_back import FrontBackResolver
from spatial.geometry import bearing_deg, load_geometry, microphones, mic_positions, world_to_head, wrap180
from spatial.localize import localize
from spatial.simulate import SAMPLE_RATE, SOUNDING_SECONDS, render, source_signal

MAX_SOURCES = 10
KEEP_AFTER_SOUNDING_SECONDS = 20
MAP_RADIUS_M = 6.0
TICK_SECONDS = 0.1          # one mic reading per sounding source per tick
YAW_HISTORY_SECONDS = 6
OBSERVATION_SECONDS = 0.12  # length of each simulated mic window

# Natural head yaw as a sum of sways: (amplitude degrees, frequency Hz, phase radians).
# Walking: the head yaws about +/-2.5 degrees once per stride, with a little faster jitter.
HEAD_MOTION = {
    'still': (),
    'walking': ((2.5, 0.9, 0.0), (0.6, 2.3, 1.1)),
    'looking': ((12.0, 0.15, 0.0), (3.0, 0.4, 0.7)),
}


class Scene:
    def __init__(self, geometry=None, rng=None, clock=time.monotonic):
        self.geometry = geometry or load_geometry()
        self.rng = np.random.default_rng() if rng is None else rng
        self.clock = clock
        self.lock = threading.RLock()
        self.sources = []
        self.base_yaw = 0.0   # where the wearer means to face (turn buttons)
        self.yaw = 0.0        # base plus natural sway: what the IMU would report
        self.motion = 'still'
        self.motion_started = clock()
        self.yaw_history = deque(maxlen=int(YAW_HISTORY_SECONDS / TICK_SECONDS))
        self.mic_count = 2
        self.snr_db = 15.0
        self.next_id = 1
        self.audio = dict(url=None, status='off')

    # Inputs -------------------------------------------------------------
    def add(self, kind, x=None, y=None, origin='map', label=None, event_id=None):
        if kind not in TARGETS:
            raise ValueError(f'Unknown sound type: {kind}')
        with self.lock:
            if x is None or y is None:
                bearing = self.rng.uniform(-180, 180)
                distance = self.rng.uniform(1.5, 5.0)
                x, y = distance * math.sin(math.radians(bearing)), distance * math.cos(math.radians(bearing))
            x, y = float(x), float(y)
            distance = math.hypot(x, y)
            if not 0.5 <= distance <= MAP_RADIUS_M:
                raise ValueError('Place sounds between 0.5 m and 6 m from the wearer')
            now = self.clock()
            source = dict(id=self.next_id, type=kind, label=label or TARGETS[kind][1], origin=origin,
                          event_id=event_id, x=round(x, 3), y=round(y, 3),
                          bearing=round(bearing_deg(x, y), 1), distance=round(distance, 2),
                          started=now, sounding_until=now + SOUNDING_SECONDS.get(kind, 2),
                          resolver=FrontBackResolver(), estimate=None)
            self.next_id += 1
            self._estimate(source)
            self.sources.append(source)
            del self.sources[:-MAX_SOURCES]
            return self._public(source, now)

    def turn(self, delta=None, yaw=None):
        with self.lock:
            self.base_yaw = wrap180(float(yaw) if yaw is not None else self.base_yaw + float(delta))
            self._update_yaw()
            self._reestimate_sounding()

    def set_motion(self, mode):
        if mode not in HEAD_MOTION:
            raise ValueError(f'Head motion must be one of: {", ".join(HEAD_MOTION)}')
        with self.lock:
            self.motion = mode
            self.motion_started = self.clock()
            self._update_yaw()

    def tick(self):
        """Advance natural head motion and take one mic reading of every sound still playing."""
        with self.lock:
            self._update_yaw()
            self.yaw_history.append(round(self.yaw, 2))
            self._reestimate_sounding()

    def set_mic_count(self, count):
        if count not in (2, 3):
            raise ValueError('Microphone count must be 2 or 3')
        with self.lock:
            self.mic_count = count
            for source in self.sources:
                source['resolver'] = FrontBackResolver()
            self._reestimate_sounding()

    def set_noise(self, snr_db):
        snr_db = float(snr_db)
        if not -10 <= snr_db <= 60:
            raise ValueError('snr_db must be between -10 and 60')
        with self.lock:
            self.snr_db = snr_db

    def clear(self):
        with self.lock:
            self.sources.clear()

    # Estimation ---------------------------------------------------------
    def _update_yaw(self):
        t = self.clock() - self.motion_started
        sway = sum(a * math.sin(2 * math.pi * f * t + p) for a, f, p in HEAD_MOTION[self.motion])
        self.yaw = wrap180(self.base_yaw + sway)

    def _mics(self):
        return mic_positions(self.geometry, include_bridge=self.mic_count == 3)

    def _reestimate_sounding(self):
        now = self.clock()
        for source in self.sources:
            if now < source['sounding_until']:
                self._estimate(source)

    def _estimate(self, source):
        ids, mic_xy = self._mics()
        head_xy = world_to_head((source['x'], source['y']), self.yaw)
        channels = render(head_xy, mic_xy, source_signal(source['type'], duration=OBSERVATION_SECONDS, rng=self.rng),
                          snr_db=self.snr_db, rng=self.rng)
        result = localize(channels, SAMPLE_RATE, mic_xy, ids)
        candidates = result['candidates']
        resolver = source['resolver']
        if result['ambiguous']:
            front_back = resolver.update(self.yaw, result['lateral_deg'])
            chosen = {'front': candidates[:1], 'back': candidates[1:]}.get(front_back, candidates)
            decided_by = 'head motion' if front_back != 'unknown' else None
        else:
            chosen = candidates
            front_back = 'front' if abs(candidates[0]) <= 90 else 'back'
            decided_by = 'three mics'
        world = [round(wrap180(c + self.yaw), 1) for c in chosen]
        source['estimate'] = dict(
            head_candidates=candidates, world_bearings=world, resolved=len(world) == 1,
            front_back=front_back, needs_head_turn=result['ambiguous'] and front_back == 'unknown',
            confidence=result['confidence'], lateral_deg=result['lateral_deg'], pairs=result['pairs'],
            score=result['score'], score_step_deg=result['score_step_deg'], yaw=round(self.yaw, 1),
            mic_count=len(ids), decided_by=decided_by, readings=len(resolver.observations),
            yaw_span_deg=round(resolver.yaw_span_deg, 2), error_deg=round(min(abs(wrap180(w - source['bearing'])) for w in world), 1))

    # Output -------------------------------------------------------------
    def _public(self, source, now):
        public = {k: v for k, v in source.items() if k not in ('resolver', 'started', 'sounding_until')}
        public['sounding'] = now < source['sounding_until']
        public['age_seconds'] = round(now - source['started'], 1)
        return public

    def snapshot(self):
        with self.lock:
            now = self.clock()
            self.sources = [s for s in self.sources if now < s['sounding_until'] + KEEP_AFTER_SOUNDING_SECONDS]
            mics = microphones(self.geometry, include_bridge=self.mic_count == 3)
            return dict(
                yaw=round(self.yaw, 2), base_yaw=round(self.base_yaw, 1), motion=self.motion,
                yaw_history=list(self.yaw_history), tick_seconds=TICK_SECONDS,
                mic_count=self.mic_count, snr_db=self.snr_db,
                map_radius_m=MAP_RADIUS_M, audio=dict(self.audio),
                mics=[dict(id=m['id'], x_mm=m['x_mm'], y_mm=m['y_mm'], status=m.get('status')) for m in mics],
                planned_mics=[dict(id='M0', x_mm=0, y_mm=0)] if self.mic_count == 2 else [],
                frame=self.geometry.get('frame', {}),
                reference_points=self.geometry.get('reference_points', []),
                sound_types=[dict(type=k, label=v[1]) for k, v in TARGETS.items() if k != 'bicycle_bell'],
                sources=[self._public(s, now) for s in reversed(self.sources)])
