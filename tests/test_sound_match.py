import io
import json
import unittest
from unittest import mock

from audio import sound_match
from audio.setup_suggestions import SuggestionError


def reply(text, stop='end_turn'):
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(json.dumps(
        dict(stop_reason=stop, content=[dict(type='text', text=text)])).encode())
    return response


class SoundMatchTests(unittest.TestCase):
    def ask(self, text, request='my kettle'):
        with mock.patch.object(sound_match.claude, 'credential', return_value='test-key'), \
             mock.patch.object(sound_match.claude, 'open_request', return_value=reply(text)) as send:
            result = sound_match.match(dict(request=request))
        return result, json.loads(send.call_args[0][0].data)

    def test_returns_only_real_enabled_catalog_labels(self):
        answer = json.dumps(dict(matches=[
            dict(label='Whistle', reason='A kettle whistles when it boils.'),
            dict(label='Kettle whistle', reason='Invented label.'),
            dict(label='Bicycle bell', reason='Disabled pending evidence.'),
            dict(label='Boiling', reason='Water boiling.')]))
        result, body = self.ask('```json\n' + answer + '\n```')
        self.assertEqual([m['label'] for m in result['matches']], ['Whistle', 'Boiling'])
        self.assertEqual(result['matches'][0]['name'], 'Whistle')
        self.assertIn('icon', result['matches'][0])
        # Only the typed request and the public class list are sent.
        self.assertEqual(body['messages'], [dict(role='user', content='{"sound": "my kettle"}')])
        self.assertIn('"Whistle"', body['system'])
        self.assertNotIn('"Bicycle bell"', body['system'])

    def test_empty_and_invalid_answers(self):
        self.assertEqual(self.ask('{"matches": []}')[0], dict(matches=[]))
        with self.assertRaises(SuggestionError):
            self.ask('Sure! The kettle is probably a whistle.')

    def test_needs_a_key_and_a_bounded_request(self):
        with mock.patch.object(sound_match.claude, 'credential', return_value=''), \
             mock.patch.object(sound_match.claude, 'open_request') as send:
            with self.assertRaises(SuggestionError) as caught:
                sound_match.match(dict(request='my kettle'))
        self.assertEqual(caught.exception.code, 'missing_api_key')
        send.assert_not_called()
        for bad in (dict(request=''), dict(request='x' * 81), dict(request='kettle', extra=1)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                sound_match.validate_request(bad)


if __name__ == '__main__':
    unittest.main()
