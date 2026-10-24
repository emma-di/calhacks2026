import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar

from audio.server import create_server
from scripts.phone_mirror import ViewerHandler


class PhoneMirrorTests(unittest.TestCase):
    def test_only_authenticated_state_and_assets_are_exposed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'index.html').write_text('phone-viewer')
            receiver = create_server(port=0, profile_path=root / 'profile.json')
            viewer = ThreadingHTTPServer(('127.0.0.1', 0), partial(ViewerHandler, directory=folder))
            viewer.receiver = f'http://127.0.0.1:{receiver.server_port}'
            viewer.access_key = 'test-access-key'
            for server in (receiver, viewer):
                threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{viewer.server_port}'
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + '/api/state')
                self.assertEqual(error.exception.code, 403)
                client = build_opener(HTTPCookieProcessor(CookieJar()))
                self.assertEqual(client.open(base + '/?key=test-access-key').read(), b'phone-viewer')
                self.assertIn(b'"state_sequence"', client.open(base + '/api/state').read())
                for path, method, status in [('/api/profile', 'GET', 404), ('/api/dismiss', 'POST', 405), ('/api/profile', 'PUT', 405), ('/../AGENTS.md', 'GET', 404)]:
                    with self.subTest(path=path, method=method), self.assertRaises(HTTPError) as error:
                        client.open(Request(base + path, method=method))
                    self.assertEqual(error.exception.code, status)
            finally:
                for server in (viewer, receiver):
                    server.shutdown()
                    server.server_close()


if __name__ == '__main__':
    unittest.main()
