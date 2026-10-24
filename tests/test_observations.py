"""Observation stream tests. NumPy only: no weights, recordings or microphone."""
import json
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from audio import server
from audio.events import Detector
from audio.observations import (ObservationPublisher, build_observation, level_dbfs,
                                validate_observation)

def sample(**overrides):
    detector = Detector()
    scores = {'Knock': 0.8, 'Speech': 0.3, 'Bark': 0.01, 'Music': 0.2}
    events = detector.detect(scores, 'replay', now=0)
    custom = [dict(type='custom', custom_sound_id='kettle', raw_score=0.12, threshold=0.7, reason='below_threshold')]
    args = dict(source='replay', model='zipformer', timestamp_ms=1_792_800_000_000, inference_ms=48.2,
                window_rms=0.05, rule_decisions=detector.decisions, custom_decisions=custom,
                custom_labels={'kettle': 'Kettle'}, events=events, top_k=3)
    args.update(overrides)
    return build_observation(scores, **args)

class BuildAndValidateTests(unittest.TestCase):
    def test_shape(self):
        obs = validate_observation(sample())
        self.assertEqual([t['label'] for t in obs['top']], ['Knock', 'Speech', 'Music'])
        self.assertEqual(obs['rules']['knock']['reason'], 'emitted')
        self.assertEqual(obs['rules']['bicycle_bell']['reason'], 'disabled')
        self.assertEqual(obs['custom'], [dict(id='kettle', label='Kettle', score=0.12, threshold=0.7, reason='below_threshold')])
        self.assertEqual([e['type'] for e in obs['emitted']], ['knock'])
        self.assertEqual(obs['level_dbfs'], -26.0)
        self.assertLess(len(json.dumps(obs)), 4000)

    def test_level(self):
        self.assertEqual(level_dbfs(1.0), 0.0)
        self.assertEqual(level_dbfs(0.0), -100.0)

    def test_rejects_bad_observations(self):
        cases = [
            dict(kind='event'), dict(schema_version=2), dict(source='satellite'),
            dict(timestamp_ms=-1), dict(top=[{'label': 'Knock', 'score': 1.5}]),
            dict(top=[{'label': '', 'score': 0.1}]), dict(top=[{'label': 'x', 'score': 0.1}]*26),
            dict(rules={'knock': {'score': float('nan'), 'reason': 'x'}}),
            dict(custom=[{'id': 'k', 'label': 'K', 'score': 2, 'reason': 'x'}]), dict(emitted='nope'),
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_observation(dict(sample(), **change))

class StoreAndRouteTests(unittest.TestCase):
    def setUp(self):
        self.store = server.ObservationStore(maxlen=5)
        self.patch = mock.patch.object(server, 'observations', self.store)
        self.patch.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.patch.stop()

    def request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {'Content-Type': 'application/json'} if data else {}
        try:
            with urlopen(Request(self.base+path, data=data, method=method, headers=headers)) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_post_then_poll_since(self):
        for _ in range(7):
            status, body = self.request('POST', '/observations', sample())
            self.assertEqual(status, 200)
        self.assertEqual(body['seq'], 7)
        status, body = self.request('GET', '/observations?since=0&limit=20')
        self.assertEqual([o['seq'] for o in body['observations']], [3, 4, 5, 6, 7])   # ring buffer of 5
        self.assertEqual(body['latest_seq'], 7)
        _, body = self.request('GET', '/observations?since=6')
        self.assertEqual([o['seq'] for o in body['observations']], [7])
        _, body = self.request('GET', '/observations?since=7')
        self.assertEqual(body['observations'], [])
        _, body = self.request('GET', '/observations?since=0&limit=2')
        self.assertEqual([o['seq'] for o in body['observations']], [6, 7])
        self.assertIn('received_ms', body['observations'][0])

    def test_bad_requests(self):
        self.assertEqual(self.request('POST', '/observations', dict(sample(), source='x'))[0], 400)
        self.assertEqual(self.request('GET', '/observations?since=abc')[0], 400)

class PublisherTests(unittest.TestCase):
    def test_never_blocks_when_server_hangs(self):
        import socket
        hung = socket.socket()
        hung.bind(('127.0.0.1', 0))
        hung.listen(8)   # accepts connections into the backlog but never answers
        try:
            url = f'http://127.0.0.1:{hung.getsockname()[1]}/observations'
            publisher = ObservationPublisher(url, max_pending=3, timeout=0.3)
            start = time.monotonic()
            with mock.patch('sys.stderr'):
                for _ in range(200):
                    publisher.publish(sample())
            self.assertLess(time.monotonic()-start, 0.5)   # the audio loop is never held up
            self.assertGreater(publisher.dropped, 150)      # stale observations are discarded
        finally:
            hung.close()

if __name__ == '__main__':
    unittest.main()
