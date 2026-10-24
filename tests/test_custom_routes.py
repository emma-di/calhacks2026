"""HTTP route tests for custom-sound onboarding. NumPy only: a fake embedder replaces Zipformer."""
import io
import json
import tempfile
import threading
import unittest
import wave
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np

from audio import custom_sounds as cs
from audio import server

class SpectrumEmbedder:
    """Stand-in for ZipformerEmbedder: a log spectrum, so tones and noise separate."""
    def embed(self, window):
        spectrum = np.abs(np.fft.rfft(window))[:256*62]
        return np.log1p(spectrum.reshape(256, 62).mean(axis=1)).astype(np.float32)

def wav_bytes(samples, rate=16000, channels=1):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        pcm = (np.clip(samples, -1, 1)*32767).astype('<i2')
        writer.writeframes(np.repeat(pcm, channels).tobytes() if channels > 1 else pcm.tobytes())
    return buffer.getvalue()

def tone(freq, seconds, rate=16000, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds*rate))/rate
    return 0.5*np.sin(2*np.pi*freq*t)+0.01*rng.standard_normal(len(t))

def noise(seconds, seed):
    return 0.2*np.random.default_rng(seed).standard_normal(int(seconds*16000))

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(cs, 'STORE', Path(self.tmp.name)),
                        mock.patch.object(server.custom, 'embedder', SpectrumEmbedder())]
        for patch in self.patches:
            patch.start()
        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.httpd.server_address[1]}'

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def call(self, method, path, body=None, content_type=None, headers=None):
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        all_headers = dict(headers or {})
        if data is not None:
            all_headers['Content-Type'] = content_type or ('application/json' if isinstance(body, dict) else 'audio/wav')
        request = Request(self.base+path, data=data, method=method, headers=all_headers)
        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None, response.headers
        except HTTPError as exc:
            return exc.code, json.loads(exc.read()), exc.headers

    def test_full_onboarding_flow(self):
        status, body, _ = self.call('GET', '/custom-sounds')
        self.assertEqual((status, body['sounds'], body['background']['ready']), (200, [], False))

        # Room background: two 15-second recordings of ordinary noise.
        for seed in (1, 2):
            status, body, _ = self.call('POST', '/background/clips', wav_bytes(noise(15, seed)))
            self.assertEqual(status, 200)
        self.assertEqual(body['room_clips'], 2)
        self.assertTrue(body['background']['ready'] if 'background' in body else body['ready'])

        # Create, upload five recordings (a 44.1 kHz stereo one too), train.
        status, meta, _ = self.call('POST', '/custom-sounds', {'label': 'Kettle whistle', 'priority_tier': 3})
        self.assertEqual((status, meta['id'], meta['status']), (201, 'kettle-whistle', 'recording'))
        for seed in range(4):
            status, meta, _ = self.call('POST', '/custom-sounds/kettle-whistle/clips', wav_bytes(tone(1000, 3, seed=seed)))
            self.assertEqual(status, 200)
        stereo = wav_bytes(tone(1000, 3, rate=44100, seed=9), rate=44100, channels=2)
        status, meta, _ = self.call('POST', '/custom-sounds/kettle-whistle/clips', stereo)
        self.assertEqual(meta['clip_count'], 5)
        status, meta, _ = self.call('POST', '/custom-sounds/kettle-whistle/train', {})
        self.assertEqual((status, meta['status']), (200, 'ready'))

        # Test: a new whistle is recognized; noise and silence are not.
        status, result, _ = self.call('POST', '/custom-sounds/kettle-whistle/test', wav_bytes(tone(1000, 2, seed=42)))
        self.assertTrue(result['detected'], result)
        _, result, _ = self.call('POST', '/custom-sounds/kettle-whistle/test', wav_bytes(noise(3, 77)))
        self.assertFalse(result['detected'], result)
        _, result, _ = self.call('POST', '/custom-sounds/kettle-whistle/test', wav_bytes(np.zeros(32000)))
        self.assertEqual(result['reason'], 'silent')

        # Live detector sees it; disabling hides it; more room background retrains it.
        self.assertEqual([m['id'] for m, _ in cs.load_heads()], ['kettle-whistle'])
        status, meta, _ = self.call('PATCH', '/custom-sounds/kettle-whistle', {'enabled': False})
        self.assertEqual((status, meta['enabled'], cs.load_heads()), (200, False, []))
        _, body, _ = self.call('POST', '/background/clips', wav_bytes(noise(10, 3)))
        self.assertEqual(body['retrained'], [{'id': 'kettle-whistle', 'status': 'ready'}])

        # Start over, then delete.
        _, meta, _ = self.call('DELETE', '/custom-sounds/kettle-whistle/clips')
        self.assertEqual((meta['clip_count'], meta['status']), (0, 'recording'))
        self.assertEqual(self.call('DELETE', '/custom-sounds/kettle-whistle')[0], 200)
        self.assertEqual(self.call('GET', '/custom-sounds/kettle-whistle')[0], 404)

    def test_errors(self):
        self.assertEqual(self.call('GET', '/custom-sounds/nope')[0], 404)
        self.assertEqual(self.call('GET', '/custom-sounds/..%2f..')[0], 404)
        self.assertEqual(self.call('POST', '/custom-sounds', {'label': ''})[0], 400)
        self.assertEqual(self.call('POST', '/custom-sounds', {'label': 'x', 'priority_tier': 9})[0], 400)
        self.call('POST', '/custom-sounds', {'label': 'Doorbell'})
        status, body, _ = self.call('POST', '/custom-sounds/doorbell/clips', b'not audio at all')
        self.assertEqual(status, 400)
        status, _, _ = self.call('POST', '/custom-sounds/doorbell/clips', wav_bytes(tone(500, 1)), content_type='text/plain')
        self.assertEqual(status, 400)
        status, body, _ = self.call('POST', '/custom-sounds/doorbell/train', {})   # no clips
        self.assertEqual(status, 400)
        self.call('POST', '/custom-sounds/doorbell/clips', wav_bytes(tone(500, 2)))
        status, body, _ = self.call('POST', '/custom-sounds/doorbell/train', {})   # no background yet
        self.assertEqual(status, 503)
        self.assertIn('background', body['error'])
        self.assertEqual(self.call('PATCH', '/custom-sounds/doorbell', {'clip_count': 99})[0], 400)
        self.assertEqual(self.call('POST', '/custom-sounds/doorbell/test', wav_bytes(tone(500, 2)))[0], 400)

    def test_cors_only_for_local_origins(self):
        request = Request(self.base+'/custom-sounds', method='OPTIONS', headers={'Origin': 'http://localhost:3000'})
        with urlopen(request) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'http://localhost:3000')
            self.assertIn('PATCH', response.headers['Access-Control-Allow-Methods'])
        _, _, headers = self.call('GET', '/custom-sounds', headers={'Origin': 'https://evil.example'})
        self.assertIsNone(headers['Access-Control-Allow-Origin'])

    def test_existing_alert_routes_unchanged(self):
        from audio.events import make_event
        self.assertEqual(self.call('POST', '/events', make_event('knock', .9, 'mock'))[0], 200)
        _, body, _ = self.call('GET', '/state')
        self.assertEqual(body['active']['type'], 'knock')
        self.assertEqual(self.call('POST', '/dismiss', {})[0], 200)
        self.assertEqual(self.call('POST', '/nowhere', {})[0], 404)
        self.assertEqual(self.call('DELETE', '/state')[0], 404)

class HotReloadTests(unittest.TestCase):
    def test_detector_reloads_after_changes(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(cs, 'STORE', Path(tmp)), \
                mock.patch.object(cs, 'RELOAD_CHECK_SECONDS', 0):
            detector = cs.CustomSoundDetector()
            self.assertFalse(detector.maybe_reload())
            cs.create_sound('Microwave')
            self.assertTrue(detector.maybe_reload())
            self.assertFalse(detector.maybe_reload())

class DecodeTests(unittest.TestCase):
    def test_pcm_wav_any_rate_and_channels(self):
        for rate, channels in ((16000, 1), (48000, 2), (8000, 1)):
            samples = cs.decode_audio(wav_bytes(tone(440, 1, rate=rate), rate=rate, channels=channels))
            self.assertAlmostEqual(len(samples), 16000, delta=2)
            self.assertLess(np.abs(samples).max(), 1.01)
        with self.assertRaises(ValueError):
            cs.decode_audio(b'RIFF....garbage')

if __name__ == '__main__':
    unittest.main()
