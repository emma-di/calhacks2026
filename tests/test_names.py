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

VOCAB = {'▁JO', 'H', 'N', '▁E', 'M', 'MA', '▁', 'Y', 'E', '▁WHY', '▁DON', "'", 'T', '▁AND', '▁THE', '▁SAID', 'AR', 'TH', '▁A', 'R'}

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

    def test_save_bumps_revision_atomically(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(names, 'PROFILE', Path(tmp)/'profile.json'):
            self.assertEqual(names.load_profile()['revision'], 0)
            first = names.save_profile({'display_name': 'Ann'})
            second = names.save_profile(dict(first, display_name='Anne'))
            self.assertEqual((first['revision'], second['revision']), (1, 2))
            self.assertEqual(names.load_profile()['display_name'], 'Anne')
            self.assertFalse((Path(tmp)/'profile.tmp').exists())

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
        self.assertEqual(names.safe_spelling(['▁', 'Y', 'E', 'M', 'Y'])[0], ['▁', 'Y', 'E', 'M', 'Y'])
        self.assertEqual(names.safe_spelling(['▁AND', '▁E', 'M', 'MA', '▁THE'])[0], ['▁E', 'M', 'MA'])
        self.assertIsNone(names.safe_spelling(['▁WHY'])[0])                       # Wei -> "why"
        self.assertIsNone(names.safe_spelling(['▁DON', "'", 'T'])[0])             # John -> "don't"
        self.assertIsNone(names.safe_spelling(['▁SAID', '▁E', 'AR', 'TH'])[0])    # contains common words
        self.assertIsNone(names.safe_spelling(['▁A', 'R'])[0])                    # too short
        self.assertEqual(names.safe_spelling(['▁GRACE'], allowed={'GRACE'})[0], ['▁GRACE'])

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
        for change in ({'schema_version': 1}, {'confidence': 1.5}, {'profile_revision': -1},
                       {'matched_alias_id': ''}, {'direction_degrees': 10}):
            event = dict(names.make_name_event(self.profile, 'primary', 'replay'), **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_event(event)

class ProfileRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(names, 'PROFILE', Path(self.tmp.name)/'profile.json')
        self.patch.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
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

    def test_get_put_profile(self):
        status, profile = self.call('GET', '/profile')
        self.assertEqual((status, profile['revision'], profile['name_detection']['enabled']), (200, 0, False))
        status, profile = self.call('PUT', '/profile', {'display_name': 'Samira', 'notification_preferences': {'mode': 'quiet'}})
        self.assertEqual((status, profile['revision'], profile['name_detection']['primary_name']), (200, 1, 'Samira'))
        self.assertEqual(self.call('GET', '/profile')[1]['notification_preferences'], {'mode': 'quiet'})
        self.assertEqual(self.call('PUT', '/profile', {'name_detection': {'enabled': True}})[0], 400)
        request = Request(self.base+'/profile', method='OPTIONS', headers={'Origin': 'http://localhost:3000'})
        with urlopen(request) as response:
            self.assertIn('PUT', response.headers['Access-Control-Allow-Methods'])

if __name__ == '__main__':
    unittest.main()
