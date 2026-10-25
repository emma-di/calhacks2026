#!/usr/bin/env python3
"""Explicit Mac-side recognizer control. Never switches microphone sources automatically."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache'
STATE = CACHE / 'recognizer-process.json'
LOG = CACHE / 'recognizer-console.log'
MIC = re.compile(r'(?:^|\s)-m\s+audio\.cli\s+mic(?:\s|$)')


def worker_command(source, device=None, pi='pi@glasses-pi.local', endpoint='http://127.0.0.1:8766/events'):
    if source == 'mac' and device is None:
        raise ValueError('Mac mode requires --device INDEX; run devices first.')
    return [str(ROOT / '.venv/bin/python'), '-m', 'audio.cli', 'mic',
            *(['--pi', pi] if source == 'pi' else ['--device', str(device)]),
            '--endpoint', endpoint]


def processes():
    result = subprocess.run(['ps', '-axo', 'pid=,command='], capture_output=True, text=True, check=True)
    return {int(parts[0]): parts[1] for line in result.stdout.splitlines()
            if len(parts := line.strip().split(None, 1)) == 2 and MIC.search(parts[1])}


def identity(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart=,command='], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def managed(workers):
    try:
        state = json.loads(STATE.read_text())
        pid = state['pid']
        if pid in workers and identity(pid) == state['identity']:
            return state
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError):
        pass
    return None


def stop(state):
    if not state:
        return
    pid = state['pid']
    # Check again immediately before signalling; never kill a reused/stale PID.
    if identity(pid) != state['identity']:
        raise RuntimeError('Process identity changed; refusing to signal it.')
    if os.getpgid(pid) != pid:
        raise RuntimeError('Unexpected process group; refusing to signal it.')
    os.killpg(pid, signal.SIGTERM)
    for _ in range(100):
        if pid not in processes():
            STATE.unlink(missing_ok=True)
            print('Recognizer stopped.')
            return
        time.sleep(.1)
    raise RuntimeError('Recognizer has not stopped; no replacement started. Inspect status/logs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['pi', 'mac', 'stop', 'status', 'devices', 'logs'])
    parser.add_argument('--device', type=int)
    parser.add_argument('--pi', default='pi@glasses-pi.local')
    parser.add_argument('--endpoint', default='http://127.0.0.1:8766/events')
    parser.add_argument('--dry-run', action='store_true', help='Print the recognition command without opening a mic')
    args = parser.parse_args()
    if args.action in ('pi', 'mac'):
        command = worker_command(args.action, args.device, args.pi, args.endpoint)
        if args.dry_run:
            print(json.dumps(command))
            return
    if args.action == 'devices':
        subprocess.run([str(ROOT / '.venv/bin/python'), '-m', 'audio.cli', 'devices'], cwd=ROOT, check=True)
        return
    if args.action == 'logs':
        if LOG.exists():
            print('\n'.join(LOG.read_text(errors='replace').splitlines()[-40:]))
        else:
            print('No managed recognizer log yet.')
        return
    CACHE.mkdir(exist_ok=True)
    with (CACHE / 'recognizer-control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        workers = processes()
        state = managed(workers)
        external = {pid: cmd for pid, cmd in workers.items() if not state or pid != state['pid']}
        if args.action == 'status':
            print(f"Managed recognizer: {state['source']} · PID {state['pid']} (process running; not proof of audio)" if state else 'No managed recognizer running.')
            for pid, cmd in external.items():
                print(f'Unmanaged recognizer PID {pid}: {cmd}')
            return
        if args.action == 'stop':
            stop(state)
            if external:
                print('Unmanaged recognizer(s) left untouched; stop their original terminal before starting another.')
            elif not state:
                print('Already stopped.')
            return
        if external:
            raise RuntimeError('An unmanaged recognizer is already running (PID ' + ', '.join(map(str, external)) + '). Stop its original terminal first; no duplicate started.')
        if state and state['command'] == command:
            print(f"Already running {state['source']} · PID {state['pid']}; no duplicate started.")
            return
        # Avoid stopping a healthy worker if its replacement cannot reach the receiver.
        with urlopen(args.endpoint.rsplit('/events', 1)[0] + '/state', timeout=3) as response:
            response.read()
        stop(state)
        with LOG.open('ab', buffering=0) as output:
            output.write(f'\n--- Starting {args.action} recognizer ---\n'.encode())
            child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                     stdout=output, stderr=output, start_new_session=True)
        time.sleep(.2)
        if child.poll() is not None:
            raise RuntimeError('Recognizer exited during startup. Run logs to inspect the error.')
        STATE.write_text(json.dumps(dict(pid=child.pid, source=args.action, command=command, identity=identity(child.pid))))
        print(f'Started {args.action} recognizer · PID {child.pid}. Model loading may take a moment.')
        print('Check Log → Diagnostics on the site for actual incoming windows. No automatic Mac fallback.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
