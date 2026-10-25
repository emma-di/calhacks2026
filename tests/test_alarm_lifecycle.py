import json
import time
import unittest
from audio.events import make_event
from audio.server import AlertState


def observation(source='microphone', present=False):
    return dict(source=source, timestamp_ms=int(time.time()*1000), rules={
        'smoke_alarm': dict(score=.9 if present else .01, threshold=.35, reason='emitted' if present else 'below_threshold')})


class AlarmLifecycleTests(unittest.TestCase):
    def state(self):
        state = AlertState()
        state.add(make_event('smoke_alarm', .9, 'microphone'), now=0)
        return state

    def test_continuous_quiet_clears_without_acknowledging_and_alarm_can_return(self):
        state = self.state()
        for at in (1,2,3,4):
            state.observe(observation(), now=at)
            self.assertIsNotNone(state.snapshot(now=at)['active'])
        state.observe(observation(), now=5)
        self.assertIsNone(state.snapshot(now=5)['active'])
        self.assertEqual(state.decisions[-1]['reason'], 'sound_stopped')
        self.assertFalse(state.engine.acks)
        self.assertIsNone(state.snapshot(now=5)['confirm'])
        state.add(make_event('smoke_alarm', .9, 'microphone'), now=5.1)
        self.assertIsNotNone(state.snapshot(now=5.1)['active'])

    def test_capture_stall_and_other_source_are_not_proof_alarm_stopped(self):
        state = self.state()
        state.observe(observation(), now=1)
        self.assertIsNotNone(state.snapshot(now=10)['active'])
        # A gap in reports resets the quiet timer rather than treating missing reports as silence.
        state.observe(observation(), now=10)
        self.assertIsNotNone(state.snapshot(now=10)['active'])
        for at in (11,12,13,14):
            state.observe(observation(source='replay'), now=at)
        self.assertIsNotNone(state.snapshot(now=14)['active'])

    def test_stopped_alarm_resumes_a_fresh_queued_cue(self):
        state = self.state()
        state.add(make_event('knock', .9, 'microphone'), now=1)
        for at in (1,2,3,4,5): state.observe(observation(), now=at)
        self.assertEqual(state.snapshot(now=5)['active']['type'], 'knock')

    def test_stale_windows_and_missing_rule_do_not_clear_alarm(self):
        state = self.state()
        state.observe(dict(observation(), rules={}), now=1)
        self.assertNotIn('quiet_since', state.engine.active)
        state.observe(dict(observation(), timestamp_ms=1))
        self.assertNotIn('quiet_since', state.engine.active)
