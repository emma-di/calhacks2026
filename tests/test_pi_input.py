import queue
import unittest
import numpy as np

from audio.pi_input import RecognitionState, StereoResampler


def pcm(data):
    return (np.clip(data, -1, .999999) * 2**31).astype('<i4').tobytes()


class PiInputTests(unittest.TestCase):
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
        clock[0] += .5
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

    def test_network_burst_discarded_instead_of_fresh_quiet_evidence(self):
        clock = [1.]
        pending = queue.Queue(maxsize=5)
        state = RecognitionState(pending, clock=lambda: clock[0])
        raw = pcm(np.zeros((4800, 2)))
        state.update(raw)
        seq = state.sequence
        clock[0] += .001
        state.update(raw)
        self.assertTrue(pending.empty())
        self.assertEqual(state.sequence, seq)


if __name__ == '__main__':
    unittest.main()
