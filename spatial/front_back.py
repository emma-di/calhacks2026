"""Resolve front vs. back for a two-mic array from head rotation.

Rule: when the head turns, a sound in front shifts the opposite way (turn right, it
moves toward the left ear) and a sound behind shifts the same way.

Two mics measure s = sin(alpha), where alpha is the sound's bearing relative to the head.
A head rotation d_psi (radians) changes it by ds = -cos(alpha) d_psi. The size of
cos(alpha) is known from s itself; only its sign differs: negative slope in front,
positive behind. The resolver fits the slope of s against yaw over all readings and
decides only when the slope is clearly nonzero and about the size geometry predicts.
Otherwise it stays 'unknown' rather than guess. Small natural head sway while walking is
enough for sharp sounds when the yaw is measured (IMU).
"""
import math
import statistics


class FrontBackResolver:
    def __init__(self, min_span_deg=1.5, min_t=3.0, slope_range=(0.4, 2.5),
                 outlier_deg=10.0, deliberate_turn_deg=5.0, max_observations=80):
        self.min_span_deg = min_span_deg  # least head rotation seen before deciding
        self.deliberate_turn_deg = deliberate_turn_deg  # a turn this big is enough with 2 readings
        self.min_t = min_t                # slope must exceed this many standard errors
        self.slope_range = slope_range    # allowed |slope| / predicted |cos(alpha)|
        self.outlier_deg = outlier_deg    # drop readings this far from the median angle
        self.max_observations = max_observations
        self.observations = []            # (yaw radians, lateral degrees)
        self.status = 'unknown'

    @property
    def yaw_span_deg(self):
        if not self.observations:
            return 0.0
        yaws = [y for y, _ in self.observations]
        return math.degrees(max(yaws) - min(yaws))

    def update(self, yaw_deg, lateral_deg):
        """Feed one reading: head yaw (positive = right) and left/right angle (-90..90).

        Re-evaluates with every reading, so a later, better-supported answer can replace
        an earlier one; it never switches on weak evidence.
        """
        self.observations.append((math.radians(yaw_deg), float(lateral_deg)))
        del self.observations[:-self.max_observations]
        decision = self._decide()
        if decision:
            self.status = decision
        return self.status

    def _decide(self):
        span = self.yaw_span_deg
        needed = 2 if span >= self.deliberate_turn_deg else 3
        if len(self.observations) < needed or span < self.min_span_deg:
            return None
        median = statistics.median(lat for _, lat in self.observations)
        kept = [(y, math.sin(math.radians(lat))) for y, lat in self.observations
                if abs(lat - median) <= self.outlier_deg]
        if len(kept) < needed:
            return None
        n = len(kept)
        mean_y = sum(y for y, _ in kept) / n
        mean_s = sum(s for _, s in kept) / n
        sxx = sum((y - mean_y) ** 2 for y, _ in kept)
        if sxx <= 0 or math.degrees(max(y for y, _ in kept) - min(y for y, _ in kept)) < self.min_span_deg:
            return None
        slope = sum((y - mean_y) * (s - mean_s) for y, s in kept) / sxx
        residual = sum((s - mean_s - slope * (y - mean_y)) ** 2 for y, s in kept)
        stderr = math.sqrt(residual / max(n - 2, 1) / sxx) + 1e-9
        predicted = math.sqrt(max(0.0, 1 - mean_s ** 2))  # |cos(alpha)|
        if predicted < 0.15:  # sound is almost exactly to one side: front and back coincide
            return None
        ratio = abs(slope) / predicted
        clear = n == 2 or abs(slope) / stderr >= self.min_t  # two readings: no spread to test
        if not clear or not self.slope_range[0] <= ratio <= self.slope_range[1]:
            return None
        return 'front' if slope < 0 else 'back'
