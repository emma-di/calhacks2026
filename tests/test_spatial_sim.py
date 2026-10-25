"""Spatial checks on synthesized audio; NumPy only, no recordings or microphones."""
import math
import unittest

import numpy as np

from spatial.front_back import FrontBackResolver
from spatial.gcc_phat import gcc_phat
from spatial.geometry import mic_positions, unit_vector, world_to_head, wrap180
from spatial.localize import localize
from spatial.scene import Scene
from spatial.simulate import SAMPLE_RATE, render, source_signal


def angle_error(a, b):
    return abs(wrap180(a - b))


class GccPhatTests(unittest.TestCase):
    def test_recovers_fractional_delay(self):
        rng = np.random.default_rng(1)
        ref = rng.standard_normal(4800)
        delay = 7.4 / SAMPLE_RATE
        spectrum = np.fft.rfft(ref, 9600)
        freqs = np.fft.rfftfreq(9600, 1 / SAMPLE_RATE)
        sig = np.fft.irfft(spectrum * np.exp(-2j * np.pi * freqs * delay), 9600)[:4800]
        tau, _, _ = gcc_phat(sig, ref, SAMPLE_RATE, max_tau=0.001)
        self.assertAlmostEqual(tau, delay, delta=2e-6)


class LocalizeTests(unittest.TestCase):
    def test_three_mics_find_bearing_all_around(self):
        rng = np.random.default_rng(2)
        ids, mics = mic_positions(include_bridge=True)
        for bearing in range(-180, 180, 30):
            channels = render(unit_vector(bearing) * 4, mics, source_signal('knock', rng=rng), rng=rng)
            result = localize(channels, SAMPLE_RATE, mics, ids)
            self.assertFalse(result['ambiguous'])
            self.assertLess(angle_error(result['candidates'][0], bearing), 4, bearing)

    def test_two_mics_report_front_and_back_mirror(self):
        rng = np.random.default_rng(3)
        ids, mics = mic_positions()
        for bearing in (-150, -60, 20, 130):
            channels = render(unit_vector(bearing) * 4, mics, source_signal('knock', rng=rng), rng=rng)
            result = localize(channels, SAMPLE_RATE, mics, ids)
            self.assertTrue(result['ambiguous'])
            front, back = result['candidates']
            self.assertLessEqual(abs(front), 90)
            self.assertLess(min(angle_error(front, bearing), angle_error(back, bearing)), 4, bearing)
            self.assertLess(angle_error(back, 180 - front), 1)


def feed(resolver, bearing, yaws, noise_deg=0.0, seed=0):
    """Feed what two mics would measure for a sound at `bearing` while the head is at each yaw."""
    rng = np.random.default_rng(seed)
    for yaw in yaws:
        head = math.radians(bearing - yaw)
        resolver.update(yaw, math.degrees(math.asin(math.sin(head))) + rng.normal(0, noise_deg))
    return resolver.status


class FrontBackTests(unittest.TestCase):
    def test_turn_right_front_sound_moves_left(self):
        self.assertEqual(feed(FrontBackResolver(), 20, [0, 5, 10, 15]), 'front')

    def test_turn_right_back_sound_moves_right(self):
        self.assertEqual(feed(FrontBackResolver(), 160, [0, 5, 10, 15]), 'back')

    def test_small_natural_sway_is_enough(self):
        sway = [2.5 * math.sin(2 * math.pi * 0.9 * k * 0.1) for k in range(6)]
        self.assertEqual(feed(FrontBackResolver(), 30, sway, noise_deg=0.1), 'front')
        self.assertEqual(feed(FrontBackResolver(), -140, sway, noise_deg=0.1), 'back')

    def test_waits_without_enough_rotation(self):
        self.assertEqual(feed(FrontBackResolver(), 20, [0, 0.3, 0.6, 0.9]), 'unknown')

    def test_does_not_guess_on_noise(self):
        self.assertEqual(feed(FrontBackResolver(), 20, [0, 1, 2, 1, 0], noise_deg=5, seed=3), 'unknown')

    def test_sound_at_the_side_stays_unknown(self):
        self.assertEqual(feed(FrontBackResolver(), 90, [0, 3, 6, 3, 0]), 'unknown')

    def test_head_rotation(self):
        ahead = world_to_head((0, 1), 90)  # facing right, the old "ahead" is now to the left
        np.testing.assert_allclose(ahead, (-1, 0), atol=1e-12)


class SceneTests(unittest.TestCase):
    def test_head_turn_resolves_two_mic_sound_behind(self):
        scene = Scene(rng=np.random.default_rng(4), clock=lambda: 0.0)
        source = scene.add('siren', x=-2.0, y=-3.0)
        self.assertFalse(source['estimate']['resolved'])
        scene.turn(delta=15)
        estimate = scene.snapshot()['sources'][0]['estimate']
        self.assertEqual(estimate['front_back'], 'back')
        self.assertLess(estimate['error_deg'], 5)

    def test_ended_sound_is_not_reestimated(self):
        now = [0.0]
        scene = Scene(rng=np.random.default_rng(5), clock=lambda: now[0])
        scene.add('knock', x=-3.0, y=1.0)
        now[0] = 5.0
        scene.turn(delta=20)
        self.assertEqual(scene.snapshot()['sources'][0]['estimate']['front_back'], 'unknown')

    def test_three_mics_resolve_without_turning(self):
        scene = Scene(rng=np.random.default_rng(6), clock=lambda: 0.0)
        scene.set_mic_count(3)
        estimate = scene.add('dog_bark', x=1.0, y=-3.0)['estimate']
        self.assertTrue(estimate['resolved'])
        self.assertLess(estimate['error_deg'], 6)

    def test_walking_sway_resolves_a_short_knock(self):
        for bearing, expected in ((25, 'front'), (-150, 'back')):
            now = [0.0]
            scene = Scene(rng=np.random.default_rng(8), clock=lambda: now[0])
            scene.set_motion('walking')
            scene.add('knock', x=3 * math.sin(math.radians(bearing)), y=3 * math.cos(math.radians(bearing)))
            for _ in range(6):  # a knock lasts 0.6 s
                now[0] += 0.1
                scene.tick()
            estimate = scene.snapshot()['sources'][0]['estimate']
            self.assertEqual(estimate['front_back'], expected, bearing)
            self.assertEqual(estimate['decided_by'], 'head motion')
            self.assertLess(estimate['error_deg'], 5)

    def test_standing_still_cannot_resolve(self):
        now = [0.0]
        scene = Scene(rng=np.random.default_rng(9), clock=lambda: now[0])
        scene.add('siren', x=1.0, y=-3.0)
        for _ in range(10):
            now[0] += 0.1
            scene.tick()
        self.assertEqual(scene.snapshot()['sources'][0]['estimate']['front_back'], 'unknown')

    def test_rejects_unknown_motion(self):
        with self.assertRaises(ValueError):
            Scene(rng=np.random.default_rng(10)).set_motion('running')

    def test_rejects_unknown_type_and_out_of_range(self):
        scene = Scene(rng=np.random.default_rng(7))
        with self.assertRaises(ValueError):
            scene.add('thunder', x=1, y=1)
        with self.assertRaises(ValueError):
            scene.add('knock', x=10, y=0)


if __name__ == '__main__':
    unittest.main()
