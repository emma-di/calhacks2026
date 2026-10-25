"""Mac-only Pi microphone level bridge; numeric telemetry, never an HTTP audio stream.

Run explicitly: python -m audio.pi_levels --pi pi@glasses-pi.local --port 8768
Only stock arecord/SSH run on the Pi. No models, recordings, or receiver restart are involved.
"""
import argparse
import json
import math
import os
import re
import select
import shlex
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import numpy as np

SAMPLE_RATE = 48000
CHANNELS = 2
WINDOW_FRAMES = 4800  # 100 ms of interleaved S32_LE stereo
WINDOW_BYTES = WINDOW_FRAMES * CHANNELS * 4
FRESH_SECONDS = 1.2
STALL_SECONDS = 8.0


def levels_from_pcm(pcm):
    """One complete stereo window in, two independent numerical channel summaries out."""
    if not pcm or len(pcm) % (CHANNELS * 4):
        raise ValueError('PCM must contain complete interleaved stereo frames')
    data = np.frombuffer(pcm, dtype='<i4').reshape(-1, CHANNELS).astype(np.float64) / (2 ** 31)
    rms = np.sqrt(np.mean(data * data, axis=0))
    peaks = np.max(np.abs(data), axis=0)
    return [dict(channel=index,
                 rms_dbfs=round(20 * math.log10(max(float(rms[index]), 1e-6)), 2),
                 peak_dbfs=round(20 * math.log10(max(float(peaks[index]), 1e-6)), 2),
                 clip_fraction=round(float(np.mean(np.abs(data[:, index]) >= .999)), 6))
            for index in range(CHANNELS)]


def ssh_command(pi, device):
    # ssh runs its final argument through the remote login shell; quote each fixed/validated token.
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@:-]*', pi):
        raise ValueError('Invalid Pi SSH destination')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_:.,=+\-]*', device):
        raise ValueError('Invalid ALSA capture device')
    remote = shlex.join(['arecord', '-q', '-D', device, '-t', 'raw', '-f', 'S32_LE',
                         '-r', str(SAMPLE_RATE), '-c', str(CHANNELS)])
    return ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', '-o', 'ConnectionAttempts=1',
            '-o', 'ServerAliveInterval=2', '-o', 'ServerAliveCountMax=2',
            '-o', 'StrictHostKeyChecking=yes', pi, remote]


class LevelState:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.sequence = 0
        self.received = None
        self.levels = []
        self.error = 'Waiting for Pi microphone stream.'

    def update(self, pcm):
        levels = levels_from_pcm(pcm)
        with self.lock:
            self.sequence += 1
            self.received = self.clock()
            self.levels = levels
            self.error = None

    def disconnect(self, message):
        with self.lock:
            self.levels = []
            self.error = message

    def snapshot(self):
        with self.lock:
            age = None if self.received is None else max(0, self.clock() - self.received)
            connected = bool(self.levels) and age is not None and age <= FRESH_SECONDS
            return dict(schema_version=1, sample_rate=SAMPLE_RATE, channels=CHANNELS,
                        sequence=self.sequence, age_ms=None if age is None else round(age * 1000),
                        connected=connected,
                        levels=[dict(level) for level in self.levels] if connected else [],
                        error=self.error if self.error else (None if connected else 'Pi audio stream is stale.'))


def reap(process):
    """Never leave a previous SSH/capture connection alive while reconnecting."""
    try:
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass  # The child may exit between poll() and terminate().
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
        else:
            process.wait(timeout=2)
    finally:
        if process.stdout is not None:
            process.stdout.close()


class CaptureBridge:
    def __init__(self, state, pi, device, popen=subprocess.Popen):
        self.state = state
        self.command = ssh_command(pi, device)
        self.popen = popen
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, name='pi-audio-levels', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=6)

    def run(self):
        while not self.stop_event.is_set():
            process = None
            try:
                # Never create an unconsumed stderr pipe. SSH/ALSA output cannot leak through HTTP.
                process = self.popen(self.command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
                pending = bytearray()
                last_bytes = time.monotonic()
                while not self.stop_event.is_set():
                    ready, _, _ = select.select([process.stdout], [], [], .2)
                    if ready:
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            raise RuntimeError('Pi audio connection ended. Check the Pi and microphone capture device.')
                        last_bytes = time.monotonic()
                        pending.extend(chunk)
                        while len(pending) >= WINDOW_BYTES:
                            self.state.update(bytes(pending[:WINDOW_BYTES]))
                            del pending[:WINDOW_BYTES]
                    if time.monotonic() - last_bytes > STALL_SECONDS:
                        raise RuntimeError('Pi audio timed out. Retrying the microphone connection.')
            except RuntimeError as error:
                self.state.disconnect(str(error))
            except (OSError, ValueError):
                self.state.disconnect('Unable to open the Pi microphone stream. Check SSH and the capture device.')
            finally:
                if process is not None:
                    reap(process)
            if self.stop_event.is_set():
                break
            self.stop_event.wait(2)
        self.state.disconnect('Pi microphone bridge stopped.')


def create_server(state, port=8768):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            if urlsplit(self.path).path != '/levels':
                self.send_error(404)
                return
            payload = json.dumps(state.snapshot(), allow_nan=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            self.send_error(405)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pi', default='pi@glasses-pi.local')
    parser.add_argument('--device', default='hw:CARD=AwareINMP441,DEV=0')
    parser.add_argument('--port', type=int, default=8768)
    args = parser.parse_args()
    state = LevelState()
    bridge = CaptureBridge(state, args.pi, args.device)
    # Bind first: a port conflict must not start another microphone capture.
    server = create_server(state, args.port)
    bridge.start()
    print(f'Pi microphone levels: http://127.0.0.1:{server.server_port}/levels', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()
        server.server_close()


if __name__ == '__main__':
    main()
