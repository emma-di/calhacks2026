"""Lazy-loaded YAMNet; cached weights, mono float32 at 16 kHz."""
import csv
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault('TFHUB_CACHE_DIR', str(ROOT / '.cache' / 'tfhub'))
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')

class Yamnet:
    model_id = 'yamnet/1'
    sample_rate = 16000
    window_samples = 15600  # 0.975s including STFT framing context
    hop_samples = 7680

    def __init__(self):
        import tensorflow_hub as hub
        from audio.events import load_policy
        self.model = hub.load('https://tfhub.dev/google/yamnet/1')
        with open(self.model.class_map_path().numpy().decode()) as f:
            self.labels = [r['display_name'] for r in csv.DictReader(f)]
        missing = {label for rule in load_policy(model_name='yamnet')['rules'].values() for label in rule['labels']} - set(self.labels)
        if missing:
            raise RuntimeError(f'Model labels missing: {missing}')

    def predict(self, waveform):
        import numpy as np
        start = time.perf_counter()
        scores, _, _ = self.model(np.asarray(waveform, dtype=np.float32))
        values = scores.numpy().max(axis=0)
        return dict(zip(self.labels, map(float, values))), (time.perf_counter()-start)*1000

class Zipformer:
    """CPU ONNX baseline with two seconds of acoustic context."""
    model_id = 'zipformer-small-int8/2024-04-15'
    sample_rate = 16000
    window_samples = 32000
    hop_samples = 16000

    def __init__(self):
        import sherpa_onnx as so
        folder=ROOT/'.cache'/'models'/'sherpa-onnx-zipformer-small-audio-tagging-2024-04-15'
        if not (folder/'model.int8.onnx').exists():
            raise RuntimeError('Zipformer weights missing. Run: python -m audio.download_model')
        config=so.AudioTaggingConfig(model=so.AudioTaggingModelConfig(
            zipformer=so.OfflineZipformerAudioTaggingModelConfig(model=str(folder/'model.int8.onnx')),
            num_threads=2,provider='cpu'), labels=str(folder/'class_labels_indices.csv'),top_k=527)
        if not config.validate():
            raise RuntimeError('Invalid Zipformer configuration')
        self.model=so.AudioTagging(config)

    def predict(self,waveform):
        import numpy as np
        start=time.perf_counter()
        stream=self.model.create_stream()
        stream.accept_waveform(sample_rate=16000,waveform=np.ascontiguousarray(waveform,dtype=np.float32))
        events=self.model.compute(stream)
        return {e.name:float(e.prob) for e in events},(time.perf_counter()-start)*1000

def create_model(name='yamnet'):
    return {'yamnet':Yamnet,'zipformer':Zipformer}[name]()

def load_audio(path):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    from math import gcd
    data, rate = sf.read(path, dtype='float32', always_2d=True)
    data = data.mean(axis=1)
    if rate != 16000:
        divisor = gcd(rate, 16000)
        data = resample_poly(data, 16000//divisor, rate//divisor)
    return np.asarray(data, dtype=np.float32)
