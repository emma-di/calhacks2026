import unittest
import numpy as np
from audio.pi_spatial import frame_evidence, window_evidence, annotate_events, unknown, assumed_front
from audio.events import make_event
from audio.server import AlertState


def signal(lag=0, left_gain=1., right_gain=1.):
    data = np.random.default_rng(42).normal(0, .015, 4800)
    other = np.roll(data, lag)
    return (np.column_stack((data*left_gain, other*right_gain))*2**31).astype('<i4').tobytes()


class PiSpatialTests(unittest.TestCase):
    def test_small_level_difference_still_localizes_by_arrival_time(self):
        left = frame_evidence(signal(lag=8, right_gain=.99))
        right = frame_evidence(signal(lag=-8, left_gain=.99))
        self.assertEqual(left['side'], 'left')
        self.assertEqual(right['side'], 'right')
        self.assertEqual(left['reason'], 'lateral_arrival_time')
        self.assertLess(abs(left['difference_db']), .2)

    def test_quiet_but_coherent_alarm_evidence_is_not_discarded_by_loudness(self):
        raw=np.frombuffer(signal(lag=8),dtype='<i4').astype(np.float64)
        raw=(raw*.02).astype('<i4').tobytes()
        self.assertEqual(frame_evidence(raw)['side'],'left')

    def test_balanced_zero_delay_and_impossible_delay_are_unknown(self):
        for lag in (0, 1, 25, -25):
            with self.subTest(lag=lag):
                self.assertIsNone(frame_evidence(signal(lag))['side'])

    def test_rejected_zero_delay_is_visible_without_inventing_a_side(self):
        result = frame_evidence(signal())
        self.assertIsNone(result['side'])
        self.assertEqual(result['timing_peak_lag_samples'], 0)
        self.assertEqual(result['timing_rejection'], 'near_zero_delay')
        delayed = frame_evidence(signal(lag=8))
        self.assertEqual(delayed['timing_peak_lag_samples'], -8)
        self.assertIsNone(delayed['timing_rejection'])

    def test_level_difference_fallback_and_gain_compensation(self):
        self.assertEqual(frame_evidence(signal(right_gain=.7))['side'], 'left')
        self.assertEqual(frame_evidence(signal(left_gain=.7))['side'], 'right')
        self.assertIsNone(frame_evidence(signal(right_gain=.7), gain_offset_db=3.1)['side'])

    def test_contradictory_timing_and_level_evidence_is_unknown(self):
        self.assertEqual(frame_evidence(signal(lag=8, left_gain=.4))['reason'], 'timing_level_conflict')

    def test_silence_dead_dc_clipped_and_bad_frames_are_unknown(self):
        for raw in (b'', b'bad', bytes(4800*8), np.tile([2**30, 0],4800).astype('<i4').tobytes(),
                    np.tile([2**31-1, 2**31-1],4800).astype('<i4').tobytes(),bytes(8)):
            self.assertIsNone(frame_evidence(raw)['side'])

    def test_uncorrelated_concurrent_audio_is_unknown(self):
        rng = np.random.default_rng(88)
        stereo = rng.normal(0, .01, (4800,2)) * [2.,1.]
        self.assertEqual(frame_evidence((stereo*2**31).astype('<i4').tobytes())['reason'], 'inconsistent_channels')

    def test_sustained_evidence_no_holding_through_silence_or_side_change(self):
        left = frame_evidence(signal(8))
        right = frame_evidence(signal(-8))
        quiet = unknown('quiet')
        self.assertEqual(window_evidence([left]*3)['side'], 'left')
        self.assertIsNone(window_evidence([left]*2)['side'])
        self.assertIsNone(window_evidence([left]*4+[quiet])['side'])
        self.assertIsNone(window_evidence([left]*4+[right])['side'])
        self.assertIsNone(window_evidence([quiet]*18+[left]*2)['side'])

    def test_competing_detections_do_not_inherit_one_direction(self):
        events = [make_event('knock',.9,'microphone'),make_event('smoke_alarm',.9,'microphone')]
        annotate_events(events,window_evidence([frame_evidence(signal(8))]*5), competing=True)
        self.assertTrue(all(event['direction_degrees'] == 0 and event['direction_assumed_front'] for event in events))

    def test_classified_alarm_beep_pauses_do_not_erase_same_window_direction(self):
        left = frame_evidence(signal(8))
        quiet = unknown('quiet')
        frames = [left]+[quiet]*4+[left]+[quiet]*4+[left]+[quiet]*9
        self.assertEqual(window_evidence(frames,require_current=False)['side'],'left')
        self.assertIsNone(window_evidence(frames)['side'])
        self.assertIsNone(window_evidence([quiet]*20,require_current=False)['side'])

    def test_one_noisy_frame_does_not_veto_an_entire_classified_alarm(self):
        left=frame_evidence(signal(8)); right=frame_evidence(signal(-8))
        self.assertEqual(window_evidence([left]*9+[right]+[left]*10,require_current=False)['side'],'left')
        self.assertIsNone(window_evidence([left]*10+[right]*10,require_current=False)['side'])

    def test_fire_alarm_drives_existing_left_right_triangles(self):
        for lag, side, degrees in ((16,'left',-90),(-16,'right',90)):
            event = make_event('smoke_alarm',.9,'microphone')
            annotate_events([event],window_evidence([frame_evidence(signal(lag))]*20))
            state = AlertState()
            state.add(event,now=1.)
            result = state.snapshot(now=1.)
            self.assertEqual(result['direction'],side)
            self.assertEqual(result['active']['direction_degrees'],degrees)

    def test_phone_never_fills_unknown_pi_direction(self):
        state = AlertState()
        state.spatial_reading(dict(bearing_degrees=90,coherence=.9,rms=.1,calibrated=True,device='phone'),now=1.)
        event = make_event('smoke_alarm',.9,'microphone')
        annotate_events([event],unknown('ambiguous'))
        state.add(event,now=1.1)
        self.assertEqual(state.snapshot(now=1.1)['direction'],'front')
        self.assertEqual(state.snapshot(now=1.1)['active']['direction_source'],'pi_stereo')

    def test_front_branch_rough_angles_use_existing_display_steps(self):
        angles=[]
        for lag in (-18,-16,-13,-8,-2,2,8,13,16,18):
            frame=frame_evidence(signal(lag))
            window=window_evidence([frame]*20)
            angle=window['direction_degrees']; angles.append(angle)
            self.assertIsNotNone(angle)
            self.assertGreaterEqual(angle,-90); self.assertLessEqual(angle,90)
            self.assertEqual(angle % 45.,0)
            self.assertTrue(window['front_assumed'])
        self.assertGreaterEqual(len(set(angles)),5)

    def test_front_fallback_is_explicit_and_silence_does_not_gain_evidence(self):
        result=assumed_front(unknown('competing_sides'))
        self.assertEqual(result['direction_degrees'],0)
        self.assertTrue(result['front_assumed'])
        self.assertIn('assumed_front',result['reason'])
        self.assertIsNone(frame_evidence(bytes(4800*8))['direction_degrees'])


if __name__ == '__main__':
    unittest.main()
