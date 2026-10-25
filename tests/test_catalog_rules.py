import copy
import json
from pathlib import Path
import tempfile
import unittest
from audio.alerts import AlertEngine, DEFAULT_PROFILE, validate_profile
from audio.events import EVENT_TYPES, validate_event
from audio.custom_rules import CustomRules


def profile(tier=2):
    p=copy.deepcopy(DEFAULT_PROFILE)
    p['custom_sound_requests']=[dict(id='whistle',label='Whistling',tier=tier,status='recognized',model_labels=['Whistling'])]
    return p


class CatalogRulesTests(unittest.TestCase):
    def test_selected_rule_flows_into_receiver_and_profile_priority_wins(self):
        p=validate_profile(profile(0),EVENT_TYPES)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';path.write_text(json.dumps(p));rules=CustomRules(path)
            event=validate_event(rules.detect({'Whistling':.9},'simulation',now=0)[0])
            self.assertEqual(event['icon_id'],p['custom_sound_requests'][0]['icon'])
            event['priority_tier']=4
            engine=AlertEngine(profile=p)
            self.assertEqual(engine.add(event,0)['reason'],'ignored_tier_zero')
            self.assertIsNone(engine.presentation(0)['icon_id'])
            p['custom_sound_requests'][0]['tier']=3
            engine.set_profile(p)
            rules.repeat_suppression=False
            event=rules.detect({'Whistling':.9},'simulation',now=1)[0]
            self.assertEqual(engine.add(event,1000)['priority_tier'],3)
            self.assertEqual(engine.presentation(1000)['icon_id'],event['icon_id'])

    def test_pending_does_not_detect_and_deleting_rule_stops_recognition(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'profile.json';p=profile();p['custom_sound_requests'][0]={'id':'whistle','label':'Whistling','tier':2,'status':'pending'}
            path.write_text(json.dumps(p));rules=CustomRules(path)
            self.assertEqual(rules.detect({'Whistling':1},'simulation',now=0),[])
            path.write_text(json.dumps(profile()));rules.reload(force=True)
            self.assertEqual(len(rules.detect({'Whistling':1},'simulation',now=1)),1)
            path.write_text(json.dumps(DEFAULT_PROFILE));rules.reload(force=True)
            self.assertEqual(rules.detect({'Whistling':1},'simulation',now=2),[])

    def test_validation_rejects_unknown_labels_and_duplicate_ids(self):
        for change in ({'model_labels':['imaginary model sound']},{'model_labels':[]},{'threshold':0},{'threshold':float('nan')},{'status':'pretend'}):
            p=profile();p['custom_sound_requests'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):validate_profile(p,EVENT_TYPES)
        p=profile();p['custom_sound_requests'].append(dict(p['custom_sound_requests'][0],label='Other whistle'))
        with self.assertRaises(ValueError):validate_profile(p,EVENT_TYPES)
