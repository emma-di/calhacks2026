"""Approved cue wiring, independent of microphone/model accuracy or physical hardware."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from audio.alerts import DEFAULT_PROFILE
from audio.custom_rules import CustomRules
from audio.events import Detector, EVENT_TYPES, load_policy, validate_event
from audio.server import AlertState
from hardware.display import ICON_IDS, Presentation, render

ROOT = Path(__file__).resolve().parents[1]
CUES = json.loads((ROOT / 'audio/cue-catalog.json').read_text())['cues']
ENVIRONMENTAL = [cue for cue in CUES if cue['model_labels']]
CUSTOM = [cue for cue in CUES if cue['event_type'] == 'custom']


def selection(cue, tier):
    return dict(id='qa-' + cue['id'], cue_id=cue['id'], label=cue['label'], tier=tier,
                status='recognized', model_labels=cue['model_labels'], icon=cue['icon_id'],
                threshold=cue['threshold'])


class CueCatalogPipelineTests(unittest.TestCase):
    def test_catalog_ids_labels_and_icons_are_distinct(self):
        self.assertEqual(len(CUES), 50)
        for field in ('id', 'icon_id'):
            self.assertEqual(len({cue[field] for cue in CUES}), 50)
        self.assertEqual([cue['id'] for cue in CUES if not cue['model_labels']], ['name_called'])
        self.assertTrue({cue['icon_id'] for cue in CUES}.issubset(ICON_IDS))
        assets = json.loads((ROOT / 'hardware/oled-assets.json').read_text())['bitmaps']
        self.assertEqual(len({tuple(assets[cue['icon_id']]) for cue in CUES}), 50,
                         'Each approved cue needs a distinct bitmap, not only a distinct ID')

    def test_name_speech_event_contract_reaches_its_cue_at_every_tier(self):
        """Synthetic speech-worker event tests delivery, not name-recognizer accuracy."""
        cue = next(cue for cue in CUES if cue['id'] == 'name_called')
        for tier in range(5):
            with self.subTest(tier=tier), tempfile.TemporaryDirectory() as folder:
                receiver = AlertState(profile_path=Path(folder) / 'profile.json')
                profile = copy.deepcopy(DEFAULT_PROFILE)
                profile['notification_preferences']['event_tiers']['name_called'] = tier
                receiver.save_profile(profile)
                event = dict(schema_version=2, event_id='synthetic-speech-name', type='name_called',
                             label='Your name', source='simulation', recognizer='qa-speech-contract',
                             confidence=None, confidence_kind='unavailable', matched_alias_id='primary',
                             profile_revision=1, priority_tier=3, timestamp_ms=0,
                             direction_degrees=None, direction_confidence=None, distance_meters=None,
                             proximity='unknown')
                receiver.add(validate_event(event), now=0)
                parsed = Presentation.parse(receiver.presentation(now=0))
                self.assertEqual(parsed.effective_tier, tier)
                self.assertEqual(parsed.icon_id, cue['icon_id'] if tier else None)
                self.assertEqual(bool(any(render(parsed).buffer)), bool(tier))

    def test_each_selected_environmental_cue_reaches_receiver_and_pixels_at_every_tier(self):
        for cue in ENVIRONMENTAL:
            for tier in range(5):
                with self.subTest(cue=cue['id'], tier=tier), tempfile.TemporaryDirectory() as folder:
                    path = Path(folder) / 'profile.json'
                    receiver = AlertState(profile_path=path)
                    profile = copy.deepcopy(DEFAULT_PROFILE)
                    if cue['event_type'] == 'custom':
                        profile['custom_sound_requests'] = [selection(cue, tier)]
                    else:
                        profile['notification_preferences']['event_tiers'][cue['event_type']] = tier
                    saved = receiver.save_profile(profile)
                    if cue['event_type'] == 'custom':
                        self.assertEqual(saved['custom_sound_requests'][0]['cue_id'], cue['id'])
                        rules = CustomRules(path)
                    else:
                        rules = Detector(policy=load_policy(model_name='zipformer'))
                    events = rules.detect({cue['model_labels'][0]: .95}, 'simulation', now=0)
                    if cue['id'] == 'bicycle_bell':
                        self.assertEqual(events, [], 'Bicycle subtype must remain disabled pending evidence')
                        continue
                    self.assertEqual(len(events), 1)
                    event = validate_event(events[0])
                    if cue['event_type'] == 'custom':
                        self.assertEqual(event['custom_sound_id'], 'qa-' + cue['id'])
                        self.assertEqual(event['icon_id'], cue['icon_id'])
                    else:
                        self.assertEqual(event['type'], cue['event_type'])
                    # A producer cannot overrule the saved per-selection priority.
                    event['priority_tier'] = (tier + 1) % 5
                    decision = receiver.add(event, now=0)
                    presentation = receiver.presentation(now=0)
                    parsed = Presentation.parse(presentation)
                    bitmap = render(parsed)
                    if tier == 0:
                        self.assertEqual(decision['reason'], 'ignored_tier_zero')
                        self.assertIsNone(parsed.icon_id)
                        self.assertFalse(any(bitmap.buffer))
                    else:
                        self.assertEqual(decision['priority_tier'], tier)
                        self.assertEqual(parsed.icon_id, cue['icon_id'])
                        self.assertEqual(parsed.label, cue['label'] if cue['event_type'] == 'custom'
                                         else EVENT_TYPES[cue['event_type']][0])
                        self.assertEqual(parsed.effective_tier, tier)
                        self.assertTrue(any(bitmap.buffer))

    def test_all_43_custom_selections_survive_one_profile_save_and_only_matching_cue_fires(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            receiver = AlertState(profile_path=path)
            profile = copy.deepcopy(DEFAULT_PROFILE)
            profile['custom_sound_requests'] = [selection(cue, cue['default_tier']) for cue in CUSTOM]
            saved = receiver.save_profile(profile)
            self.assertEqual(len(saved['custom_sound_requests']), 43)
            rules = CustomRules(path)
            self.assertEqual(len(rules.rules), 43)
            self.assertEqual(rules.detect({}, 'simulation', now=0), [])
            for cue in CUSTOM:
                for label in cue['model_labels']:
                    with self.subTest(cue=cue['id'], label=label):
                        rules.last.clear()
                        events = rules.detect({label: .95}, 'simulation', now=0)
                        self.assertEqual({event['custom_sound_id'] for event in events}, {'qa-' + cue['id']})


if __name__ == '__main__':
    unittest.main()
