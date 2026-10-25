"""Control safety checks; never open a real microphone."""
import importlib.util
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('recognizer_control', 'scripts/recognizer.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class RecognizerControlTests(unittest.TestCase):
    def test_sources_are_explicit_and_mutually_exclusive(self):
        pi = control.worker_command('pi')
        mac = control.worker_command('mac', device=7)
        self.assertIn('--pi', pi)
        self.assertNotIn('--device', pi)
        self.assertIn('--device', mac)
        self.assertNotIn('--pi', mac)
        self.assertEqual(mac[mac.index('--device') + 1], '7')
        with self.assertRaises(ValueError):
            control.worker_command('mac')

    def test_stale_pid_is_never_signalled(self):
        with patch.object(control, 'identity', return_value='different process'), patch.object(control.os, 'killpg') as kill:
            with self.assertRaises(RuntimeError):
                control.stop({'pid': 123, 'identity': 'old process'})
            kill.assert_not_called()

    def test_only_recognition_workers_match(self):
        self.assertTrue(control.MIC.search('.venv/bin/python -m audio.cli mic --pi pi@glasses-pi.local'))
        self.assertFalse(control.MIC.search('python -m audio.cli devices'))
        self.assertFalse(control.MIC.search('python scripts/recognizer.py pi'))

    def test_foreign_process_group_is_never_signalled(self):
        with patch.object(control, 'identity', return_value='same'), patch.object(control.os, 'getpgid', return_value=99), patch.object(control.os, 'killpg') as kill:
            with self.assertRaises(RuntimeError):
                control.stop({'pid': 123, 'identity': 'same'})
            kill.assert_not_called()

    def test_repeated_start_is_idempotent(self):
        import tempfile
        from pathlib import Path
        command = control.worker_command('pi')
        state = dict(pid=123, source='pi', command=command, identity='same')
        with tempfile.TemporaryDirectory() as folder, patch.object(control, 'CACHE', Path(folder)), patch.object(control, 'processes', return_value={123: 'worker'}), patch.object(control, 'managed', return_value=state), patch.object(control.subprocess, 'Popen') as launch, patch.object(control, 'urlopen') as request, patch('sys.argv', ['recognizer.py', 'pi']):
            control.main()
            launch.assert_not_called()
            request.assert_not_called()

    def test_unmanaged_worker_prevents_duplicate_capture(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder, patch.object(control, 'CACHE', Path(folder)), patch.object(control, 'processes', return_value={99: 'external worker'}), patch.object(control, 'managed', return_value=None), patch.object(control.subprocess, 'Popen') as launch, patch('sys.argv', ['recognizer.py', 'pi']):
            with self.assertRaisesRegex(RuntimeError, 'unmanaged recognizer'):
                control.main()
            launch.assert_not_called()

    def test_source_switch_stops_old_worker_before_launching_replacement(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock
        state = dict(pid=123, source='pi', command=control.worker_command('pi'), identity='same')
        order = []
        child = MagicMock(pid=456)
        child.poll.return_value = None
        def launch(*args, **kwargs):
            order.append('launch')
            return child
        with tempfile.TemporaryDirectory() as folder, patch.object(control, 'CACHE', Path(folder)), patch.object(control, 'STATE', Path(folder) / 'state.json'), patch.object(control, 'LOG', Path(folder) / 'log'), patch.object(control, 'processes', return_value={123: 'worker'}), patch.object(control, 'managed', return_value=state), patch.object(control, 'stop', side_effect=lambda _: order.append('stop')), patch.object(control, 'urlopen'), patch.object(control.subprocess, 'Popen', side_effect=launch), patch.object(control, 'identity', return_value='new identity'), patch.object(control.time, 'sleep'), patch('sys.argv', ['recognizer.py', 'mac', '--device', '7']):
            control.main()
            self.assertEqual(order, ['stop', 'launch'])
            self.assertEqual(control.json.loads(control.STATE.read_text())['source'], 'mac')
