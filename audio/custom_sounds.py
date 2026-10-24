"""Custom sounds: "teach it your doorbell" from a few recordings.

The Zipformer backbone stays frozen. Each custom sound gets a tiny logistic-regression head
trained on 256-number embeddings (audio/embeddings.py): the user's clips are positives and a
local background bank (other everyday sounds, silence, room noise) is negatives.

Everything lives under .cache/custom-sounds/ (gitignored): recordings, trained heads and the
background bank. Nothing is uploaded.

    python -m audio.custom_sounds build-background            # once; uses samples/benchmark
    python -m audio.custom_sounds add "Front doorbell" a.wav b.wav c.wav --tier 2
    python -m audio.custom_sounds test some-recording.wav
    python -m audio.custom_sounds list
    python -m audio.custom_sounds remove front-doorbell
"""
import argparse
import json
import math
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

from audio.model import ROOT

STORE = ROOT/'.cache'/'custom-sounds'
# Paths are resolved from STORE at call time (tests point STORE at a temporary folder).
def background_path(): return STORE/'background.npz'   # everyday sounds (build-background)
def room_path(): return STORE/'room.npz'               # the user's room, recorded in onboarding
def version_path(): return STORE/'version'             # touched on every change; detectors reload
WINDOW = 32000
HOP = 16000
ACTIVE_FRACTION = 0.25    # keep windows with RMS >= 25% of the loudest window in a clip
SILENCE_RMS = 1e-3        # never match (or train on) near-silent windows
MIN_THRESHOLD, MAX_THRESHOLD = 0.7, 0.97   # floor 0.7: see docs/custom-sounds.md sweep
TARGET_FALSE_ALERT_RATE = 0.005   # per window, measured on held-out background
MAX_CLIPS, MAX_CLIP_SECONDS = 20, 30
MAX_ROOM_CLIPS = 30
RELOAD_CHECK_SECONDS = 2

# ---------- audio helpers ----------

def windows(waveform):
    """2-second windows with 1-second hops, zero-padded at the end (same as the live CLI)."""
    import numpy as np
    waveform = np.asarray(waveform, dtype=np.float32)
    out = []
    for offset in range(0, max(len(waveform)-WINDOW, 0)+1, HOP):
        window = waveform[offset:offset+WINDOW]
        if len(window) < WINDOW:
            window = np.pad(window, (0, WINDOW-len(window)))
        out.append(window)
    if len(waveform) > WINDOW and (len(waveform)-WINDOW) % HOP:
        out.append(waveform[-WINDOW:])   # don't drop the tail of the clip
    return out

def decode_audio(data):
    """Uploaded audio bytes -> 16 kHz mono float32. PCM WAV needs only NumPy (stdlib `wave`);
    other formats (float WAV, FLAC, OGG) fall back to soundfile when installed."""
    import io
    import wave
    import numpy as np
    try:
        with wave.open(io.BytesIO(data)) as reader:
            width, channels, rate = reader.getsampwidth(), reader.getnchannels(), reader.getframerate()
            frames = reader.readframes(reader.getnframes())
        if width == 1:
            samples = (np.frombuffer(frames, np.uint8).astype(np.float32)-128)/128
        elif width in (2, 4):
            dtype = np.int16 if width == 2 else np.int32
            samples = np.frombuffer(frames, dtype).astype(np.float32)/np.iinfo(dtype).max
        else:
            raise ValueError(f'unsupported {8*width}-bit WAV')
        samples = samples.reshape(-1, channels).mean(axis=1)
    except (wave.Error, EOFError):
        try:
            import soundfile as sf
        except ImportError:
            raise ValueError('expected a PCM WAV file (16 kHz mono recommended)') from None
        try:
            samples, rate = sf.read(io.BytesIO(data), dtype='float32', always_2d=True)
        except Exception:
            raise ValueError('could not decode audio; send a WAV file') from None
        samples = samples.mean(axis=1)
    if rate != 16000:
        try:
            from math import gcd
            from scipy.signal import resample_poly
            divisor = gcd(rate, 16000)
            samples = resample_poly(samples, 16000//divisor, rate//divisor)
        except ImportError:
            positions = np.arange(0, len(samples), rate/16000)
            samples = np.interp(positions, np.arange(len(samples)), samples)
    return np.asarray(samples, dtype=np.float32)

def rms(window):
    import numpy as np
    return float(np.sqrt(np.mean(np.square(window, dtype=np.float64))))

def active_windows(waveform):
    """Windows that contain the sound rather than silence before/after it."""
    candidates = [(w, rms(w)) for w in windows(waveform)]
    loudest = max((level for _, level in candidates), default=0)
    if loudest < SILENCE_RMS:
        return []
    return [w for w, level in candidates if level >= max(ACTIVE_FRACTION*loudest, SILENCE_RMS)]

def clip_embeddings(embedder, waveform, active_only=True):
    import numpy as np
    selected = active_windows(waveform) if active_only else windows(waveform)
    if not selected:
        return np.empty((0, 256), dtype=np.float32)
    return np.stack([embedder.embed(w) for w in selected])

# ---------- head ----------

def normalize(embeddings, mean, std):
    import numpy as np
    x = (np.atleast_2d(embeddings)-mean)/std
    return x/np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-8)

def fit_logistic(x, y, l2=1.0, iterations=30):
    """Class-balanced L2 logistic regression via Newton/IRLS. x: (n,d), y: 0/1."""
    import numpy as np
    n, d = x.shape
    xb = np.hstack([x, np.ones((n, 1))])
    positives = max(y.sum(), 1)
    negatives = max(n-y.sum(), 1)
    sample_weight = np.where(y == 1, n/(2*positives), n/(2*negatives))
    w = np.zeros(d+1)
    ridge = l2*np.eye(d+1)
    ridge[-1, -1] = 0  # don't shrink the bias
    for _ in range(iterations):
        p = 1/(1+np.exp(-np.clip(xb@w, -30, 30)))
        gradient = xb.T@(sample_weight*(p-y)) + ridge@w
        hessian = (xb*(sample_weight*p*(1-p))[:, None]).T@xb + ridge
        step = np.linalg.solve(hessian, gradient)
        w -= step
        if np.max(np.abs(step)) < 1e-6:
            break
    return w[:-1], float(w[-1])

def head_scores(head, embeddings):
    import numpy as np
    x = normalize(embeddings, head['mean'], head['std'])
    return 1/(1+np.exp(-np.clip(x@head['weights']+head['bias'], -30, 30)))

def train_head(positives, background, background_groups=None, seed=0):
    """Train one sound's head. Threshold = the score exceeded by only
    TARGET_FALSE_ALERT_RATE of held-out background windows, clipped to [0.5, 0.97]."""
    import numpy as np
    if len(positives) == 0:
        raise ValueError('No usable (non-silent) audio in the recordings')
    if len(background) < 20:
        raise ValueError('Background bank too small; run build-background first')
    rng = np.random.default_rng(seed)
    groups = np.asarray(background_groups if background_groups is not None else np.arange(len(background)))
    unique = rng.permutation(np.unique(groups))
    held_out = np.isin(groups, unique[:max(1, len(unique)//5)])   # whole recordings, not windows
    mean = background.mean(axis=0)
    std = background.std(axis=0)+1e-6
    x = normalize(np.vstack([positives, background[~held_out]]), mean, std)
    y = np.concatenate([np.ones(len(positives)), np.zeros((~held_out).sum())])
    weights, bias = fit_logistic(x, y)
    head = dict(weights=weights.astype(np.float32), bias=bias, mean=mean.astype(np.float32), std=std.astype(np.float32))
    validation = head_scores(head, background[held_out])
    quantile = float(np.quantile(validation.astype(np.float64), 1-TARGET_FALSE_ALERT_RATE))
    threshold = min(max(quantile, MIN_THRESHOLD), MAX_THRESHOLD)
    training = head_scores(head, positives)
    head['threshold'] = threshold
    report = dict(threshold=round(threshold, 3), positive_windows=int(len(positives)),
                  background_windows=int(len(background)), held_out_background_windows=int(held_out.sum()),
                  held_out_false_alert_rate=round(float((validation >= threshold).mean()), 4),
                  training_recall=round(float((training >= threshold).mean()), 3))
    return head, report

# ---------- store ----------

def slugify(label):
    slug = re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')[:40] or 'sound'
    return slug

def validate_label(label):
    label = (label or '').strip()
    if not 0 < len(label) <= 60 or any(ord(c) < 32 for c in label):
        raise ValueError('label must be 1..60 printable characters')
    return label

def sound_dir(sound_id):
    if not re.fullmatch(r'[a-z0-9-]{1,64}', sound_id or ''):
        raise ValueError('invalid sound id')
    return STORE/sound_id

def read_meta(sound_id):
    return json.loads((sound_dir(sound_id)/'meta.json').read_text())

def touch_version():
    STORE.mkdir(parents=True, exist_ok=True)
    version_path().write_text(str(time.time_ns()))

def read_version():
    try:
        return version_path().read_text()
    except OSError:
        return None

def write_meta(meta):
    path = sound_dir(meta['id'])/'meta.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(meta, indent=2))
    temporary.replace(path)   # atomic, so the live detector never reads half a file
    touch_version()

def list_sounds():
    if not STORE.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(STORE.glob('*/meta.json'))]

def create_sound(label, priority_tier=2):
    label = validate_label(label)
    if type(priority_tier) is not int or not 1 <= priority_tier <= 4:
        raise ValueError('priority_tier must be 1..4')
    base = slugify(label)
    sound_id = base if not (STORE/base).exists() else f'{base}-{uuid.uuid4().hex[:6]}'
    (sound_dir(sound_id)/'clips').mkdir(parents=True)
    meta = dict(id=sound_id, label=label, priority_tier=priority_tier, enabled=True,
                status='recording', clip_count=0, created_ms=int(time.time()*1000), training=None)
    write_meta(meta)
    return meta

def add_clip(sound_id, waveform):
    """Store one 16 kHz mono recording for a sound (as the onboarding UI would upload it)."""
    import numpy as np
    meta = read_meta(sound_id)
    if meta['clip_count'] >= MAX_CLIPS:
        raise ValueError(f'at most {MAX_CLIPS} recordings per sound')
    waveform = np.asarray(waveform, dtype=np.float32)
    if not 0 < len(waveform) <= MAX_CLIP_SECONDS*16000:
        raise ValueError(f'recordings must be 0..{MAX_CLIP_SECONDS} seconds')
    write_wav(sound_dir(sound_id)/'clips'/f'{meta["clip_count"]:02d}.wav', waveform)
    meta['clip_count'] += 1
    if meta['status'] in ('ready', 'failed'):
        meta['status'] = 'needs_training'
    write_meta(meta)
    return meta

def clear_clips(sound_id):
    """Delete a sound's recordings (e.g. "start over") but keep its name and settings."""
    meta = read_meta(sound_id)
    for clip in (sound_dir(sound_id)/'clips').glob('*.wav'):
        clip.unlink()
    head = sound_dir(sound_id)/'head.npz'
    if head.exists():
        head.unlink()
    meta.update(clip_count=0, status='recording', training=None)
    write_meta(meta)
    return meta

def write_wav(path, waveform):
    import wave
    import numpy as np
    pcm = (np.clip(waveform, -1, 1)*32767).astype('<i2')
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(pcm.tobytes())

def update_sound(sound_id, changes):
    meta = read_meta(sound_id)
    unknown = set(changes)-{'label', 'priority_tier', 'enabled'}
    if unknown:
        raise ValueError(f'cannot change {sorted(unknown)}')
    if 'label' in changes:
        meta['label'] = validate_label(changes['label'])
    if 'priority_tier' in changes:
        if type(changes['priority_tier']) is not int or not 1 <= changes['priority_tier'] <= 4:
            raise ValueError('priority_tier must be 1..4')
        meta['priority_tier'] = changes['priority_tier']
    if 'enabled' in changes:
        if type(changes['enabled']) is not bool:
            raise ValueError('enabled must be true or false')
        meta['enabled'] = changes['enabled']
    write_meta(meta)
    return meta

def load_background():
    """Negatives for training: everyday sounds plus the user's recorded room, if any."""
    import numpy as np
    parts = [np.load(path) for path in (background_path(), room_path()) if path.exists()]
    if not parts:
        raise RuntimeError('No background yet. Run: python -m audio.custom_sounds build-background '
                           '(or record room background first)')
    return (np.vstack([p['embeddings'] for p in parts]),
            np.concatenate([p['groups'] for p in parts]))

def background_status():
    import numpy as np
    status = dict(base_windows=0, room_windows=0, room_clips=0)
    if background_path().exists():
        status['base_windows'] = int(len(np.load(background_path())['groups']))
    if room_path().exists():
        groups = np.load(room_path())['groups']
        status.update(room_windows=int(len(groups)), room_clips=int(len(np.unique(groups))))
    status['ready'] = status['base_windows']+status['room_windows'] >= 20
    return status

def add_room_background(embedder, waveform):
    """Add a recording of the user's ordinary room (chatter, HVAC, music) as negatives.
    Every window is used, quiet ones included; each clip is one held-out group."""
    import numpy as np
    waveform = np.asarray(waveform, dtype=np.float32)
    if not 0 < len(waveform) <= MAX_CLIP_SECONDS*16000:
        raise ValueError(f'recordings must be 0..{MAX_CLIP_SECONDS} seconds')
    embeddings = np.stack([embedder.embed(w) for w in windows(waveform)])
    old_embeddings, old_groups = np.empty((0, embeddings.shape[1]), np.float32), np.empty(0, np.int64)
    if room_path().exists():
        data = np.load(room_path())
        old_embeddings, old_groups = data['embeddings'], data['groups']
    clip = len(np.unique(old_groups))
    if clip >= MAX_ROOM_CLIPS:
        raise ValueError(f'at most {MAX_ROOM_CLIPS} room recordings; clear them first')
    group = 1_000_000+clip   # never collides with build-background group ids
    STORE.mkdir(parents=True, exist_ok=True)
    np.savez(room_path(), embeddings=np.vstack([old_embeddings, embeddings]).astype(np.float32),
             groups=np.concatenate([old_groups, np.full(len(embeddings), group)]))
    touch_version()
    return len(embeddings)

def clear_room_background():
    if room_path().exists():
        room_path().unlink()
    touch_version()

def retrain_trained(embedder):
    """Retrain every sound that has been trained before, e.g. after new room background."""
    results = []
    for meta in list_sounds():
        if meta['status'] in ('ready', 'needs_training', 'failed') and meta['clip_count']:
            try:
                results.append(train_sound(meta['id'], embedder))
            except Exception:
                results.append(read_meta(meta['id']))
    return results

def test_clip(sound_id, embedder, waveform):
    """Score one recording against a trained sound (onboarding's "try it once more")."""
    import numpy as np
    meta = read_meta(sound_id)
    path = sound_dir(sound_id)/'head.npz'
    if not path.exists():
        raise ValueError('sound is not trained yet')
    data = np.load(path)
    head = {k: data[k] for k in data.files}
    audible = [w for w in windows(waveform) if rms(w) >= SILENCE_RMS]
    if not audible:
        return dict(id=meta['id'], detected=False, score=0.0, threshold=float(head['threshold']), reason='silent')
    scores = head_scores(head, np.stack([embedder.embed(w) for w in audible]))
    best = float(scores.max())
    return dict(id=meta['id'], detected=best >= float(head['threshold']), score=round(best, 4),
                threshold=round(float(head['threshold']), 4), window_scores=[round(float(x), 4) for x in scores])

def train_sound(sound_id, embedder):
    import numpy as np
    meta = read_meta(sound_id)
    meta['status'] = 'training'
    write_meta(meta)
    try:
        clips = sorted((sound_dir(sound_id)/'clips').glob('*.wav'))
        if not clips:
            raise ValueError('record the sound at least once before training')
        positives = np.vstack([clip_embeddings(embedder, decode_audio(c.read_bytes())) for c in clips])
        if len(positives) == 0:
            raise ValueError('the recordings are silent; record the sound closer to the microphone')
        background, groups = load_background()
        head, report = train_head(positives, background, groups)
        np.savez(sound_dir(sound_id)/'head.npz', **head)
        meta.update(status='ready', training=dict(report, clips=len(clips), trained_ms=int(time.time()*1000)))
    except Exception as exc:
        meta.update(status='failed', training=dict(error=str(exc)))
        write_meta(meta)
        raise
    write_meta(meta)
    return meta

def remove_sound(sound_id):
    path = sound_dir(sound_id)
    if not (path/'meta.json').exists():
        raise KeyError(sound_id)
    shutil.rmtree(path)
    touch_version()

def load_heads():
    import numpy as np
    heads = []
    for meta in list_sounds():
        path = sound_dir(meta['id'])/'head.npz'
        if meta.get('status') == 'ready' and meta.get('enabled', True) and path.exists():
            data = np.load(path)
            heads.append((meta, {k: data[k] for k in data.files}))
    return heads

def build_background(embedder, folders, max_files=None, exclude_labels=()):
    """Embed every window (silent ones included) of the recordings in `folders`."""
    import numpy as np
    from audio.model import load_audio
    files = sorted(p for folder in folders for p in Path(folder).rglob('*') if p.suffix.lower() in ('.wav', '.flac', '.ogg', '.mp3'))
    files = [p for p in files if not any(token in p.name for token in exclude_labels)]
    if max_files:
        files = files[:max_files]
    if not files:
        raise RuntimeError('No audio found for the background bank. Run audio.prepare_benchmark first or pass folders.')
    embeddings, groups = [], []
    for index, path in enumerate(files):
        try:
            for window in windows(load_audio(path)):
                embeddings.append(embedder.embed(window))
                groups.append(index)
        except Exception as exc:
            print(f'Skipping {path.name}: {exc}', file=sys.stderr)
        if index % 50 == 0:
            print(f'{index}/{len(files)} recordings embedded', file=sys.stderr)
    embeddings = np.stack(embeddings).astype(np.float32)
    # Include true silence so the head never learns "quiet room = my sound".
    silence = embedder.embed(np.zeros(WINDOW, dtype=np.float32))
    embeddings = np.vstack([embeddings, silence[None]])
    groups = np.append(groups, -1)
    STORE.mkdir(parents=True, exist_ok=True)
    np.savez(background_path(), embeddings=embeddings, groups=np.asarray(groups))
    return len(files), len(embeddings)

# ---------- live detection ----------

class CustomSoundDetector:
    """Matches each live window's embedding against every ready custom sound."""
    def __init__(self, cooldown=5):
        self.cooldown = cooldown
        self.version = read_version()
        self.heads = load_heads()
        self.last = {}
        self.decisions = []
        self.checked = time.monotonic()

    def maybe_reload(self):
        """Pick up sounds taught, retrained, disabled or deleted while listening."""
        if time.monotonic()-self.checked < RELOAD_CHECK_SECONDS:
            return False
        self.checked = time.monotonic()
        version = read_version()
        if version == self.version:
            return False
        self.version, self.heads = version, load_heads()
        print('Custom sounds reloaded: '+(', '.join(m['label'] for m, _ in self.heads) or 'none'), file=sys.stderr)
        return True

    def detect(self, embedding, window_rms, source, now=None, timestamp_ms=None):
        from audio.events import make_custom_event
        self.maybe_reload()
        now = time.monotonic() if now is None else now
        self.decisions, events = [], []
        for meta, head in self.heads:
            decision = dict(type='custom', custom_sound_id=meta['id'], threshold=float(head['threshold']))
            if window_rms < SILENCE_RMS:
                decision.update(reason='silent_window', raw_score=0.0)
                self.decisions.append(decision)
                continue
            score = float(head_scores(head, embedding)[0])
            decision['raw_score'] = round(score, 4)
            if score < head['threshold']:
                decision['reason'] = 'below_threshold'
            elif now-self.last.get(meta['id'], -math.inf) < self.cooldown:
                decision['reason'] = 'cooldown'
            else:
                event = make_custom_event(meta, score, source, timestamp_ms)
                events.append(event)
                self.last[meta['id']] = now
                decision.update(reason='emitted', event_id=event['event_id'])
            self.decisions.append(decision)
        return events

# ---------- command line ----------

def main():
    from audio.embeddings import ZipformerEmbedder
    from audio.model import load_audio
    parser = argparse.ArgumentParser(description='Teach the recognizer your own sounds')
    sub = parser.add_subparsers(dest='command', required=True)
    bg = sub.add_parser('build-background', help='embed everyday sounds used as negatives')
    bg.add_argument('folders', nargs='*', default=[str(ROOT/'samples'/'benchmark')])
    bg.add_argument('--max-files', type=int)
    add = sub.add_parser('add', help='create a sound from recordings and train it')
    add.add_argument('label')
    add.add_argument('clips', nargs='+')
    add.add_argument('--tier', type=int, default=2)
    retrain = sub.add_parser('retrain')
    retrain.add_argument('id')
    remove = sub.add_parser('remove')
    remove.add_argument('id')
    sub.add_parser('list')
    room = sub.add_parser('add-room', help='add recordings of your ordinary room as negatives, then retrain')
    room.add_argument('clips', nargs='+')
    test = sub.add_parser('test', help='score a recording against every custom sound')
    test.add_argument('path')
    args = parser.parse_args()

    if args.command == 'list':
        for meta in list_sounds():
            print(json.dumps(meta))
        return
    if args.command == 'remove':
        remove_sound(args.id)
        print(f'Removed {args.id}')
        return
    embedder = ZipformerEmbedder()
    if args.command == 'build-background':
        files, count = build_background(embedder, args.folders, args.max_files)
        print(f'Background bank: {count} windows from {files} recordings -> {background_path()}')
    elif args.command == 'add':
        meta = create_sound(args.label, args.tier)
        for clip in args.clips:
            add_clip(meta['id'], load_audio(clip))
        print(json.dumps(train_sound(meta['id'], embedder), indent=2))
    elif args.command == 'add-room':
        for clip in args.clips:
            print(f'{clip}: {add_room_background(embedder, load_audio(clip))} windows', file=sys.stderr)
        for meta in retrain_trained(embedder):
            print(json.dumps(dict(id=meta['id'], status=meta['status'], training=meta['training'])))
    elif args.command == 'retrain':
        print(json.dumps(train_sound(args.id, embedder), indent=2))
    elif args.command == 'test':
        heads = load_heads()
        if not heads:
            sys.exit('No trained custom sounds. Add one first.')
        for index, window in enumerate(windows(load_audio(args.path))):
            embedding = embedder.embed(window)
            results = {meta['label']: round(float(head_scores(head, embedding)[0]), 3) for meta, head in heads}
            hits = [meta['label'] for meta, head in heads if rms(window) >= SILENCE_RMS and head_scores(head, embedding)[0] >= head['threshold']]
            print(json.dumps(dict(second=index, scores=results, detected=hits)))

if __name__ == '__main__':
    main()
