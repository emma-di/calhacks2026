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


def stretch(bearing, right, left=None):
    """Map a front-calibrated bearing so the observed side references land on +90 and -90.

    Phones held in portrait compress and can mirror the lateral axis, and not equally on both sides
    (John's iPhone: right knocks read about -29, left knocks only +9..+32). `right`/`left` are the
    bearings observed for sounds at the wearer's right/left; the left defaults to mirroring the
    right. Piecewise-linear and monotonic per side: front stays 0, behind stays 180.
    """
    if right is None and left is None:
        return bearing
    sign = math.copysign(1, right if right is not None else -left)  # +1 if the phone is not mirrored
    toward_right = bearing * sign >= 0
    reference = abs(right if toward_right and right is not None else left if left is not None else right)
    magnitude = abs(bearing)
    mapped = 90 * magnitude / reference if magnitude <= reference \
        else 90 + (magnitude - reference) * 90 / (180 - reference)
    return min(180, mapped) * (1 if toward_right else -1)


class SpatialBuffer:
    """Recent phone readings, keyed by Mac receive time in monotonic milliseconds."""

    def __init__(self, calibration_path=None):
        self.readings = deque(maxlen=200)
        self.last_seen = {}
        self.calibration_path = Path(calibration_path) if calibration_path else None
        self.right_reference = self.left_reference = None
        try:
            saved = json.loads(self.calibration_path.read_text())
            self.right_reference, self.left_reference = saved.get('right_degrees'), saved.get('left_degrees')
        except (AttributeError, OSError, ValueError, TypeError):
            pass

    def calibrate(self, right_degrees, left_degrees=None):
        """Bearings the phone reported for sounds at the wearer's right and left (None clears)."""
        for name, value in (('right_degrees', right_degrees), ('left_degrees', left_degrees)):
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                                      or not 5 <= abs(value) <= 170):
                raise ValueError(f'{name} must be between 5 and 170 degrees from front, or null')
        if right_degrees is not None and left_degrees is not None and (right_degrees > 0) == (left_degrees > 0):
            raise ValueError('right and left references must be on opposite sides of front')
        self.right_reference, self.left_reference = right_degrees, left_degrees
        if self.calibration_path:
            self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.calibration_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(dict(right_degrees=right_degrees, left_degrees=left_degrees)))
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
        return dict(reading, bearing_degrees=stretch(reading['bearing_degrees'], self.right_reference,
                                                     self.left_reference),
                    phone_degrees=reading['bearing_degrees'], age_ms=round(at - t))

    def status(self, at):
        live = {device: dict(age_ms=round(at - t), bearing_degrees=r['bearing_degrees'],
                             coherence=round(r['coherence'], 2), calibrated=r['calibrated'])
                for device, (t, r) in self.last_seen.items() if at - t < POLICY['stale_ms']}
        return dict(connected=bool(live), devices=live, right_reference=self.right_reference,
                    left_reference=self.left_reference)
