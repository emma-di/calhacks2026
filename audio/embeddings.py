"""Zipformer scores plus a reusable sound embedding from one inference.

The audio-tagging Zipformer ends with: encoder frames -> linear classifier per frame ->
mean over time -> sigmoid. The time-averaged encoder frames (256 numbers per window) are
the embedding. Custom-sound heads are trained on that embedding while the backbone stays frozen.

This runs the same ONNX file as `audio.model.Zipformer` through onnxruntime with matching
Kaldi fbank features, so the 527 AudioSet scores are identical to the sherpa-onnx path
(verified to 0.0 difference on the bundled test WAVs). Requires `onnx`, `onnxruntime`
and `kaldi-native-fbank` (see requirements-audio.txt).
"""
import csv
import time

from audio.model import ROOT

MODEL_DIR = ROOT/'.cache'/'models'/'sherpa-onnx-zipformer-small-audio-tagging-2024-04-15'
EMBEDDING_OUTPUT = '/Transpose_1_output_0'  # encoder frames feeding the classifier
EMBEDDING_DIM = 256

def fbank(waveform):
    """80-bin Kaldi fbank with sherpa-onnx's audio-tagging defaults."""
    import numpy as np
    import kaldi_native_fbank as knf
    opts = knf.FbankOptions()
    opts.frame_opts.dither = 0
    opts.frame_opts.snip_edges = False
    opts.frame_opts.samp_freq = 16000
    opts.mel_opts.num_bins = 80
    opts.mel_opts.high_freq = -400
    extractor = knf.OnlineFbank(opts)
    extractor.accept_waveform(16000, np.asarray(waveform, dtype=np.float32).tolist())
    extractor.input_finished()
    return np.stack([extractor.get_frame(i) for i in range(extractor.num_frames_ready)]).astype(np.float32)

class ZipformerEmbedder:
    """Drop-in for audio.model.Zipformer: same window/hop and predict() contract,
    and the embedding of the most recent window is kept in `last_embedding`."""
    model_id = 'zipformer-small-int8/2024-04-15+embedding'
    sample_rate = 16000
    window_samples = 32000
    hop_samples = 16000

    def __init__(self, num_threads=2):
        import onnx
        import onnxruntime as ort
        from onnx import TensorProto, helper
        path = MODEL_DIR/'model.int8.onnx'
        if not path.exists():
            raise RuntimeError('Zipformer weights missing. Run: python -m audio.download_model')
        graph = onnx.load(str(path))
        graph.graph.output.append(helper.make_tensor_value_info(EMBEDDING_OUTPUT, TensorProto.FLOAT, None))
        options = ort.SessionOptions()
        options.intra_op_num_threads = num_threads
        options.log_severity_level = 3
        self.session = ort.InferenceSession(graph.SerializeToString(), options, providers=['CPUExecutionProvider'])
        with open(MODEL_DIR/'class_labels_indices.csv') as f:
            self.labels = [row['display_name'] for row in csv.DictReader(f)]
        self.last_embedding = None

    def run(self, waveform):
        """Return (scores dict, embedding vector, elapsed ms) for one window."""
        import numpy as np
        start = time.perf_counter()
        features = fbank(waveform)[None]
        logits, frames = self.session.run(None, {'x': features, 'x_lens': np.array([features.shape[1]], dtype=np.int64)})
        embedding = frames[0].mean(axis=0).astype(np.float32)
        scores = dict(zip(self.labels, map(float, logits[0])))
        return scores, embedding, (time.perf_counter()-start)*1000

    def predict(self, waveform):
        scores, self.last_embedding, elapsed = self.run(waveform)
        return scores, elapsed

    def embed(self, waveform):
        return self.run(waveform)[1]
