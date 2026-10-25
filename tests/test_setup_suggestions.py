"""Claude setup boundaries with mocked provider HTTPS; never sends a paid request."""
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from audio import server
from audio import setup_suggestions as ss


SUGGESTION = dict(cue_id='baby_cry', tier=3, reason='Notice when your baby needs attention.')


def response(value=None, **changes):
    envelope = dict(stop_reason='end_turn', content=[dict(type='text', text=json.dumps(
        value if value is not None else dict(suggestions=[SUGGESTION])))])
    envelope.update(changes)
    return io.BytesIO(json.dumps(envelope).encode())


class SuggestionTests(unittest.TestCase):
    def setUp(self):
        self.environment = mock.patch.dict(ss.os.environ, {'ANTHROPIC_API_KEY': 'qa-private-key'}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.memory = mock.patch.object(ss, '_memory_key', None)
        self.memory.start()
        self.addCleanup(self.memory.stop)

    def test_offline_status_does_not_probe_provider_and_key_is_not_exposed(self):
        with mock.patch.object(ss, 'open_request') as provider:
            self.assertTrue(ss.status()['available'])
            provider.assert_not_called()
        self.assertNotIn('qa-private-key', json.dumps(ss.status()))
        ss.os.environ.pop('ANTHROPIC_API_KEY')
        self.assertEqual(ss.status()['code'], 'missing_api_key')
        with self.assertRaises(ss.SuggestionError) as caught:
            ss.suggest(dict(description='I care for a baby.'))
        self.assertEqual(caught.exception.status, 503)

    def test_real_provider_request_shape_and_validated_response(self):
        with mock.patch.object(ss, 'open_request', return_value=response()) as provider:
            result = ss.suggest(dict(description='I care for a baby.'))
        request = provider.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.anthropic.com/v1/messages')
        self.assertEqual(request.get_header('Authorization'), 'Bearer qa-private-key')
        self.assertEqual(provider.call_args.kwargs['timeout'], 18)
        body = json.loads(request.data)
        self.assertEqual(body['model'], ss.DEFAULT_MODEL)
        self.assertEqual(body['max_tokens'], 2048)
        self.assertNotIn('temperature', body)
        self.assertEqual(result['suggestions'], [SUGGESTION])
        self.assertEqual(result['provider'], 'Anthropic')
        self.assertNotIn('qa-private-key', json.dumps(result))

    def test_invalid_input_never_calls_provider(self):
        for body in (None, {}, {'description': ''}, {'description': 'x' * 1501},
                     {'description': 123}, {'description': 'a', 'key': 'no'}, {'description': '\x00a'}):
            with self.subTest(body_type=type(body).__name__), mock.patch.object(ss, 'open_request') as provider:
                with self.assertRaises(ValueError):
                    ss.suggest(body)
                provider.assert_not_called()

    def test_disallowed_and_malformed_suggestions_are_rejected(self):
        invalid = [dict(SUGGESTION, cue_id='name_called'), dict(SUGGESTION, cue_id='bicycle_bell'),
                   dict(SUGGESTION, cue_id='invented'), dict(SUGGESTION, tier=True),
                   dict(SUGGESTION, tier=5), dict(SUGGESTION, reason='x' * 181),
                   dict(SUGGESTION, reason='line\nbreak'), dict(SUGGESTION, extra='field')]
        for entry in invalid:
            with self.subTest(entry=entry), mock.patch.object(ss, 'open_request', return_value=response(dict(suggestions=[entry]))):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Working from home.'))
                self.assertEqual(caught.exception.code, 'invalid_provider_response')

    def test_deduplicates_and_enforces_eight_item_limit(self):
        self.assertEqual(ss.validate_suggestions(dict(suggestions=[SUGGESTION, SUGGESTION])), [SUGGESTION])
        with self.assertRaises(ValueError):
            ss.validate_suggestions(dict(suggestions=[SUGGESTION] * 9))

    def test_malformed_truncated_and_oversized_provider_response(self):
        for fake in (io.BytesIO(b'not-json'), io.BytesIO(b'x' * (ss.MAX_RESPONSE_BYTES + 1)),
                     response(stop_reason='max_tokens'), response(content=[]), response(content='not-list')):
            with mock.patch.object(ss, 'open_request', return_value=fake):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Office work.'))
                self.assertEqual(caught.exception.status, 502)

    def test_exact_json_fences_are_unwrapped_and_schema_is_still_validated(self):
        text = json.dumps(dict(suggestions=[SUGGESTION]))
        for wrapped in ('```json\n' + text + '\n```', '```\n' + text + '\n```',
                        '\n```JSON\r\n' + text + '\r\n```\n'):
            with self.subTest(fence=wrapped[:8]), mock.patch.object(ss, 'open_request', return_value=response(
                    content=[dict(type='text', text=wrapped)])):
                self.assertEqual(ss.suggest(dict(description='Working at home.'))['suggestions'], [SUGGESTION])
        invalid = '```json\n' + json.dumps(dict(suggestions=[dict(SUGGESTION, cue_id='invented')])) + '\n```'
        with mock.patch.object(ss, 'open_request', return_value=response(content=[dict(type='text', text=invalid)])):
            with self.assertRaises(ss.SuggestionError) as caught:
                ss.suggest(dict(description='Working at home.'))
            self.assertEqual(caught.exception.code, 'invalid_provider_response')

    def test_prose_partial_json_and_extra_fences_are_not_extracted(self):
        text = json.dumps(dict(suggestions=[SUGGESTION]))
        for wrapped in ('Here are your settings: ' + text, '```json\n' + text,
                        '```json\n' + text + '\n```\nDone.', text + '\n' + text):
            with self.subTest(prefix=wrapped[:12]), mock.patch.object(ss, 'open_request', return_value=response(
                    content=[dict(type='text', text=wrapped)])):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Working at home.'))
                self.assertEqual(caught.exception.code, 'malformed_suggestions_json')

    def test_incomplete_empty_and_unreadable_response_codes_are_distinct(self):
        cases = [(response(stop_reason='max_tokens'), 'incomplete_provider_response'),
                 (response(stop_reason='pause_turn'), 'incomplete_provider_response'),
                 (response(content=[]), 'empty_provider_response'),
                 (response(content='wrong-shape'), 'malformed_provider_response'),
                 (io.BytesIO(b'wrong-envelope'), 'malformed_provider_response'),
                 (response(content=[dict(type='text', text='not json')]), 'malformed_suggestions_json')]
        for fake, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(ss, 'open_request', return_value=fake):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Working at home.'))
                self.assertEqual(caught.exception.code, expected)

    def test_multiple_text_blocks_and_thinking_do_not_change_suggestion_contract(self):
        text = json.dumps(dict(suggestions=[SUGGESTION]))
        blocks = [dict(type='thinking', thinking='private-provider-thought'),
                  dict(type='text', text=text[:25]), dict(type='text', text=text[25:])]
        with mock.patch.object(ss, 'open_request', return_value=response(content=blocks)):
            self.assertEqual(ss.suggest(dict(description='Working at home.'))['suggestions'], [SUGGESTION])

    def test_refusal_metadata_is_not_returned(self):
        for extra in (dict(stop_reason='refusal'), dict(stop_details=dict(type='refusal', explanation='private-data'))):
            with mock.patch.object(ss, 'open_request', return_value=response(**extra)):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Private context.'))
                self.assertEqual(caught.exception.code, 'provider_declined')
                self.assertNotIn('private-data', str(caught.exception))

    def test_envelope_and_text_size_limits_are_preserved(self):
        for raw in (b'x' * (ss.MAX_RESPONSE_BYTES + 1),
                    response(content=[dict(type='text', text='x' * (ss.MAX_SUGGESTION_TEXT + 1))]).getvalue()):
            with self.assertRaises(ss.SuggestionError) as caught:
                ss.parse_response(raw)
            self.assertEqual(caught.exception.code, 'oversized_provider_response')

    def test_provider_failures_are_clear_and_do_not_echo_body(self):
        for code, status, expected in ((401, 503, 'provider_auth_error'), (403, 503, 'provider_auth_error'),
                                      (429, 429, 'provider_rate_limited'), (404, 503, 'provider_model_error'),
                                      (400, 503, 'provider_model_error'), (500, 502, 'provider_error')):
            exc = HTTPError(ss.API_URL, code, 'qa-private-key private description', {}, io.BytesIO(b'private data'))
            with self.subTest(code=code), mock.patch.object(ss, 'open_request', side_effect=exc):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Private context.'))
                self.assertEqual((caught.exception.status, caught.exception.code), (status, expected))
                self.assertNotIn('private', str(caught.exception))

    def test_network_timeout_and_unreachable(self):
        for exc, status in ((TimeoutError(), 504), (URLError(TimeoutError()), 504), (URLError('offline'), 502)):
            with mock.patch.object(ss, 'open_request', side_effect=exc):
                with self.assertRaises(ss.SuggestionError) as caught:
                    ss.suggest(dict(description='Office.'))
                self.assertEqual(caught.exception.status, status)

    def test_invalid_config_and_redirects(self):
        ss.os.environ['ANTHROPIC_MODEL'] = 'bad model'
        self.assertFalse(ss.status()['available'])
        with self.assertRaises(ss.SuggestionError):
            ss.suggest(dict(description='Office.'))
        self.assertIsNone(ss.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example'))

    def test_entered_key_stays_in_memory_and_overrides_environment(self):
        self.assertEqual(ss.configure_key({'key': 'sk-ant-local-private'}), {'available': True, 'storage': 'memory'})
        self.assertEqual(ss.os.environ['ANTHROPIC_API_KEY'], 'qa-private-key')
        self.assertEqual(ss.credential(), 'sk-ant-local-private')
        self.assertNotIn('sk-ant-local-private', json.dumps(ss.status()))
        with mock.patch.object(ss, 'open_request', return_value=response()) as provider:
            ss.suggest(dict(description='Office.'))
        self.assertEqual(provider.call_args.args[0].get_header('Authorization'), 'Bearer sk-ant-local-private')
        self.assertEqual(ss.clear_key(), {'available': True, 'storage': 'environment'})
        self.assertEqual(ss.credential(), 'qa-private-key')

    def test_invalid_session_key_is_not_echoed_or_applied(self):
        for key in ('', 'sk-ant-secret\nvalue', 'a' * 513, 'value with spaces', None):
            with self.subTest(length=len(key) if isinstance(key, str) else None):
                with self.assertRaises(ValueError) as caught:
                    ss.configure_key({'key': key})
                self.assertNotIn('sk-ant-secret', str(caught.exception))
                self.assertEqual(ss.credential(), 'qa-private-key')


class SuggestionRouteTests(unittest.TestCase):
    def setUp(self):
        self.memory = mock.patch.object(ss, '_memory_key', None)
        self.memory.start()
        self.addCleanup(self.memory.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.httpd = server.create_server(port=0, profile_path=Path(self.tmp.name) / 'profile.json')
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def call(self, method, body=None, origin=None, path='/setup/suggestions', content_type='application/json'):
        data = json.dumps(body).encode() if body is not None else None
        headers = {'Content-Type': content_type} if data else {}
        if origin:
            headers['Origin'] = origin
        request = Request(self.base + path, method=method, data=data, headers=headers)
        try:
            with urlopen(request, timeout=3) as result:
                return result.status, json.loads(result.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_status_and_suggestion_routes_never_change_profile_or_alerts(self):
        before = self.httpd.alert_state.profile()
        with mock.patch.dict(ss.os.environ, {}, clear=True):
            self.assertFalse(self.call('GET')[1]['available'])
            self.assertEqual(self.call('POST', dict(description='Office.'))[0], 503)
        with mock.patch.dict(ss.os.environ, {'ANTHROPIC_API_KEY': 'qa-key'}, clear=True), \
                mock.patch.object(ss, 'open_request', return_value=response()):
            status, body = self.call('POST', dict(description='A baby at home.'), 'http://127.0.0.1:5174')
            self.assertEqual((status, body['suggestions']), (200, [SUGGESTION]))
        self.assertEqual(self.httpd.alert_state.profile(), before)
        self.assertIsNone(self.httpd.alert_state.snapshot()['active'])
        self.assertFalse((Path(self.tmp.name) / 'profile.json').exists())

    def test_validation_and_local_access_rules(self):
        self.assertEqual(self.call('POST', dict(description=''))[0], 400)
        self.assertEqual(self.call('POST', dict(description='Office.'), 'https://untrusted.example')[0], 403)
        with mock.patch.object(server.Handler, 'from_loopback', return_value=False):
            self.assertEqual(self.call('GET')[0], 403)

    def test_key_configuration_requires_local_origin_json_and_redacts_key(self):
        path = '/setup/suggestions/key'
        body = {'key': 'sk-ant-do-not-echo'}
        for origin in (None, 'null', 'https://untrusted.example', 'http://['):
            self.assertEqual(self.call('POST', body, origin, path)[0], 403)
        with mock.patch.object(server.Handler, 'from_loopback', return_value=False):
            self.assertEqual(self.call('POST', body, 'http://localhost:5174', path)[0], 403)
        self.assertEqual(self.call('POST', body, 'http://localhost:5174', path, 'text/plain')[0], 400)
        with mock.patch.dict(ss.os.environ, {}, clear=True):
            code, result = self.call('POST', body, 'http://127.0.0.1:5174', path)
            self.assertEqual((code, result), (200, {'available': True, 'storage': 'memory'}))
            self.assertNotIn(body['key'], json.dumps(self.call('GET')[1]))
            self.assertTrue(self.call('GET')[1]['available'])
            code, result = self.call('DELETE', {}, 'http://[::1]:5174', path)
            self.assertEqual((code, result), (200, {'available': False, 'storage': 'none'}))
        self.assertFalse((Path(self.tmp.name) / 'profile.json').exists())
