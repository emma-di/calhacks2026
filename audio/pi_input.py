"""Mac-only, single-owner Pi stereo capture shared by recognition and numeric meters."""
import queue
import threading
import time

import numpy as np
from scipy.signal import firwin, lfilter

from audio.pi_levels import CaptureBridge, LevelState, create_server


class StereoResampler:
    """Continuous antialiased 48k stereo → 16k mono; preserve filter state between blocks."""
    def __init__(self):
        self.taps = firwin(127, 1 / 3, window=('kaiser', 8))
        self.reset()

    def reset(self):
        self.zi = np.zeros(len(self.taps) - 1)
        self.phase = 0

    def convert(self, pcm):
        if not pcm or len(pcm) % 8:
            raise ValueError('Expected complete S32_LE stereo frames')
        stereo = np.frombuffer(pcm, dtype='<i4').reshape(-1, 2).astype(np.float64) / 2**31
        mono = stereo.mean(axis=1)
        filtered, self.zi = lfilter(self.taps, [1.], mono, zi=self.zi)
        result = filtered[(-self.phase) % 3::3].astype(np.float32)
        self.phase = (self.phase + len(mono)) % 3
        return result


class RecognitionState(LevelState):
    def __init__(self, pending, clock=time.monotonic):
        super().__init__(clock)
        self.pending = pending
        self.resampler = StereoResampler()
        self.last_capture = None
        self.generation = 0
        self.inference_input = 'pi_stereo'

    def reset_audio(self):
        self.generation += 1
        self.last_capture = None
        self.resampler.reset()
        while True:
            try:
                self.pending.get_nowait()
            except queue.Empty:
                break

    def disconnect(self, message):
        super().disconnect(message)
        self.reset_audio()

    def update(self, pcm):
        captured = self.clock()
        # SSH can deliver buffered bursts after a network pause. Discard bursts and reset;
        # do not process them as fresh observations (especially alarm quiet evidence).
        if self.last_capture is not None and captured - self.last_capture < .04:
            self.reset_audio()
            self.last_capture = captured
            return
        if self.last_capture is not None and captured - self.last_capture > .3:
            self.reset_audio()
        self.last_capture = captured
        if self.pending.full():
            self.reset_audio()
            self.last_capture = captured
        block = self.resampler.convert(pcm)
        self.pending.put_nowait((block, captured, int(time.time() * 1000), self.generation))
        super().update(pcm)


class PiInput:
    """Context manager replacing sounddevice capture; no Mac microphone is opened."""
    def __init__(self, pending, pi, device, port=8768):
        self.state = RecognitionState(pending)
        self.bridge = CaptureBridge(self.state, pi, device)
        self.port = port

    def __enter__(self):
        # A port conflict must not launch a competing ALSA owner.
        self.server = create_server(self.state, self.port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.bridge.start()
        return self

    def __exit__(self, *_args):
        self.bridge.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
