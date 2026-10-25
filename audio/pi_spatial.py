"""Conservative lateral evidence from synchronized Pi stereo, never front/back or distance.

Channel 0=physical left, 1=right (confirmed by Emma). This is a level-based demo
heuristic, not calibrated localization accuracy. All thresholds need final-room trials.
"""
import math
import numpy as np


def unknown(reason):
    return dict(side=None, direction_degrees=None, direction_confidence=None, reason=reason)


def delay_evidence(left, right, spacing_cm=13.):
    """GCC-PHAT lateral delay, constrained by the confirmed 11–13cm array.

    Negative correlation lag means left heard it first. Require a distinct peak;
    periodic alarms can have equally plausible lags and must remain ambiguous.
    """
    if not math.isfinite(spacing_cm) or not 1 <= spacing_cm <= 30:
        return None
    max_lag = int(math.ceil(spacing_cm / 100 / 343 * 48000))
    cross = np.fft.rfft(left, 16384) * np.conj(np.fft.rfft(right, 16384))
    magnitude = np.abs(cross)
    if not np.any(magnitude > 1e-10):
        return None
    corr = np.fft.irfft(cross / np.maximum(magnitude, max(float(magnitude.max()) * 1e-4, 1e-12)), 16384)
    lags = np.arange(-max_lag, max_lag+1)
    peaks = np.abs(corr[lags % len(corr)])
    index = int(np.argmax(peaks))
    lag = int(lags[index])
    alternatives = peaks[np.abs(lags - lag) > 2]
    runner = float(alternatives.max()) if len(alternatives) else 0.
    quality = float(peaks[index]) / max(runner, 1e-12)
    if abs(lag) < 2 or abs(lag) > spacing_cm / 100 / 343 * 48000 + .5 or quality < 1.6:
        return None
    return dict(side='left' if lag < 0 else 'right', lag_samples=lag,
                peak_ratio=round(quality, 2))


def frame_evidence(pcm, gain_offset_db=0., min_dbfs=-75., margin_db=2.5):
    """100ms S32_LE stereo → lateral evidence, gated by signal and channel agreement."""
    if not pcm or len(pcm) % 8 or not math.isfinite(gain_offset_db):
        return unknown('invalid_input')
    stereo = np.frombuffer(pcm, dtype='<i4').reshape(-1, 2).astype(np.float64) / 2**31
    if len(stereo) != 4800:
        return unknown('invalid_frame_length')
    if np.any(np.abs(stereo) >= .999):
        return unknown('clipping')
    # Remove DC so a stuck/broken channel cannot look like a steady loud source.
    stereo -= stereo.mean(axis=0)
    rms = np.sqrt(np.mean(stereo * stereo, axis=0))
    db = 20*np.log10(np.maximum(rms, 1e-6))
    if min(db) < -85:
        return unknown('quiet_or_missing_channel')
    if max(db) < min_dbfs:
        return unknown('quiet')
    difference = float(db[0] - db[1] - gain_offset_db)
    # Reject strongly different mixtures. Allow up to 1ms lag, covering plausible glasses
    # spacing, without claiming a measured geometry or an exact bearing from that lag.
    left, right = stereo.T
    corr = np.fft.irfft(np.fft.rfft(left, 16384) * np.conj(np.fft.rfft(right, 16384)), 16384)
    peak = max(float(np.max(np.abs(corr[:49]))), float(np.max(np.abs(corr[-48:]))))
    coherence = min(1., peak / max(float(np.linalg.norm(left)*np.linalg.norm(right)), 1e-12))
    if coherence < .2:
        return dict(unknown('inconsistent_channels'), coherence=round(coherence,3), difference_db=round(difference,2))
    timing = delay_evidence(left, right) if coherence >= .55 else None
    level_side = ('left' if difference > 0 else 'right') if abs(difference) >= margin_db else None
    if timing and level_side and timing['side'] != level_side:
        return unknown('timing_level_conflict')
    side = timing['side'] if timing else level_side
    if side is None:
        return dict(unknown('balanced_or_ambiguous_delay'), coherence=round(coherence,3), difference_db=round(difference,2))
    return dict(side=side, direction_degrees=-90 if side == 'left' else 90,
                # Evidence quality, NOT a measured probability of correct direction.
                direction_confidence=round(min(.9, .7 if timing else .6 + (abs(difference)-margin_db)*.025), 3),
                reason='lateral_arrival_time' if timing else 'lateral_level_difference',
                lag_samples=timing['lag_samples'] if timing else None,
                difference_db=round(difference, 2),
                coherence=round(coherence, 3))


def window_evidence(frames, require_current=True):
    """Associate only evidence carried by this exact recognition window.

    Require >=300ms of consistent evidence, recent support and no opposite side.
    Stable timing may bridge brief tonal ambiguity, never quiet or channel failure.
    This cannot separate simultaneous overlapping sound sources.
    """
    if len(frames) < 3:
        return unknown('insufficient_duration')
    sides = {frame['side'] for frame in frames if frame['side'] is not None}
    if len(sides) > 1:
        return unknown('competing_sides')
    if not sides:
        return unknown('no_lateral_evidence')
    side = next(iter(sides))
    votes = [frame for frame in frames if frame['side'] == side]
    recent = frames[-3:]
    # Quiet, clipping and a broken/mixed channel must clear immediately. A periodic tone
    # can briefly lose a unique correlation peak while retaining the same ongoing sound.
    if require_current and frames[-1]['side'] != side and (frames[-1]['reason'] != 'balanced_or_ambiguous_delay'
            or not any(frame['side'] == side for frame in recent)):
        return unknown('no_current_evidence')
    run = longest = 0
    for frame in frames:
        run = run + 1 if frame['side'] == side else 0
        longest = max(longest, run)
    timing = [frame for frame in votes if frame.get('lag_samples') is not None]
    stable_timing = (len(timing) >= 3 and
                     max(frame['lag_samples'] for frame in timing) - min(frame['lag_samples'] for frame in timing) <= 2)
    # For a classified window, beep pauses are not contradictory direction evidence.
    # Infer direction from its audible frames; monitor mode still clears on quiet.
    eligible = frames if require_current else [frame for frame in frames if frame['reason'] not in
                ('quiet', 'quiet_or_missing_channel')]
    if (len(votes) < 3 or (require_current and longest < 2) or
            len(votes) / max(len(eligible),1) < (.2 if stable_timing else .6)):
        return unknown('insufficient_consistency')
    return dict(side=side, direction_degrees=-90 if side == 'left' else 90,
                direction_confidence=min(frame['direction_confidence'] for frame in votes),
                reason='sustained_lateral_evidence')


def annotate_events(events, evidence, competing=False):
    """Pi owns its unknowns too; never fill them from an unrelated phone reading."""
    reading = unknown('multiple_detected_events') if competing else evidence
    for event in events:
        event.update(direction_degrees=reading['direction_degrees'],
                     direction_confidence=reading['direction_confidence'],
                     direction_source='pi_stereo', direction_reason=reading['reason'])
