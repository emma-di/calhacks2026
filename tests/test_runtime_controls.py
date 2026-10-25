import io
import json
import unittest
from unittest.mock import patch, Mock
from audio.runtime_controls import RecognitionControls
from audio.events import Detector
from audio.names import NameDetector


class RepeatTestingTests(unittest.TestCase):
    def test_runtime_toggle_polls_and_fails_back_to_normal(self):
        control = RecognitionControls('http://127.0.0.1:8766/events')
        with patch('audio.runtime_controls.time.monotonic', side_effect=[0, .2, 2]), patch(
                'audio.runtime_controls.urlopen', side_effect=[io.BytesIO(json.dumps(
                    dict(repeat_suppression=False, snap_to_dismiss=True, active_event_id='cue-1')).encode()), OSError('offline')]) as fetch:
            self.assertFalse(control.refresh())
            self.assertTrue(control.snap_to_dismiss)
            self.assertEqual(control.active_event_id, "cue-1")
            self.assertFalse(control.refresh())
            self.assertTrue(control.refresh())
            self.assertFalse(control.snap_to_dismiss)
            self.assertIsNone(control.active_event_id)
            self.assertEqual(fetch.call_count, 2)

    def test_built_in_cooldown_can_be_bypassed_and_restored(self):
        detector = Detector(policy=dict(cooldown_seconds=5, rules={
            'knock': dict(labels={'Knock': 1}, threshold=.5)}))
        self.assertEqual(len(detector.detect({'Knock': .9}, 'mock', now=0)), 1)
        self.assertEqual(detector.detect({'Knock': .9}, 'mock', now=1), [])
        detector.repeat_suppression = False
        self.assertEqual(len(detector.detect({'Knock': .9}, 'mock', now=2)), 1)
        detector.repeat_suppression = True
        self.assertEqual(detector.detect({'Knock': .9}, 'mock', now=3), [])

    def test_name_cooldown_bypass_does_not_need_model_or_microphone(self):
        detector = NameDetector.__new__(NameDetector)
        detector.maybe_reload = Mock()
        detector.stream = Mock()
        detector.spotter = Mock()
        detector.spotter.get_result.return_value = 'primary'
        detector.cooldown = 5
        detector.last = 0
        detector.profile = {'revision': 1}
        for suppress, expected in [(True, 0), (False, 1), (True, 0)]:
            detector.repeat_suppression = suppress
            detector.spotter.is_ready.side_effect = [True, False]
            with patch('audio.names.make_name_event', return_value={'event_id':'n'}):
                self.assertEqual(len(detector.accept([], 'mock', now=1)), expected)
            self.assertEqual(detector.decisions[0]['reason'], 'cooldown' if suppress else 'emitted')

    def test_receiver_session_controls_and_invalid_request_are_atomic(self):
        from audio.server import AlertState
        state = AlertState()
        self.assertTrue(state.snapshot()['repeat_suppression'])
        state.controls(repeat_suppression=False)
        self.assertFalse(state.health()['repeat_suppression'])
        with self.assertRaises(ValueError):
            state.controls(focus_mode='dnd', repeat_suppression='off')
        self.assertEqual(state.snapshot()['focus_mode'], 'everyday')
        self.assertFalse(state.snapshot()['repeat_suppression'])
        self.assertTrue(AlertState().health()['repeat_suppression'])
