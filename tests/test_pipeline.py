import time
import unittest
from audio.events import Detector, make_event, validate_event
from audio.server import AlertState

class PipelineTests(unittest.TestCase):
    def test_threshold_cooldown_and_replay_clock(self):
        d = Detector()
        threshold=d.policy['rules']['knock']['threshold']
        self.assertEqual(d.detect({'Knock':threshold/2}, 'replay', now=0), [])
        self.assertEqual(len(d.detect({'Knock':.8}, 'replay', now=0)), 1)
        self.assertEqual(d.detect({'Knock':.8}, 'replay', now=1), [])
        self.assertEqual(len(d.detect({'Knock':.8}, 'replay', now=5)), 1)

    def test_invalid_scores(self):
        for score in (float('nan'), float('inf'), -1, 2, True):
            e = make_event('knock', .9, 'mock')
            e['confidence'] = score
            with self.assertRaises(ValueError):
                validate_event(e)

    def test_unknown_spatial_data_rejected(self):
        e = make_event('knock', .9, 'mock')
        e['direction_degrees'] = 45
        with self.assertRaises(ValueError):
            validate_event(e)

    def test_priority_and_expiry(self):
        s = AlertState()
        s.add(make_event('smoke_alarm', .9, 'mock'))
        s.add(make_event('dog_bark', .9, 'mock'))
        self.assertEqual(s.snapshot()['active']['type'], 'smoke_alarm')
        self.assertIsNone(s.snapshot(now=time.monotonic() + 31)['active'])

    def test_ignore(self):
        # Ignore is a saved preference; the receiver, not the producer, decides the tier.
        s = AlertState()
        s.engine.profile['notification_preferences']['event_tiers'] = {'knock': 0}
        s.add(make_event('knock', .9, 'mock'))
        self.assertIsNone(s.snapshot()['active'])
        self.assertEqual(s.snapshot()['decisions'][-1]['reason'], 'ignored_tier_zero')

    def test_custom_model_rules_are_applied(self):
        policy={'rules':{'dog_bark':{'labels':{'Bark':1,'Bow-wow':1},'threshold':.2}}}
        events=Detector(policy=policy).detect({'Bow-wow':.7},'simulation',now=0)
        self.assertEqual(events[0]['type'],'dog_bark')
        self.assertEqual(events[0]['confidence'],.7)

    def test_disabled_specificity_does_not_emit(self):
        policy={'rules':{'bicycle_bell':{'labels':{'Bicycle bell':1},'threshold':.1,'enabled':False}}}
        self.assertEqual(Detector(policy=policy).detect({'Bicycle bell':.9},'simulation',now=0),[])

    def test_specific_alarm_suppresses_generic_bell_in_same_window(self):
        policy={'rules':{'bell':{'labels':{'Bell':1},'threshold':.2,'suppressors':{'Alarm clock':.3}}}}
        d=Detector(policy=policy)
        self.assertEqual(d.detect({'Bell':.8,'Alarm clock':.9},'simulation',now=0),[])
        self.assertEqual(d.detect({'Bell':.8,'Alarm clock':.01},'simulation',now=1)[0]['type'],'bell')

    def test_alert_interruption_with_simulated_clock(self):
        s=AlertState()
        s.add(make_event('knock',.8,'simulation'),now=0)
        self.assertEqual(s.snapshot(now=1)['active']['type'],'knock')
        s.add(make_event('smoke_alarm',.8,'simulation'),now=1)
        s.add(make_event('dog_bark',.9,'simulation'),now=2)
        self.assertEqual(s.snapshot(now=2)['active']['type'],'smoke_alarm')
        self.assertEqual(s.snapshot(now=2)['decisions'][-1]['reason'],'suppressed_lower_priority')
        self.assertIsNone(s.snapshot(now=32)['active'])

    def test_alarm_tail_does_not_create_a_second_bell_alert(self):
        policy={'rules':{'bell':{'labels':{'Bell':1},'threshold':.2,
            'suppressors':{'Alarm clock':.3},'suppressor_hold_seconds':2}}}
        d=Detector(policy=policy)
        self.assertEqual(d.detect({'Bell':.8,'Alarm clock':.9},'simulation',now=0),[])
        self.assertEqual(d.detect({'Bell':.8,'Alarm clock':.01},'simulation',now=1),[])
        self.assertEqual(d.decisions[0]['reason'],'suppressed_recent_context')
        self.assertIn('Alarm clock',d.decisions[0]['recent_context']['labels'])
        self.assertEqual(d.detect({'Bell':.8,'Alarm clock':.01},'simulation',now=2)[0]['type'],'bell')

if __name__ == '__main__':
    unittest.main()
