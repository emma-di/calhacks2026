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

    def test_four_side_examples_fix_mirroring_uneven_sides_and_front_back(self):
        from audio.spatial import calibrated_bearing
        # John's iPhone with doorbells: right reads negative, left positive, behind not at 180.
        points = dict(front=2, right=-60, behind=150, left=50)
        side = lambda raw: min(('front', 0), ('right', 90), ('behind', 180), ('left', -90),
                               key=lambda s: abs((calibrated_bearing(raw, points) - s[1] + 180) % 360 - 180))[0]
        self.assertEqual([side(r) for r in (0, -65, -22 - 30, 155, -170, 48, 90)],
                         ['front', 'right', 'right', 'behind', 'behind', 'left', 'left'])
        self.assertEqual(calibrated_bearing(33.0, {}), 33.0)
        buffer = SpatialBuffer()
        buffer.calibrate(dict(front=[0, 4], right=[-58, -62], left=[50], behind=[150]))
        buffer.add(reading(-61, 0.8), 100)
        self.assertAlmostEqual(buffer.match(200)['bearing_degrees'], 90, delta=3)
        for bad in (dict(right=[-60]), dict(front=[0], up=[5]), dict(front=[]), dict(front=[0], right=['x'])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                buffer.calibrate(bad)
        buffer.calibrate({})
        self.assertEqual(buffer.points, {})

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
