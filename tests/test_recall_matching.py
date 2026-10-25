"""Recall-first selected cues: sibling labels are explicit, explainable fallbacks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from audio.alerts import DEFAULT_PROFILE, validate_profile, AlertEngine
from audio.cue_catalog import CUES_BY_ID
from audio.custom_rules import CustomRules
from audio.events import EVENT_TYPES
from hardware.display import Presentation, render

class RecallMatchingTests(unittest.TestCase):
    def rules(self, ids):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        p=copy.deepcopy(DEFAULT_PROFILE)
        p['custom_sound_requests']=[dict(id=key,cue_id=key,label=CUES_BY_ID[key]['label'],tier=3,
            status='recognized',model_labels=CUES_BY_ID[key]['model_labels'],
            threshold=CUES_BY_ID[key]['threshold']) for key in ids]
        p=validate_profile(p,EVENT_TYPES)
        path=Path(tmp.name)/'profile.json';path.write_text(json.dumps(p))
        return CustomRules(path),p

    def test_observed_truck_horn_can_reach_selected_train_cue_without_training(self):
        rules,p=self.rules(['train_horn'])
        event=rules.detect({'Air horn, truck horn':.353019,'Train horn':.000075},'simulation',now=0)[0]
        self.assertEqual(event['recognition_match'],'related_label')
        self.assertEqual(event['matched_model_label'],'Air horn, truck horn')
        self.assertEqual(event['label'],'Horn — possibly train')
        self.assertEqual(event['custom_sound_id'],'train_horn')
        engine=AlertEngine(profile=p);engine.add(event,0)
        cue=Presentation.parse(engine.presentation(0))
        self.assertEqual(cue.icon_id,'cue_train_horn')
        self.assertEqual(cue.effective_tier,3)
        self.assertTrue(any(render(cue).buffer))
        self.assertEqual(rules.decisions[0]['match_kind'],'related_label')

    def test_exact_selected_horn_wins_over_related_subtype_and_primary_keeps_label(self):
        rules,_=self.rules(['train_horn','truck_horn'])
        events=rules.detect({'Air horn, truck horn':.8},'simulation',now=0)
        self.assertEqual([e['custom_sound_id'] for e in events],['truck_horn'])
        self.assertEqual(events[0]['label'],CUES_BY_ID['truck_horn']['label'])
        self.assertEqual(events[0]['recognition_match'],'primary_label')

    def test_sensitive_primary_threshold_catches_point_two_but_background_stays_quiet(self):
        rules,_=self.rules(['breaking','saxophone','clap'])
        events=rules.detect({'Breaking':.20,'Saxophone':.16},'simulation',now=0)
        self.assertEqual({e['custom_sound_id'] for e in events},{'breaking','saxophone'})
        self.assertEqual(rules.detect({'Music':.99,'Speech':.9},'simulation',now=1),[])
        self.assertEqual(rules.detect({'Applause':.20},'simulation',now=2),[])
        self.assertEqual(rules.detect({'Applause':.4},'simulation',now=3)[0]['custom_sound_id'],'clap')

    def test_each_configured_fallback_has_real_model_label_and_reaches_its_selected_cue(self):
        from audio.custom_rules import LABEL_ICONS
        for cue in CUES_BY_ID.values():
            for label in cue.get('fallback_labels',[]):
                with self.subTest(cue=cue['id'],label=label):
                    self.assertIn(label,LABEL_ICONS)
                    rules,_=self.rules([cue['id']])
                    events=rules.detect({label:.8},'simulation',now=0)
                    self.assertEqual(events[0]['custom_sound_id'],cue['id'])
                    self.assertEqual(events[0]['matched_model_label'],label)
