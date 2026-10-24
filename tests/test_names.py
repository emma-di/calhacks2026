"""Name-detection tests. NumPy only: no speech model, sentencepiece or microphone."""
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from audio import names, server
from audio.events import validate_event
from audio.server import AlertState

VOCAB = {'▁YOU', '▁MEAN', '▁ME', '▁JO', 'H', 'N', '▁E', 'M', 'MA', '▁', 'Y', 'E', '▁WHY', '▁DON', "'", 'T', '▁AND', '▁THE', '▁SAID', 'AR', 'TH', '▁A', 'R'}

class ProfileTests(unittest.TestCase):
    def test_validation_and_normalization(self):
        p = names.validate_profile({'display_name': '  José  Luis ', 'name_detection': {'enabled': True, 'aliases': ['JL']},
                                    'notification_preferences': {'mode': 'balanced'}})
        self.assertEqual(p['name_detection']['primary_name'], 'José Luis')   # falls back to display name
        self.assertEqual(p['notification_preferences'], {'mode': 'balanced'})  # other workstreams' keys kept
        self.assertEqual(p['name_detection']['sensitivity'], 'balanced')
        bad = [{'name_detection': {'enabled': True}},                      # no name
               {'name_detection': {'enabled': 'yes', 'primary_name': 'A'}},
               {'name_detection': {'primary_name': 'A', 'aliases': ['']}},
               {'name_detection': {'primary_name': 'A', 'aliases': ['x']*9}},
               {'name_detection': {'primary_name': 'A', 'language': 'fr'}},
               {'name_detection': {'primary_name': 'A', 'sensitivity': 'max'}},
               {'name_detection': {'primary_name': 'bad\nname'}},
               {'name_detection': {'primary_name': 'A', 'learned_spellings': [{'text': 'x'}]}}, []]
        for profile in bad:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                names.validate_profile(profile)

    def test_spoken_form(self):
        self.assertEqual(names.spoken_form('José-Luis'), 'JOSE LUIS')
        self.assertEqual(names.spoken_form("O'Brien"), "O'BRIEN")
        self.assertEqual(names.spoken_form('李'), '')

    def test_reads_the_receiver_profile(self):
        from audio.alerts import DEFAULT_PROFILE
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(names, 'PROFILE', Path(tmp)/'profile.json'):
            self.assertEqual(names.load_profile()['revision'], 0)
            saved = json.loads(json.dumps(DEFAULT_PROFILE))
            saved['name_detection'].update(enabled=True, primary_name='Ann', sensitivity='high')
            saved['revision'] = 4
            (Path(tmp)/'profile.json').write_text(json.dumps(saved))
            loaded = names.load_profile()
            self.assertEqual((loaded['revision'], loaded['name_detection']['sensitivity']), (4, 'high'))
            self.assertEqual(loaded['notification_preferences'], saved['notification_preferences'])

class ProfileCompatibilityTests(unittest.TestCase):
    """(Emma) The receiver's /profile (audio/alerts.py) is the shared one; the name spotter must read what it saves."""
    def test_receiver_saved_profile_drives_the_name_spotter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'profile.json'
            state = AlertState(profile_path=path)
            profile = dict(schema_version=1, profile_id='demo', notification_preferences=dict(mode='balanced'),
                           name_detection=dict(enabled=True, primary_name='Samira', aliases=['Sam'],
                                               sensitivity='high', learned_spellings=[]))
            saved = state.save_profile(profile)
            self.assertEqual(saved['name_detection']['sensitivity'], 'high')
            with mock.patch.object(names, 'PROFILE', path):
                loaded = names.load_profile()
            self.assertTrue(loaded['name_detection']['enabled'])
            self.assertEqual(loaded['name_detection']['primary_name'], 'Samira')
            self.assertEqual(loaded['name_detection']['aliases'], ['Sam'])


class SpellingTests(unittest.TestCase):
    def setUp(self):
        self.patches = [mock.patch.object(names, 'model_vocabulary', return_value=VOCAB),
                        mock.patch.object(names, '_common', None)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_common_words_are_rejected_or_stripped(self):
        self.assertEqual(names.safe_spelling(['▁', 'Y', 'E', 'M', 'Y'])[:2], (['▁', 'Y', 'E', 'M', 'Y'], None))
        self.assertEqual(names.safe_spelling(['▁AND', '▁E', 'M', 'MA', '▁THE'])[0], ['▁E', 'M', 'MA'])
        self.assertIsNone(names.safe_spelling(['▁WHY'])[0])                       # Wei -> "why"
        self.assertIsNone(names.safe_spelling(['▁DON', "'", 'T'])[0])             # John -> "don't"
        self.assertIsNone(names.safe_spelling(['▁A', 'R'])[0])                    # too short
        self.assertEqual(names.safe_spelling(['▁GRACE'], allowed={'GRACE'})[0], ['▁GRACE'])

    def test_repeats_collapse_and_common_phrases_warn(self):
        # Yameen said three times in one recording, heard as "you mean you mean you mean".
        tokens, problem, warning = names.safe_spelling(['▁YOU', '▁MEAN']*3)
        self.assertEqual((tokens, problem), (['▁YOU', '▁MEAN'], None))
        self.assertIn('you mean', warning)
        tokens, _, _ = names.safe_spelling(['▁', 'Y', 'E', 'M', 'Y', '▁', 'Y', 'E', 'M', 'Y', '▁AND'])
        self.assertEqual(tokens, ['▁', 'Y', 'E', 'M', 'Y'])
        tokens, _, _ = names.safe_spelling(['▁YOU', '▁MEAN', '▁YOU', '▁ME', '▁YOU', '▁MEAN'])
        self.assertEqual(tokens, ['▁YOU', '▁MEAN'])                               # near-repeats: most frequent phrase
        self.assertIsNotNone(names.safe_spelling(['▁SAID', '▁E', 'AR', 'TH'])[2])  # all common: kept, warned
        self.assertEqual(names.safe_spelling(['▁E', 'M', 'MA', '▁WHY'])[:2], (['▁E', 'M', 'MA'], None))
        # Several attempts that differ: the distinctive word wins over a repeated everyday phrase.
        heard = ['▁YOU', '▁MEAN', '▁', 'Y', 'A', 'M', 'I', 'N', 'G', '▁YOU', '▁MEAN']
        self.assertEqual(names.safe_spelling(heard)[:2], (['▁', 'Y', 'A', 'M', 'I', 'N', 'G'], None))

    def test_keyword_lines_use_sensitivity_and_skip_unknown_tokens(self):
        profile = names.validate_profile({'name_detection': {
            'enabled': True, 'primary_name': 'John', 'sensitivity': 'high',
            'learned_spellings': [{'text': 'YEMY', 'tokens': '▁ Y E M Y'}, {'text': 'ZZ', 'tokens': '▁ZZ Q'}]}})
        with mock.patch.object(names, 'tokenize', side_effect=lambda t: {'JOHN': ['▁JO', 'H', 'N']}[t]):
            lines = names.keyword_lines(profile)
        self.assertEqual(lines, ['▁JO H N :2.0 #0.1 @primary', '▁ Y E M Y :2.0 #0.1 @learned-0'])

class EventTests(unittest.TestCase):
    profile = dict(revision=3)

    def test_name_event_validates_and_outranks_tier_2(self):
        from audio.events import make_event
        event = names.make_name_event(self.profile, 'primary', 'microphone')
        self.assertIsNone(validate_event(event)['confidence'])
        state = AlertState()
        state.add(make_event('knock', .9, 'mock'))
        state.add(event)
        self.assertEqual(state.snapshot()['active']['type'], 'name_called')
        state.add(make_event('smoke_alarm', .9, 'mock'))
        state.add(names.make_name_event(self.profile, 'primary', 'microphone'))
        self.assertEqual(state.snapshot()['active']['type'], 'smoke_alarm')   # cannot replace tier 4

    def test_name_event_rules(self):
        for change in ({'schema_version': 1}, {'confidence': 1.5}, {'priority_tier': 7}, {'profile_revision': -1},
                       {'matched_alias_id': ''}, {'direction_degrees': 10}, {'distance_meters': 2}):
            event = dict(names.make_name_event(self.profile, 'primary', 'replay'), **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_event(event)

class ProfileRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(names, 'PROFILE', Path(self.tmp.name)/'profile.json')
        self.patch.start()
        self.httpd = server.create_server(port=0, profile_path=Path(self.tmp.name)/'profile.json')
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.patch.stop()
        self.tmp.cleanup()

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(self.base+path, data=data, method=method,
                          headers={'Content-Type': 'application/json', 'Origin': 'http://localhost:3000'} if data else {})
        try:
            with urlopen(request) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_receiver_profile_keeps_name_fields_and_detector_sees_them(self):
        status, profile = self.call('GET', '/profile')
        self.assertEqual((status, profile['name_detection']['enabled']), (200, False))
        profile['name_detection'].update(enabled=True, primary_name='Samira', aliases=['Sam'], sensitivity='high',
                                         learned_spellings=[{'text': 'SAMIRAH', 'tokens': '▁SA MI RA H'}])
        status, saved = self.call('PUT', '/profile', profile)
        self.assertEqual((status, saved['revision']), (200, 1))
        self.assertEqual(saved['name_detection']['sensitivity'], 'high')
        self.assertEqual(saved['name_detection']['learned_spellings'][0]['text'], 'SAMIRAH')
        self.assertEqual(names.load_profile()['name_detection']['aliases'], ['Sam'])   # the worker's view
        bad = json.loads(json.dumps(profile)); bad['name_detection']['sensitivity'] = 'max'
        status, saved = self.call('PUT', '/profile', bad)   # invalid name settings are dropped, never fatal
        self.assertEqual(status, 200)
        self.assertNotEqual(saved['name_detection'].get('sensitivity'), 'max')
        self.assertEqual(self.call('DELETE', '/profile/name-samples')[1]['name_detection']['learned_spellings'], [])
        self.assertIn(self.call('GET', '/health')[1]['name_worker'], ('model_missing', 'idle'))

    def test_companion_saves_do_not_erase_learned_spellings(self):
        _, profile = self.call('GET', '/profile')
        profile['name_detection'].update(enabled=True, primary_name='Yameen', sensitivity='high',
                                         learned_spellings=[{'text': 'YEMY', 'tokens': '▁ Y E M Y'}])
        self.call('PUT', '/profile', profile)
        # What the companion's onboarding sends: name, aliases and language only.
        companion = json.loads(json.dumps(profile))
        companion['name_detection'] = dict(enabled=True, primary_name='Yameen', aliases=['Yam'], language='en')
        companion['notification_preferences']['mode'] = 'gentle'
        _, saved = self.call('PUT', '/profile', companion)
        self.assertEqual(saved['name_detection']['learned_spellings'][0]['text'], 'YEMY')
        self.assertEqual((saved['name_detection']['sensitivity'], saved['name_detection']['aliases']), ('high', ['Yam']))
        self.assertEqual(saved['notification_preferences']['mode'], 'gentle')
        companion['name_detection']['primary_name'] = 'Priya'   # a different name: old spellings no longer apply
        _, saved = self.call('PUT', '/profile', companion)
        self.assertEqual((saved['name_detection']['learned_spellings'], saved['name_detection']['sensitivity']), ([], 'high'))

if __name__ == '__main__':
    unittest.main()
