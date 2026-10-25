import io
import json
import unittest
from unittest import mock

import numpy as np

from audio import question_paraphrase, questions
from audio.events import validate_event


class FakeRecognizer:
    def __init__(self, text):
        self.text, self.heard = text, 0

    def create_stream(self):
        recognizer = self

        class Stream:
            result = type('R', (), {'text': recognizer.text})

            def accept_waveform(self, rate, samples):
                recognizer.heard = len(samples)
        return Stream()

    def decode_stream(self, stream):
        pass


def catcher(text, profile=None):
    events, decisions = [], []
    c = questions.QuestionCatcher(events.append, profile=lambda: profile or {'name_detection': {'primary_name': 'Emma'}},
                                  recognizer=FakeRecognizer(text), on_decision=decisions.append)
    return c, events, decisions


NAME = dict(event_id='n1', matched_alias_id='primary', direction_degrees=90, direction_confidence=.7,
            direction_source='pi_stereo', direction_reason='sustained_lateral_evidence')


class TextTests(unittest.TestCase):
    def test_finds_the_question_after_the_name(self):
        cases = {
            'Hey Emma, are you coming to lunch with us later?': 'are you coming to lunch with us later?',
            'Emma are you coming to lunch with us later': 'are you coming to lunch with us later?',
            'Excuse me, can you pass the salt please': 'can you pass the salt please?',
            "Hey Emma! Don't forget to bring your laptop tomorrow.": "Don't forget to bring your laptop tomorrow.",
            'Emma, your package arrived.': None,
            'Emma, that was a great talk.': None,
            'Hello?': None,
        }
        for transcript, expected in cases.items():
            with self.subTest(transcript=transcript):
                self.assertEqual(questions.directed_question(transcript, ['Emma']), expected)

    def test_display_text_fits_the_oled_font_and_four_lines(self):
        self.assertEqual(questions.for_display("um, what's the wifi password, Emma?"), 'Whats the wifi password Emma?')
        long = questions.for_display('what time does the bus leave and is it still running at night when we get out of the event')
        self.assertLessEqual(len(long), questions.MAX_LABEL)
        self.assertTrue(long.endswith('...'))
        self.assertRegex(long, r'^[A-Za-z0-9 !\-./?]+$')


class CatcherTests(unittest.TestCase):
    def feed(self, c, seconds, level=.1):
        for _ in range(int(seconds * 10)):
            c.feed(np.full(1600, level, dtype=np.float32))

    def test_question_after_name_keeps_its_direction_and_includes_the_name_audio(self):
        c, events, decisions = catcher('Emma, are you coming to lunch?')
        self.feed(c, 2.5)
        c.trigger(NAME, 'microphone')
        self.feed(c, 2)
        self.feed(c, 1, level=0)          # the speaker pauses, so capture ends early
        c.jobs.join()
        self.assertEqual(len(events), 1)
        event = validate_event(events[0])
        self.assertEqual((event['label'], event['transcript']), ('Are you coming to lunch?', 'Emma, are you coming to lunch?'))
        self.assertEqual((event['direction_degrees'], event['after_event_id'], event['priority_tier']), (90, 'n1', 3))
        self.assertGreaterEqual(c.recognizer.heard, int(questions.PRE_SECONDS * 16000))
        self.assertEqual(decisions[-1]['reason'], 'emitted')
        self.assertNotIn('transcript', decisions[-1])   # what people said stays out of the decision log

    def test_capture_is_bounded(self):
        c, events, _ = catcher('Emma, are you coming?')
        c.trigger(NAME, 'microphone')
        self.feed(c, questions.CAPTURE_SECONDS + 1)
        c.jobs.join()
        self.assertEqual(len(events), 1)
        self.assertLessEqual(c.recognizer.heard, (questions.PRE_SECONDS + questions.CAPTURE_SECONDS + .2) * 16000)

    def test_no_question_turned_off_or_warning_emits_nothing(self):
        c, events, decisions = catcher('Emma, nice shoes.')
        c.trigger(NAME, 'microphone')
        c.flush()
        self.assertEqual((events, decisions[-1]['reason']), ([], 'no_question'))
        c, events, _ = catcher('Are you coming?', {'name_detection': {'questions': False}})
        c.trigger(NAME, 'microphone')
        c.flush()
        self.assertEqual(events, [])
        c, events, _ = catcher('Watch out for the bike?')
        c.trigger(dict(NAME, matched_alias_id='warning-0'), 'microphone')
        c.flush()
        self.assertEqual(events, [])

    def test_claude_shortening_is_opt_in_and_falls_back_to_local(self):
        profile = {'name_detection': {'primary_name': 'Emma', 'question_paraphrase': True}}
        c, events, _ = catcher('Emma, are you coming to lunch with us later today?', profile)
        c.paraphrase_url = 'http://127.0.0.1:1/questions/paraphrase'
        with mock.patch.object(questions, 'paraphrase', return_value='Lunch later?'):
            c.trigger(NAME, 'microphone')
            c.flush()
        self.assertEqual((events[0]['label'], events[0]['summary_source']), ('Lunch later?', 'claude'))
        with mock.patch.object(questions, 'paraphrase', return_value=None):
            c.trigger(NAME, 'microphone')
            c.flush()
        self.assertEqual(events[1]['summary_source'], 'local')


class ParaphraseTests(unittest.TestCase):
    def test_without_a_key_nothing_is_sent(self):
        with mock.patch.object(question_paraphrase.claude, 'credential', return_value=''), \
             mock.patch.object(question_paraphrase.claude, 'open_request') as send:
            self.assertIsNone(question_paraphrase.shorten('Are you coming?'))
        send.assert_not_called()

    def test_sends_only_the_text_and_validates_the_reply(self):
        reply = dict(stop_reason='end_turn', content=[dict(type='text', text='"Lunch later?"')])
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(json.dumps(reply).encode())
        with mock.patch.object(question_paraphrase.claude, 'credential', return_value='test-key'), \
             mock.patch.object(question_paraphrase.claude, 'open_request', return_value=response) as send:
            self.assertEqual(question_paraphrase.shorten('Are you coming to lunch with us later?'), 'Lunch later?')
        body = json.loads(send.call_args[0][0].data)
        self.assertEqual(body['messages'], [dict(role='user', content='Are you coming to lunch with us later?')])
        reply['content'][0]['text'] = 'x' * 200
        response.__enter__.return_value = io.BytesIO(json.dumps(reply).encode())
        with mock.patch.object(question_paraphrase.claude, 'credential', return_value='test-key'), \
             mock.patch.object(question_paraphrase.claude, 'open_request', return_value=response):
            self.assertIsNone(question_paraphrase.shorten('Are you coming?'))

    def test_question_events_need_a_transcript(self):
        event = questions.make_question_event('Coming?', 'Emma, coming?', 'microphone', NAME)
        self.assertEqual(validate_event(event)['type'], 'question')
        with self.assertRaises(ValueError):
            validate_event(dict(event, transcript=''))


if __name__ == '__main__':
    unittest.main()
