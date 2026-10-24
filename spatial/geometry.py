"""Microphone geometry in the head frame, plus angle helpers.

Coordinates follow spatial/frame_geometry.json: origin at the bridge of the nose,
+x toward the wearer's right, +y in front. Angles are bearings: 0 deg straight ahead,
increasing clockwise toward the right, so bearing = atan2(x, y).
"""
import json
import math
from pathlib import Path

import numpy as np

GEOMETRY_PATH = Path(__file__).with_name('frame_geometry.json')
SPEED_OF_SOUND = 343.0  # m/s, about 20 C
BRIDGE_MIC = dict(id='M0', position='nose bridge', x_mm=0, y_mm=0, status='planned')


def load_geometry(path=None):
    return json.loads(Path(path or GEOMETRY_PATH).read_text())


def microphones(geometry=None, include_bridge=False):
    """Microphone records from the geometry file, optionally adding the planned bridge mic."""
    mics = list((geometry or load_geometry())['microphones'])
    if include_bridge and not any(m['id'] == 'M0' for m in mics):
        mics = [BRIDGE_MIC] + mics
    return mics


def mic_positions(geometry=None, include_bridge=False):
    """Return (ids, positions) with positions as an N x 2 array in meters, head frame."""
    mics = microphones(geometry, include_bridge)
    return [m['id'] for m in mics], np.array([[m['x_mm'] / 1000, m['y_mm'] / 1000] for m in mics])


def wrap180(angle_deg):
    return (angle_deg + 180.0) % 360.0 - 180.0


def bearing_deg(x, y):
    return math.degrees(math.atan2(x, y))


def unit_vector(bearing):
    rad = math.radians(bearing)
    return np.array([math.sin(rad), math.cos(rad)])


def world_to_head(xy, yaw_deg):
    """Rotate a world-frame point into the head frame. Positive yaw means the head turned right."""
    psi = math.radians(yaw_deg)
    x, y = xy
    return np.array([x * math.cos(psi) - y * math.sin(psi), x * math.sin(psi) + y * math.cos(psi)])


def max_pair_delay(mic_xy):
    """Largest possible arrival-time difference between any two mics, in seconds."""
    n = len(mic_xy)
    return max(np.linalg.norm(mic_xy[i] - mic_xy[j]) for i in range(n) for j in range(i + 1, n)) / SPEED_OF_SOUND
