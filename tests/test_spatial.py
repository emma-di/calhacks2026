import unittest
from audio.events import make_event
from audio.server import AlertState
from audio.spatial import SpatialBuffer, validate_reading


def reading(bearing=90.0, coherence=0.8, calibrated=True, device='johns-phone'):
    return validate_reading(dict(bearing_degrees=bearing, coherence=coherence, rms=0.01,
                                 calibrated=calibrated, device=device))


class SpatialTests(unittest.TestCase):
    def test_matching_uses_only_recent_confident_calibrated_readings(self):
        buffer = SpatialBuffer()
        buffer.add(reading(-90, 0.95), 1000)          # too old for an event at 5000
        buffer.add(reading(90, 0.4), 4000)            # too weak
        buffer.add(reading(180, 0.9, calibrated=False), 4100)
        self.assertIsNone(buffer.match(5000))
        buffer.add(reading(85, 0.7), 4200)
        buffer.add(reading(95, 0.85), 4400)
        match = buffer.match(5000)
        self.assertEqual((match['bearing_degrees'], match['age_ms']), (95, 600))
        self.assertTrue(buffer.status(5000)['connected'])
        self.assertFalse(buffer.status(20000)['connected'])

    def test_recognized_sound_takes_the_phone_direction_but_test_sounds_never_do(self):
        state = AlertState()
        state.spatial_reading(dict(bearing_degrees=92, coherence=0.81, rms=0.02, calibrated=True,
                                   device='johns-phone'), now=10.0)
        state.add(make_event('knock', .9, 'microphone'), now=11.5)
        snap = state.snapshot(now=11.5)
        self.assertEqual(snap['direction'], 'right')
        self.assertEqual(snap['active']['direction_source'], 'johns-phone_foa')
        state.dismiss(now=11.6)
        state.add(make_event('bell', .9, 'mock'), now=30.0)
        self.assertIsNone(state.snapshot(now=30.0)['direction'])

    def test_invalid_readings_are_rejected(self):
        for bad in (dict(bearing_degrees=400, coherence=.5, rms=0, calibrated=True),
                    dict(bearing_degrees=10, coherence=2, rms=0, calibrated=True),
                    dict(bearing_degrees=10, coherence=.5, rms=0, calibrated='yes'),
                    [1, 2]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_reading(bad)
        self.assertIsNone(validate_reading(dict(bearing_degrees=None, coherence=.1, rms=0,
                                                calibrated=False))['bearing_degrees'])


if __name__ == '__main__':
    unittest.main()
