import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from audio.alerts import GESTURES, AlertEngine, DEFAULT_PROFILE, POLICY, validate_profile
from audio.events import EVENT_TYPES, make_event
from hardware.display import DisplayState, Presentation

SCENARIOS = json.loads((Path(__file__).resolve().parent.parent / 'audio' / 'alert-scenarios.json').read_text())


def fixture_event(kind, event_id, at, direction=None):
    label, tier = EVENT_TYPES[kind]
    degrees, confidence = direction or (None, None)
    return dict(schema_version=1, event_id=event_id, type=kind, label=label, confidence=None,
                source='mock', priority_tier=tier, timestamp_ms=at, direction_degrees=degrees,
                direction_confidence=confidence, distance_meters=None)


def run_step(engine, step):
    at = step['at']
    result = {}
    if 'add' in step:
        event = fixture_event(step['add'], step['id'], at, step.get('direction'))
        if 'sound' in step:   # a user-taught custom sound
            event.update(custom_sound_id=step['sound'], label=step['sound'])
        if 'target' in step:
            event['target_event_id'] = step['target']
        result = engine.add(event, at)
    elif 'look' in step:
        result = dict(resolved=engine.look(at, step['look']))
    elif 'dismiss' in step:
        result = dict(dismissed=engine.dismiss(at, step['dismiss']))
        if engine.decisions and engine.decisions[-1]['at_ms'] == at:
            result['reason'] = engine.decisions[-1]['reason']
    elif 'evidence' in step:
        evidence = step['evidence']
        engine.observe_sound(evidence['type'], evidence['present'], evidence['source'], at)
    elif 'controls' in step:
        engine.set_controls(at, **step['controls'])
    else:
        engine.tick(at)
    return result


class SharedScenarioTests(unittest.TestCase):
    def test_shared_alert_scenarios(self):
        for scenario in SCENARIOS['scenarios']:
            engine = AlertEngine()
            if 'profile' in scenario:
                profile = json.loads(json.dumps(DEFAULT_PROFILE))
                profile['notification_preferences'] = scenario['profile']
                profile['custom_sound_requests'] = scenario.get('custom_sound_requests', [])
                engine.set_profile(validate_profile(profile, EVENT_TYPES))
            for index, step in enumerate(scenario['steps']):
                with self.subTest(scenario=scenario['name'], step=index):
                    result = run_step(engine, step)
                    snap = engine.snapshot(step['at'])
                    expect = step['expect']
                    if 'active' in expect:
                        self.assertEqual(snap['active'] and snap['active']['event_id'], expect['active'])
                    if 'reason' in expect:
                        self.assertEqual(result.get('reason'), expect['reason'])
                    if 'replaced' in expect:
                        self.assertEqual(result['active_type'], expect['replaced'])
                    if 'tier' in expect:
                        self.assertEqual(result['priority_tier'], expect['tier'])
                    if 'dismissed' in expect:
                        self.assertEqual(result['dismissed'], expect['dismissed'])
                    if 'queue' in expect:
                        self.assertEqual([item['event_id'] for item in snap['queue']], expect['queue'])
                    if 'remaining' in expect:
                        self.assertEqual(snap['remaining_ms'], expect['remaining'])
                    if 'sequence' in expect:
                        self.assertEqual(snap['state_sequence'], expect['sequence'])
                    if 'resolved' in expect:
                        self.assertEqual(result['resolved'], expect['resolved'])
                    if 'direction' in expect:
                        self.assertEqual(snap['direction'], expect['direction'])
                    if 'confirm' in expect:
                        self.assertEqual(snap['confirm'] is not None, expect['confirm'])
                    if 'last_reason' in expect:
                        self.assertEqual(snap['decisions'][-1]['reason'], expect['last_reason'])
                    if 'events' in expect:
                        self.assertEqual(len(snap['events']), expect['events'])


class PolicyTests(unittest.TestCase):
    def test_invalid_control_request_is_atomic(self):
        engine = AlertEngine()
        with self.assertRaises(ValueError):
            engine.set_controls(0, focus_mode='dnd', paused='not-a-boolean')
        self.assertEqual(engine.focus_mode, 'everyday')
        self.assertFalse(engine.paused)

    def test_presets_match_mana_onboarding_defaults(self):
        source = (Path(__file__).resolve().parent.parent / 'frontend' / 'mana' / 'AwareOnboarding.jsx').read_text()
        block = source[source.index('export const AWARE_PRESET_DEFAULTS = {'):]
        block = block[block.index('{'):block.index('};') + 1]
        for name, tiers in POLICY['presets'].items():
            section = block[block.index(f'{name}:'):]
            section = section[section.index('{') + 1:section.index('}')]
            parsed = {k.strip(): int(v) for k, v in (pair.split(':') for pair in section.replace('\n', '').split(',') if pair.strip())}
            self.assertEqual(parsed, tiers, name)

    def test_profile_validation_rejects_bad_input(self):
        good = json.loads(json.dumps(DEFAULT_PROFILE))
        validate_profile(good, EVENT_TYPES)
        for change in ({'mode': 'loud'}, {'mode': 'balanced', 'event_tiers': {'knock': 7}},
                       {'mode': 'balanced', 'event_tiers': {'thunder': 2}}, {'mode': 'balanced', 'event_tiers': []}):
            bad = dict(good, notification_preferences=change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_profile(bad, EVENT_TYPES)
        with self.assertRaises(ValueError):
            validate_profile(dict(good, schema_version=2), EVENT_TYPES)

    def test_every_presentation_is_renderable_by_the_glasses(self):
        engine = AlertEngine()
        state = DisplayState(clock=lambda: 0.0)
        state.connect(engine.session_id)
        for index, kind in enumerate(k for k in EVENT_TYPES if k not in GESTURES):
            engine.set_controls(index * 100_000)
            event = (make_event(kind, .9, 'mock') if kind not in ('name_called', 'custom') else
                     dict(fixture_event(kind, f'n{index}', 0), custom_sound_id='front-doorbell'))
            engine.add(event, index * 100_000)
            envelope = engine.presentation(index * 100_000)
            cue = Presentation.parse(envelope)
            self.assertIsNotNone(cue.icon_id, kind)
            self.assertTrue(state.accept(envelope))
            self.assertTrue(any(state.frame().buffer), kind)
            engine.dismiss(index * 100_000)


class ConfirmationTests(unittest.TestCase):
    def test_resolve_check_reaches_the_glasses_at_the_cue_position_then_clears(self):
        engine = AlertEngine()
        state = DisplayState(clock=lambda: 0.0)
        state.connect(engine.session_id)
        knock = make_event('knock', .9, 'mock')
        knock.update(direction_degrees=-90, direction_confidence=1)
        engine.add(knock, 0)
        state.accept(engine.presentation(0))
        engine.add(fixture_event('thumbs_up', 'g1', 500), 500)
        envelope = engine.presentation(500)
        self.assertEqual((envelope['icon_id'], envelope['direction']), ('check', 'left'))
        self.assertTrue(state.accept(envelope))
        self.assertEqual(engine.presentation(1100)['effective_tier'], 0)


class ReceiverHttpTests(unittest.TestCase):
    def setUp(self):
        import audio.server as server_module
        self.tmp = tempfile.TemporaryDirectory()
        self.profile_path = Path(self.tmp.name) / 'profile.json'
        self.module = server_module
        self.server = server_module.create_server(port=0, profile_path=self.profile_path)
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.module.state.decision_log.close()
        self.tmp.cleanup()

    def call(self, path, body=None, method=None):
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, method=method or ('GET' if body is None else 'POST'),
                          headers={'Content-Type': 'application/json'} if body is not None else {})
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read())

    def test_saved_preferences_change_receiver_priority_and_survive_restart(self):
        profile = json.loads(json.dumps(DEFAULT_PROFILE))
        profile['notification_preferences'] = dict(mode='balanced', event_tiers={'dog_bark': 0, 'knock': 4})
        profile['display'] = dict(labels=True)
        saved = self.call('/profile', profile, 'PUT')
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(self.call('/events', make_event('dog_bark', .9, 'replay'))['reason'], 'ignored_tier_zero')
        reply = self.call('/events', make_event('knock', .9, 'replay'))
        self.assertEqual(reply['priority_tier'], 4)
        state = self.call('/state')
        self.assertEqual(state['active']['priority_tier'], 4)
        self.assertEqual(state['active']['producer_tier'], 2)
        self.assertTrue(state['health']['capture']['live'])
        display = self.call('/display?client=oled')
        self.assertEqual((display['icon_id'], display['effective_tier'], display['show_labels']), ('cue_knock', 4, True))
        self.assertTrue(self.call('/health')['display']['connected'])
        # Restart: a new receiver loads the persisted profile.
        restarted = self.module.AlertState(profile_path=self.profile_path)
        self.assertEqual(restarted.profile()['notification_preferences']['event_tiers'], {'dog_bark': 0, 'knock': 4})

    def test_failed_disk_save_does_not_change_live_or_persisted_preferences(self):
        original = self.call('/profile')
        changed = json.loads(json.dumps(original))
        changed['notification_preferences']['event_tiers']['knock'] = 0
        with patch('audio.server.os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(HTTPError) as caught:
                self.call('/profile', changed, 'PUT')
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(self.call('/profile'), original)
        self.assertEqual(self.call('/events', make_event('knock', .9, 'mock'))['priority_tier'], 2)

    def test_receiver_instances_are_isolated(self):
        second = self.module.create_server(port=0, profile_path=Path(self.tmp.name) / 'second.json')
        other_thread = threading.Thread(target=second.serve_forever, daemon=True)
        other_thread.start()
        try:
            self.call('/events', make_event('knock', .9, 'mock'))
            self.assertEqual(self.call('/state')['active']['type'], 'knock')
            with urlopen(f'http://127.0.0.1:{second.server_address[1]}/state') as response:
                self.assertIsNone(json.loads(response.read())['active'])
        finally:
            second.shutdown()
            second.server_close()
            second.alert_state.decision_log.close()
            self.module.state = self.server.alert_state

    def test_nonfinite_look_and_invalid_controls_are_rejected_without_changes(self):
        for heading in [float('nan'), float('inf'), -float('inf')]:
            with self.assertRaises(HTTPError) as caught:
                self.call('/look', {'heading_degrees': heading})
            self.assertEqual(caught.exception.code, 400)
        with self.assertRaises(HTTPError):
            self.call('/controls', {'focus_mode': 'dnd', 'paused': 'bad'})
        self.assertEqual(self.call('/state')['focus_mode'], 'everyday')

    def test_custom_requests_persist_as_pending_without_enabling_recognition(self):
        profile = self.call('/profile')
        profile['custom_sound_requests'] = [dict(id='custom-1', label='My kettle whistle', tier=0, status='pending')]
        saved = self.call('/profile', profile, 'PUT')
        self.assertEqual(saved['custom_sound_requests'], profile['custom_sound_requests'])
        restarted = self.module.AlertState(profile_path=self.profile_path)
        self.assertEqual(restarted.profile()['custom_sound_requests'][0]['tier'], 0)
        self.assertEqual(restarted.profile()['notification_preferences']['event_tiers'], {})
        bad = dict(profile, custom_sound_requests=[dict(id='x',label='Something',tier=2,status='active')])
        with self.assertRaises(HTTPError):
            self.call('/profile', bad, 'PUT')

    def test_controls_dismiss_and_errors(self):
        alarm = make_event('smoke_alarm', .9, 'mock')
        self.call('/events', alarm)
        self.assertFalse(self.call('/dismiss', {'event_id': 'not-current'})['dismissed'])
        self.assertTrue(self.call('/dismiss', {'event_id': alarm['event_id']})['dismissed'])
        self.call('/controls', {'focus_mode': 'dnd'})
        self.assertEqual(self.call('/events', make_event('knock', .9, 'mock'))['reason'], 'held_dnd_mode')
        state = self.call('/state')
        self.assertEqual((state['focus_mode'], state['active'], state['health']['capture']['live']), ('dnd', None, False))
        knock = make_event('knock', .9, 'mock')
        knock.update(direction_degrees=95, direction_confidence=.8)
        self.call('/controls', {'focus_mode': 'everyday'})
        self.call('/events', knock)
        self.assertEqual(self.call('/display')['direction'], 'right')
        self.assertFalse(self.call('/look', {'heading_degrees': -90})['resolved'])
        self.assertTrue(self.call('/look', {'heading_degrees': 80})['resolved'])
        for path, body, method in (('/controls', {'focus_mode': 'party'}, 'POST'),
                                   ('/look', {'direction': 'up'}, 'POST'),
                                   ('/profile', {'schema_version': 1}, 'PUT'),
                                   ('/events', {'type': 'thunder'}, 'POST')):
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                self.call(path, body, method)
            self.assertEqual(caught.exception.code, 400)


if __name__ == '__main__':
    unittest.main()
