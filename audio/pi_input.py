"""Mac-only, single-owner Pi stereo capture shared by recognition and numeric meters."""
import queue
import threading
import time
import json
import math
from pathlib import Path

import numpy as np
from scipy.signal import firwin, lfilter

from audio.pi_levels import CaptureBridge, LevelState, create_server
from audio.pi_spatial import frame_evidence, window_evidence, unknown, assumed_front


def load_calibration(path=None):
    path = Path(path) if path else Path(__file__).resolve().parent.parent/'.cache'/'pi-spatial-calibration.json'
    try:
        value=json.loads(path.read_text())
        gain,margin=value['gain_offset_db'],value['margin_db']
        if (value.get('schema_version')==1 and type(gain) in (int,float) and math.isfinite(gain)
                and abs(gain)<=12 and type(margin) in (int,float) and math.isfinite(margin) and .25<=margin<=6):
            return float(gain),float(margin)
    except (OSError,ValueError,KeyError,TypeError):
        pass
    return 0.,1.25


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
        self.spatial = unknown('waiting_for_audio')
        self.spatial_frames = []
        self.recover_until = None
        self.gain_offset_db,self.margin_db=load_calibration()

    def reset_audio(self):
        self.generation += 1
        self.last_capture = None
        self.resampler.reset()
        self.spatial_frames = []
        self.spatial = unknown('capture_reset')
        self.recover_until = None
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
        # Normal SSH packet coalescing is NOT a capture gap: preserve all stereo frames.
        # After a real interruption, drain for 300ms before accepting a new window.
        if self.last_capture is not None and captured - self.last_capture > .5:
            self.reset_audio()
            self.recover_until = captured + .3
        self.last_capture = captured
        if self.recover_until is not None:
            if captured < self.recover_until:
                return
            self.recover_until = None
        if self.pending.full():
            self.reset_audio()
            self.last_capture = captured
        block = self.resampler.convert(pcm)
        evidence = frame_evidence(pcm,gain_offset_db=self.gain_offset_db,margin_db=self.margin_db)
        self.spatial_frames = (self.spatial_frames + [evidence])[-5:]
        self.spatial = window_evidence(self.spatial_frames)
        if any(frame['side'] is not None or frame['reason'] in
               ('balanced_or_ambiguous_delay','inconsistent_channels','timing_level_conflict')
               for frame in self.spatial_frames):
            self.spatial = assumed_front(self.spatial)
        self.pending.put_nowait((block, captured, int(time.time() * 1000), self.generation, evidence))
        super().update(pcm)

    def snapshot(self):
        value = super().snapshot()
        value['spatial'] = dict(self.spatial) if value['connected'] else unknown('offline')
        value['spatial_frame'] = dict(self.spatial_frames[-1]) if value['connected'] and self.spatial_frames else None
        value['spatial_calibration'] = dict(gain_offset_db=self.gain_offset_db,margin_db=self.margin_db)
        return value


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
