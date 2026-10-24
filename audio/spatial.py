"""Direction readings from a phone's spatial microphones, matched to recognized sounds by time.

The phone (native/PhoneSpatialProbe) streams its dominant-sound bearing a few times a second. When the
classifier on the Mac reports a sound without a direction, the receiver attaches the most coherent
calibrated phone reading from the window in which that sound was heard. Matching is by time only:
with two sounds at once it can pick the wrong one, so low-coherence readings are never used.
"""
from collections import deque
import json
import math
import os
from pathlib import Path

POLICY = json.loads(Path(__file__).with_name('alert-policy.json').read_text())['spatial_match']


def validate_reading(value):
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    bearing = value.get('bearing_degrees')
    if bearing is not None and (type(bearing) not in (int, float) or not math.isfinite(bearing)
                                or not -180 <= bearing <= 180):
        raise ValueError('bearing_degrees must be null or within -180..180')
    for key, upper in (('coherence', 1), ('rms', 10)):
        number = value.get(key)
        if type(number) not in (int, float) or not math.isfinite(number) or not 0 <= number <= upper:
            raise ValueError(f'{key} must be within 0..{upper}')
    if not isinstance(value.get('calibrated'), bool):
        raise ValueError('calibrated must be true or false')
    device = value.get('device', 'phone')
    if not isinstance(device, str) or not 0 < len(device) <= 40:
        raise ValueError('device must be a short name')
    return dict(bearing_degrees=bearing, coherence=float(value['coherence']), rms=float(value['rms']),
                calibrated=value['calibrated'], device=device)


SIDES = {'front': 0.0, 'right': 90.0, 'behind': 180.0, 'left': -90.0}


def wrap(degrees):
    return (degrees + 180) % 360 - 180


def circular_mean(values):
    return math.degrees(math.atan2(sum(math.sin(math.radians(v)) for v in values),
                                   sum(math.cos(math.radians(v)) for v in values)))


def calibrated_bearing(raw, points):
    """Map a phone bearing through example points {side: phone bearing observed there}.

    Learned from real sounds played at each side, so it absorbs mirroring, uneven sides and
    front/back offsets together. Between two neighbouring examples the angle is interpolated;
    with no examples the phone bearing is used unchanged.
    """
    if not points:
        return raw
    pairs = sorted((wrap(observed), SIDES[side]) for side, observed in points.items())
    if len(pairs) == 1:
        return wrap(raw - pairs[0][0] + pairs[0][1])
    a = wrap(raw)
    for index, (c1, t1) in enumerate(pairs):
        c2, t2 = pairs[(index + 1) % len(pairs)]
        span = (c2 - c1) % 360 or 360
        offset = (a - c1) % 360
        if offset <= span:
            step = wrap(t2 - t1)
            if abs(step) == 180:  # opposite examples with nothing between: keep the short way round
                step = 180 if span <= 180 else -180
            return wrap(t1 + offset / span * step)
    return a


class SpatialBuffer:
    """Recent phone readings, keyed by Mac receive time in monotonic milliseconds."""

    def __init__(self, calibration_path=None):
        self.readings = deque(maxlen=200)
        self.last_seen = {}
        self.calibration_path = Path(calibration_path) if calibration_path else None
        self.points = {}
        try:
            saved = json.loads(self.calibration_path.read_text())
            self.points = {side: float(v) for side, v in saved.get('points', {}).items() if side in SIDES}
        except (AttributeError, OSError, ValueError, TypeError):
            pass

    def calibrate(self, examples):
        """examples: {side: [phone bearings heard from that side]}; an empty dict clears.

        Each side's examples are averaged on the circle. Needs front plus at least one other side.
        """
        if not isinstance(examples, dict) or any(side not in SIDES for side in examples):
            raise ValueError('examples must map front/right/behind/left to lists of bearings')
        points = {}
        for side, values in examples.items():
            if not isinstance(values, list) or not values or not all(
                    type(v) in (int, float) and math.isfinite(v) and -180 <= v <= 180 for v in values):
                raise ValueError(f'{side} needs a non-empty list of bearings within -180..180')
            points[side] = circular_mean(values)
        if points and ('front' not in points or len(points) < 2):
            raise ValueError('calibrate front and at least one other side')
        self.points = points
        if self.calibration_path:
            self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.calibration_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(points=points)))
            os.replace(temporary, self.calibration_path)

    def add(self, reading, at):
        self.last_seen[reading['device']] = (at, reading)
        if reading['bearing_degrees'] is not None and reading['calibrated'] \
                and reading['coherence'] >= POLICY['min_coherence']:
            self.readings.append((at, reading))

    def match(self, at):
        """Best reading heard within the event's window, or None. Never invents a direction."""
        window = [(t, r) for t, r in self.readings
                  if at - POLICY['before_ms'] <= t <= at + POLICY['after_ms']]
        if not window:
            return None
        t, reading = max(window, key=lambda item: (item[1]['coherence'], item[0]))
        return dict(reading, bearing_degrees=calibrated_bearing(reading['bearing_degrees'], self.points),
                    phone_degrees=reading['bearing_degrees'], age_ms=round(at - t))

    def status(self, at):
        live = {device: dict(age_ms=round(at - t), bearing_degrees=r['bearing_degrees'],
                             coherence=round(r['coherence'], 2), calibrated=r['calibrated'])
                for device, (t, r) in self.last_seen.items() if at - t < POLICY['stale_ms']}
        return dict(connected=bool(live), devices=live,
                    calibration={side: round(v, 1) for side, v in self.points.items()})
