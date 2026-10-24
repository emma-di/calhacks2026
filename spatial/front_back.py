"""Resolve front vs. back for a two-mic array using a head turn.

Rule: when the wearer turns their head, a sound in front shifts the opposite way
(turn right, it moves toward the left ear) and a sound behind shifts the same way.
This needs the head yaw (from an IMU, or the simulator) and a sound that is still going.
"""


class FrontBackResolver:
    def __init__(self, min_turn_deg=10.0, min_shift_deg=2.0):
        self.min_turn_deg = min_turn_deg
        self.min_shift_deg = min_shift_deg
        self.reference = None
        self.status = 'unknown'

    def update(self, yaw_deg, lateral_deg):
        """Feed one observation: head yaw (positive = right) and left/right angle (-90..90)."""
        if self.status != 'unknown':
            return self.status
        if self.reference is None:
            self.reference = (yaw_deg, lateral_deg)
            return self.status
        turn = yaw_deg - self.reference[0]
        shift = lateral_deg - self.reference[1]
        if abs(turn) < self.min_turn_deg:
            return self.status
        if abs(shift) < self.min_shift_deg:
            # Sound is near one side; front and back nearly coincide. Try again from here.
            self.reference = (yaw_deg, lateral_deg)
            return self.status
        self.status = 'front' if (shift > 0) != (turn > 0) else 'back'
        return self.status
