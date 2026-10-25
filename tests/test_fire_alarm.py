import unittest
from audio.events import Detector, load_policy
from audio.alerts import AlertEngine


class FireAlarmMappingTests(unittest.TestCase):
    def test_fire_and_smoke_labels_feed_same_urgent_cue(self):
        for model in ('zipformer', 'yamnet'):
            for label in ('Fire alarm', 'Smoke detector, smoke alarm'):
                with self.subTest(model=model, label=label):
                    detector = Detector(policy=load_policy(model_name=model))
                    events = detector.detect({label: .95, 'Bell': .9}, 'simulation', now=0)
                    self.assertEqual([e['type'] for e in events], ['smoke_alarm'])
                    engine = AlertEngine()
                    decision = engine.add(events[0], 0)
                    self.assertEqual(decision['priority_tier'], 4)
                    self.assertEqual(engine.presentation(0)['icon_id'], 'smoke')

    def test_generic_alarm_and_alarm_clock_are_not_fire_evidence(self):
        for model in ('zipformer', 'yamnet'):
            events = Detector(policy=load_policy(model_name=model)).detect(
                {'Alarm': .99, 'Alarm clock': .9}, 'simulation', now=0)
            self.assertNotIn('smoke_alarm', [e['type'] for e in events])
