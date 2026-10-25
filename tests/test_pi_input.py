import queue
import unittest
import tempfile
import json
from pathlib import Path
import numpy as np

from audio.pi_input import RecognitionState, StereoResampler, load_calibration


def pcm(data):
    return (np.clip(data, -1, .999999) * 2**31).astype('<i4').tobytes()


class PiInputTests(unittest.TestCase):
    def test_numeric_calibration_is_bounded_and_invalid_values_fall_back(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'calibration.json'
            self.assertEqual(load_calibration(path),(0.,1.25))
            path.write_text(json.dumps(dict(schema_version=1,gain_offset_db=-.89,margin_db=.75)))
            self.assertEqual(load_calibration(path),(-.89,.75))
            for value in [[],None,dict(schema_version=1,gain_offset_db=100,margin_db=.75),
                          dict(schema_version=1,gain_offset_db=0,margin_db=0)]:
                path.write_text(json.dumps(value))
                self.assertEqual(load_calibration(path),(0.,1.25))
    def test_chunked_resampling_matches_continuous_and_correct_rate(self):
        rng = np.random.default_rng(12)
        stereo = rng.normal(0, .1, (9600, 2))
        raw = pcm(stereo)
        expected = StereoResampler().convert(raw)
        converter = StereoResampler()
        actual = np.concatenate([converter.convert(raw[:4000]), converter.convert(raw[4000:])])
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(len(actual), 3200)

    def test_antialias_filter_rejects_out_of_band_tone(self):
        t = np.arange(48000) / 48000
        def tone(hz):
            signal = .4 * np.sin(2*np.pi*hz*t)
            return StereoResampler().convert(pcm(np.column_stack((signal, signal))))[100:]
        low, high = tone(1000), tone(12000)
        self.assertGreater(np.sqrt(np.mean(low**2)), .27)
        self.assertLess(np.sqrt(np.mean(high**2)), .001)

    def test_downmix_has_no_int_overflow_and_both_channels_contribute(self):
        for side in (0, 1):
            stereo = np.zeros((4800, 2))
            stereo[:, side] = .8
            result = StereoResampler().convert(pcm(stereo))
            self.assertAlmostEqual(float(result[-1]), .4, places=5)
        with self.assertRaises(ValueError):
            StereoResampler().convert(b'bad')

    def test_gap_overflow_disconnect_reset_generation_and_queue(self):
        clock = [1.]
        pending = queue.Queue(maxsize=2)
        state = RecognitionState(pending, clock=lambda: clock[0])
        raw = pcm(np.ones((4800, 2)) * .1)
        state.update(raw)
        initial = pending.get_nowait()
        clock[0] += .1
        state.update(raw)
        clock[0] += .6
        state.update(raw)
        self.assertTrue(pending.empty())
        clock[0] += .31
        state.update(raw)
        after_gap = pending.get_nowait()
        self.assertGreater(after_gap[3], initial[3])
        self.assertTrue(pending.empty())
        for _ in range(3):
            clock[0] += .1
            state.update(raw)
        self.assertEqual(pending.qsize(), 1)
        state.disconnect('offline')
        self.assertTrue(pending.empty())
        self.assertFalse(state.snapshot()['connected'])
        self.assertEqual(state.snapshot()['inference_input'], 'pi_stereo')

    def test_normal_network_batching_does_not_destroy_valid_audio_windows(self):
        clock = [1.]
        pending = queue.Queue(maxsize=5)
        state = RecognitionState(pending, clock=lambda: clock[0])
        raw = pcm(np.zeros((4800, 2)))
        state.update(raw)
        seq = state.sequence
        clock[0] += .001
        state.update(raw)
        self.assertEqual(pending.qsize(), 2)
        self.assertEqual(state.sequence, seq+1)
        self.assertEqual(pending.get_nowait()[3],pending.get_nowait()[3])

    def test_coalesced_live_blocks_build_a_complete_recognition_window(self):
        clock = [1.]
        pending = queue.Queue(maxsize=40)
        state = RecognitionState(pending,clock=lambda:clock[0])
        raw = pcm(np.zeros((4800,2)))
        generations=[]
        samples=0
        for i in range(20):
            # Two blocks arrive together every 200ms, as observed over actual SSH.
            if i % 2 == 0:
                clock[0]+=.2
            state.update(raw)
            block, captured, wall, generation, evidence = pending.get_nowait()
            samples+=len(block)
            generations.append(generation)
        self.assertEqual(samples,32000)
        self.assertEqual(len(set(generations)),1)


if __name__ == '__main__':
    unittest.main()
