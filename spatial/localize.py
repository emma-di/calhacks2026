"""Direction of arrival from synchronized mic channels (SRP-PHAT over bearings).

For every candidate bearing, each mic pair's GCC-PHAT correlation is read at the
delay that bearing would produce, and the pairs are averaged. The best bearing is the
highest point. With two mics (or any mics in a line) every bearing has a mirror
image across the mic axis with the same delays, so both are reported.
"""
import numpy as np

from spatial.gcc_phat import gcc_phat
from spatial.geometry import SPEED_OF_SOUND, bearing_deg, max_pair_delay, wrap180


def is_collinear(mic_xy, tolerance_m=0.005):
    centered = mic_xy - mic_xy.mean(axis=0)
    return len(mic_xy) < 3 or np.linalg.svd(centered, compute_uv=False)[1] < tolerance_m


def mirror_bearing(bearing, mic_xy):
    """Reflect a bearing across the line through a collinear array."""
    axis = mic_xy[-1] - mic_xy[0]
    return wrap180(2 * bearing_deg(axis[0], axis[1]) - bearing)


def predicted_delays(mic_xy, azimuths_deg, i, j):
    """Far-field arrival time at mic i minus mic j, for each bearing (seconds)."""
    rad = np.radians(azimuths_deg)
    directions = np.stack((np.sin(rad), np.cos(rad)), axis=1)
    return -(directions @ (mic_xy[i] - mic_xy[j])) / SPEED_OF_SOUND


def _peaks(score):
    is_peak = (score > np.roll(score, 1)) & (score >= np.roll(score, -1))
    order = np.argsort(score[is_peak])[::-1]
    return np.flatnonzero(is_peak)[order]


def localize(channels, fs, mic_xy, ids=None, step_deg=1.0):
    """Estimate the bearing (head frame, degrees) of the dominant sound.

    Returns a dict with `candidates` (one bearing, or a mirror pair when the array is
    collinear), `ambiguous`, `confidence` (0..1, heuristic), `lateral_deg` (the
    left/right angle folded into -90..90), per-pair delays and a coarse score curve.
    """
    mic_xy = np.asarray(mic_xy, dtype=np.float64)
    ids = ids or [f'M{k}' for k in range(len(mic_xy))]
    azimuths = np.arange(-180.0, 180.0, step_deg)
    max_tau = max_pair_delay(mic_xy) * 1.2
    score = np.zeros_like(azimuths)
    pairs = []
    taus = {}
    for i in range(len(mic_xy)):
        for j in range(i + 1, len(mic_xy)):
            tau, lags, cc = gcc_phat(channels[i], channels[j], fs, max_tau=max_tau)
            taus[i, j] = tau
            score += np.interp(predicted_delays(mic_xy, azimuths, i, j), lags, cc)
            pairs.append(dict(pair=f'{ids[i]}-{ids[j]}', tdoa_us=round(tau * 1e6, 1),
                              peak=round(float(cc.max()), 3)))
    score /= len(pairs)

    peaks = _peaks(score)
    best = float(azimuths[peaks[0]])
    best_score = float(score[peaks[0]])
    ambiguous = bool(is_collinear(mic_xy))
    candidates = [best]
    if ambiguous:
        mirror = float(mirror_bearing(best, mic_xy))
        candidates = sorted([best, mirror], key=lambda a: abs(wrap180(a)))  # front-half first
    # Penalize a competing peak in an unrelated direction (echo, aliasing, second source).
    rivals = [float(score[k]) for k in peaks[1:]
              if all(abs(wrap180(azimuths[k] - c)) > 15 for c in candidates)]
    rival = max(rivals, default=0.0)
    confidence = 0.0 if best_score <= 0 else float(np.clip(best_score, 0, 1) *
                                                   np.clip(1 - max(rival, 0) / best_score, 0, 1))
    if ambiguous:
        # Read the left/right angle straight from the end pair's delay: finer than the
        # bearing grid, which matters for the small shifts caused by head sway.
        i, j = 0, len(mic_xy) - 1
        axis = mic_xy[i] - mic_xy[j]
        projection = np.clip(-SPEED_OF_SOUND * taus[i, j] / np.linalg.norm(axis), -1, 1)
        lateral = float(np.degrees(np.arcsin(projection))) * (1 if axis[0] >= 0 else -1)
    else:
        lateral = float(np.degrees(np.arcsin(np.clip(np.sin(np.radians(candidates[0])), -1, 1))))
    return dict(candidates=[round(c, 1) for c in candidates], ambiguous=ambiguous,
                confidence=round(confidence, 3), lateral_deg=round(lateral, 3),
                pairs=pairs, score=[round(float(s), 3) for s in score[::int(round(2 / step_deg)) or 1]],
                score_step_deg=2.0)
