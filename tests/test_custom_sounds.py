"""Custom-sound head tests. NumPy only: no weights, recordings or microphone."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from audio import custom_sounds as cs
from audio.events import make_custom_event, validate_event
from audio.server import AlertState

def cluster(center, n, rng, spread=0.3):
    return (center+spread*rng.standard_normal((n, len(center)))).astype(np.float32)

class HeadTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.target = rng.standard_normal(256)
        self.positives = cluster(self.target, 12, rng)
        # Background: many unrelated sounds, grouped as 20-window "recordings".
        self.background = np.vstack([cluster(rng.standard_normal(256), 20, rng) for _ in range(30)])
        self.groups = np.repeat(np.arange(30), 20)
        self.rng = rng

    def test_head_separates_and_threshold_is_bounded(self):
        head, report = cs.train_head(self.positives, self.background, self.groups)
        self.assertTrue(cs.MIN_THRESHOLD <= head['threshold'] <= cs.MAX_THRESHOLD)
        unseen = cluster(self.target, 10, self.rng)
        self.assertTrue((cs.head_scores(head, unseen) >= head['threshold']).all())
        others = cluster(self.rng.standard_normal(256), 50, self.rng)
        self.assertLess((cs.head_scores(head, others) >= head['threshold']).mean(), 0.05)
        self.assertEqual(report['positive_windows'], 12)

    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            cs.train_head(np.empty((0, 256)), self.background, self.groups)
        with self.assertRaises(ValueError):
            cs.train_head(self.positives, self.background[:5], self.groups[:5])

class WindowTests(unittest.TestCase):
    def test_window_counts_cover_the_whole_clip(self):
        self.assertEqual(len(cs.windows(np.zeros(8000))), 1)        # short clip padded
        self.assertEqual(len(cs.windows(np.zeros(32000))), 1)
        self.assertEqual(len(cs.windows(np.zeros(80000))), 4)       # 5 s like ESC-50
        self.assertEqual(len(cs.windows(np.zeros(88000))), 5)       # tail kept

    def test_silence_is_not_used_for_training(self):
        clip = np.zeros(96000, dtype=np.float32)
        clip[48000:64000] = 0.5*np.sin(np.arange(16000)/5)
        selected = cs.active_windows(clip)
        self.assertTrue(selected)
        self.assertTrue(all(cs.rms(w) > cs.SILENCE_RMS for w in selected))
        self.assertEqual(cs.active_windows(np.zeros(48000)), [])

class EventTests(unittest.TestCase):
    sound = dict(id='front-doorbell', label='Front doorbell', priority_tier=2)

    def test_custom_event_validates_and_displays(self):
        event = validate_event(make_custom_event(self.sound, 0.9, 'microphone'))
        self.assertEqual(event['label'], 'Front doorbell')
        state = AlertState()
        state.add(event)
        self.assertEqual(state.snapshot()['active']['custom_sound_id'], 'front-doorbell')

    def test_custom_event_needs_id(self):
        event = make_custom_event(self.sound, 0.9, 'microphone')
        del event['custom_sound_id']
        with self.assertRaises(ValueError):
            validate_event(event)

class StoreAndDetectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(cs, 'STORE', Path(self.tmp.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_create_list_remove_and_validation(self):
        meta = cs.create_sound('Front doorbell', 3)
        self.assertEqual(meta['id'], 'front-doorbell')
        with self.assertRaises(ValueError):
            cs.create_sound('  front   DOORBELL ')                 # duplicate name, any spacing/case
        self.assertEqual(cs.create_sound('Back doorbell')['id'], 'back-doorbell')
        self.assertEqual(len(cs.list_sounds()), 2)
        cs.remove_sound('front-doorbell')
        self.assertEqual(len(cs.list_sounds()), 1)
        for label in ('', 'x'*61, 'bad\nlabel'):
            with self.assertRaises(ValueError):
                cs.create_sound(label)
        with self.assertRaises(ValueError):
            cs.sound_dir('../escape')

    def test_detector_threshold_cooldown_and_silence(self):
        head = dict(weights=np.ones(4, np.float32), bias=0.0, mean=np.zeros(4, np.float32),
                    std=np.ones(4, np.float32), threshold=np.float32(0.7))
        meta = dict(id='kettle', label='Kettle', priority_tier=2)
        with mock.patch.object(cs, 'load_heads', return_value=[(meta, head)]):
            detector = cs.CustomSoundDetector(cooldown=5)
        match, miss = np.ones(4), -np.ones(4)
        self.assertEqual(detector.detect(miss, 0.1, 'replay', now=0), [])
        self.assertEqual(len(detector.detect(match, 0.1, 'replay', now=0)), 1)
        self.assertEqual(detector.detect(match, 0.1, 'replay', now=2), [])
        self.assertEqual(detector.decisions[0]['reason'], 'cooldown')
        self.assertEqual(detector.detect(match, 0.0, 'replay', now=10), [])
        self.assertEqual(detector.decisions[0]['reason'], 'silent_window')
        self.assertEqual(len(detector.detect(match, 0.1, 'replay', now=10)), 1)

if __name__ == '__main__':
    unittest.main()
