import json
import math
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np

from audio.pi_levels import (CaptureBridge, LevelState, WINDOW_BYTES, WINDOW_FRAMES,
                             create_server, levels_from_pcm, reap, ssh_command)


def pcm(left, right, frames=WINDOW_FRAMES):
    return np.tile(np.array([left, right], dtype='<i4'), (frames, 1)).tobytes()


class PiLevelTests(unittest.TestCase):
    def test_independent_levels_signed_full_scale_and_clipping(self):
        levels = levels_from_pcm(pcm(2**30, -(2**29)))
        self.assertAlmostEqual(levels[0]['rms_dbfs'], -6.02, places=2)
        self.assertAlmostEqual(levels[1]['rms_dbfs'], -12.04, places=2)
        self.assertEqual(levels[0]['clip_fraction'], 0)
        clipped = levels_from_pcm(pcm(-(2**31), 2**31-1))
        self.assertEqual([x['clip_fraction'] for x in clipped], [1, 1])
        self.assertTrue(all(math.isfinite(x['peak_dbfs']) for x in clipped))
        quiet = levels_from_pcm(pcm(0, 0))
        self.assertEqual([x['rms_dbfs'] for x in quiet], [-120, -120])
        for bad in (b'', b'1234', b'123456789'):
            with self.assertRaises(ValueError):
                levels_from_pcm(bad)

    def test_staleness_and_disconnect_clear_meters_without_reusing_old_audio(self):
        clock = [10.0]
        state = LevelState(clock=lambda: clock[0])
        self.assertIsNone(state.snapshot()['age_ms'])
        state.update(pcm(2**29, 0))
        fresh = state.snapshot()
        self.assertTrue(fresh['connected'])
        self.assertEqual(fresh['sequence'], 1)
        fresh['levels'][0]['rms_dbfs'] = 99
        self.assertLess(state.snapshot()['levels'][0]['rms_dbfs'], 0)
        clock[0] += 1.3
        stale = state.snapshot()
        self.assertFalse(stale['connected'])
        self.assertEqual(stale['levels'], [])
        self.assertEqual(stale['age_ms'], 1300)
        state.update(pcm(0, 2**29))
        self.assertEqual(state.snapshot()['sequence'], 2)
        state.disconnect('Connection ended.')
        self.assertEqual(state.snapshot()['levels'], [])
        self.assertFalse(state.snapshot()['connected'])

    def test_ssh_arguments_are_bounded_noninteractive_and_reject_shell_injection(self):
        command = ssh_command('pi@glasses-pi.local', 'hw:CARD=AwareINMP441,DEV=0')
        self.assertIn('BatchMode=yes', command)
        self.assertIn('ConnectTimeout=5', command)
        self.assertIn('StrictHostKeyChecking=yes', command)
        self.assertIn('-t raw -f S32_LE -r 48000 -c 2', command[-1])
        self.assertNotIn('/home/', command[-1])
        for host in ('-oProxyCommand=bad', 'pi@host;touch /tmp/bad', 'pi@$(echo bad)'):
            with self.assertRaises(ValueError):
                ssh_command(host, 'hw:1,0')
        with self.assertRaises(ValueError):
            ssh_command('pi@host', 'hw:1;rm')

    def test_process_reaped_before_reconnect_even_when_terminate_times_out(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('ssh', 2), 0]
        reap(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        process.stdout.close.assert_called_once()

    def test_exit_race_during_child_cleanup_is_harmless(self):
        process = Mock()
        process.poll.return_value = None
        process.terminate.side_effect = ProcessLookupError()
        reap(process)
        process.wait.assert_called_once_with(timeout=2)
        process.stdout.close.assert_called_once()

    def test_fragmented_local_synthetic_stream_reassembles_stereo_windows_and_stops(self):
        # A local synthetic process, not SSH, hardware or a microphone.
        children = []
        def popen(_command, **kwargs):
            program = (
                'import os,struct,time\n'
                f'data=struct.pack("<ii",1073741824,-536870912)*{WINDOW_FRAMES*3}\n'
                'for i in range(0,len(data),4093): os.write(1,data[i:i+4093])\n'
                'time.sleep(2)\n'
            )
            process = subprocess.Popen([sys.executable, '-u', '-c', program], **kwargs)
            children.append(process)
            return process
        state = LevelState()
        bridge = CaptureBridge(state, 'pi@unused', 'hw:1,0', popen=popen)
        bridge.start()
        try:
            deadline = time.monotonic()+3
            while state.snapshot()['sequence'] < 3 and time.monotonic() < deadline:
                time.sleep(.01)
            snapshot = state.snapshot()
            self.assertEqual(snapshot['sequence'], 3)
            self.assertEqual(snapshot['levels'][0]['rms_dbfs'], -6.02)
            self.assertEqual(snapshot['levels'][1]['rms_dbfs'], -12.04)
        finally:
            bridge.stop()
        self.assertFalse(bridge.thread.is_alive())
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assertFalse(state.snapshot()['connected'])

    def test_failed_child_with_large_stderr_is_reaped_before_a_fresh_connection(self):
        children = []
        def popen(_command, **kwargs):
            if children:
                self.assertIsNotNone(children[-1].poll())
                program = 'import os,struct,time; os.write(1,struct.pack("<ii",1,2)*4800); time.sleep(2)'
            else:
                program = 'import os; os.write(2,b"private diagnostic"*10000)'
            process = subprocess.Popen([sys.executable, '-u', '-c', program], **kwargs)
            children.append(process)
            return process
        state = LevelState()
        bridge = CaptureBridge(state, 'pi@unused', 'hw:1,0', popen=popen)
        bridge.start()
        try:
            deadline = time.monotonic()+4
            while state.snapshot()['sequence'] < 1 and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertEqual(state.snapshot()['sequence'], 1)
            self.assertEqual(len(children), 2)
            self.assertNotIn('private', json.dumps(state.snapshot()))
        finally:
            bridge.stop()
        self.assertFalse(bridge.thread.is_alive())
        self.assertTrue(all(process.poll() is not None for process in children))

    def test_http_exposes_only_numeric_levels_and_binds_loopback(self):
        state = LevelState()
        state.update(pcm(0, 2**29))
        server = create_server(state, port=0)
        self.assertEqual(server.server_address[0], '127.0.0.1')
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base+'/levels') as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                snapshot = json.load(response)
            self.assertEqual(set(snapshot), {'schema_version', 'sample_rate', 'channels', 'sequence',
                                            'age_ms', 'connected', 'levels', 'error'})
            self.assertEqual(snapshot['channels'], 2)
            self.assertTrue(snapshot['connected'])
            for route in ('/audio', '/profile', '/levels.wav'):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base+route)
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
