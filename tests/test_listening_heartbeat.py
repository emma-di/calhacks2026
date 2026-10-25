import unittest
from unittest import mock
from audio import server
from audio.events import Detector
from audio.observations import build_observation


class ListeningHeartbeatTests(unittest.TestCase):
    def test_recent_observations_mean_listening_and_reach_the_state(self):
        store = server.ObservationStore()
        with mock.patch.object(server, 'observations', store):
            state = server.AlertState()
            self.assertFalse(state.health()['capture']['listening'])
            detector = Detector()
            scores = {'Speech': 0.7, 'Knock': 0.05}
            store.add(build_observation(scores, source='microphone', model='zipformer', timestamp_ms=1,
                                        inference_ms=20, window_rms=0.02, rule_decisions=detector.decisions
                                        or [], events=detector.detect(scores, 'microphone', now=0)))
            health = state.health()['capture']
            self.assertEqual((health['listening'], health['listening_source']), (True, 'microphone'))
            self.assertEqual(state.snapshot()['observations'][-1]['top'][0]['label'], 'Speech')
            store.items[-1]['received_ms'] -= 5000   # silence from the recognizer for 5 s
            self.assertFalse(state.health()['capture']['listening'])


if __name__ == '__main__':
    unittest.main()
