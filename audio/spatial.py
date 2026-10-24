"""Direction readings from a phone's spatial microphones, matched to recognized sounds by time.

The phone (native/PhoneSpatialProbe) streams its dominant-sound bearing a few times a second. When the
classifier on the Mac reports a sound without a direction, the receiver attaches the most coherent
calibrated phone reading from the window in which that sound was heard. Matching is by time only:
with two sounds at once it can pick the wrong one, so low-coherence readings are never used.
"""
from collections import deque
import json
import math
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


class SpatialBuffer:
    """Recent phone readings, keyed by Mac receive time in monotonic milliseconds."""

    def __init__(self):
        self.readings = deque(maxlen=200)
        self.last_seen = {}

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
        return dict(reading, age_ms=round(at - t))

    def status(self, at):
        live = {device: dict(age_ms=round(at - t), bearing_degrees=r['bearing_degrees'],
                             coherence=round(r['coherence'], 2), calibrated=r['calibrated'])
                for device, (t, r) in self.last_seen.items() if at - t < POLICY['stale_ms']}
        return dict(connected=bool(live), devices=live)
