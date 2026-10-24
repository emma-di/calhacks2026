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
BACKGROUND = STORE/'background.npz'
WINDOW = 32000
HOP = 16000
ACTIVE_FRACTION = 0.25    # keep windows with RMS >= 25% of the loudest window in a clip
SILENCE_RMS = 1e-3        # never match (or train on) near-silent windows
MIN_THRESHOLD, MAX_THRESHOLD = 0.7, 0.97   # floor 0.7: see docs/custom-sounds.md sweep
TARGET_FALSE_ALERT_RATE = 0.005   # per window, measured on held-out background
MAX_CLIPS, MAX_CLIP_SECONDS = 20, 30

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

def write_meta(meta):
    path = sound_dir(meta['id'])/'meta.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(meta, indent=2))
    temporary.replace(path)   # atomic, so the live detector never reads half a file

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
    import soundfile as sf
    meta = read_meta(sound_id)
    if meta['clip_count'] >= MAX_CLIPS:
        raise ValueError(f'at most {MAX_CLIPS} recordings per sound')
    waveform = np.asarray(waveform, dtype=np.float32)
    if not 0 < len(waveform) <= MAX_CLIP_SECONDS*16000:
        raise ValueError(f'recordings must be 0..{MAX_CLIP_SECONDS} seconds')
    sf.write(sound_dir(sound_id)/'clips'/f'{meta["clip_count"]:02d}.wav', waveform, 16000)
    meta['clip_count'] += 1
    write_meta(meta)
    return meta

def load_background():
    import numpy as np
    if not BACKGROUND.exists():
        raise RuntimeError('No background bank. Run: python -m audio.custom_sounds build-background')
    data = np.load(BACKGROUND)
    return data['embeddings'], data['groups']

def train_sound(sound_id, embedder):
    import numpy as np
    from audio.model import load_audio
    meta = read_meta(sound_id)
    meta['status'] = 'training'
    write_meta(meta)
    try:
        clips = sorted((sound_dir(sound_id)/'clips').glob('*.wav'))
        positives = [clip_embeddings(embedder, load_audio(c)) for c in clips]
        positives = np.vstack(positives) if positives else np.empty((0, 256), np.float32)
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
    shutil.rmtree(sound_dir(sound_id))

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
    np.savez(BACKGROUND, embeddings=embeddings, groups=np.asarray(groups))
    return len(files), len(embeddings)

# ---------- live detection ----------

class CustomSoundDetector:
    """Matches each live window's embedding against every ready custom sound."""
    def __init__(self, cooldown=5):
        self.cooldown = cooldown
        self.heads = load_heads()
        self.last = {}
        self.decisions = []

    def __bool__(self):
        return bool(self.heads)

    def detect(self, embedding, window_rms, source, now=None, timestamp_ms=None):
        from audio.events import make_custom_event
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
        print(f'Background bank: {count} windows from {files} recordings -> {BACKGROUND}')
    elif args.command == 'add':
        meta = create_sound(args.label, args.tier)
        for clip in args.clips:
            add_clip(meta['id'], load_audio(clip))
        print(json.dumps(train_sound(meta['id'], embedder), indent=2))
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
