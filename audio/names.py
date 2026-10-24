"""Name detection: "someone said your name".

Streaming keyword spotting with the sherpa-onnx Zipformer KWS model (3.3M parameters, English,
trained on GigaSpeech). The keywords are the typed name and aliases from the onboarding profile,
so there is no per-user training or spoken enrollment. Audio is processed in short blocks as it
arrives; nothing is transcribed, stored or uploaded.

Profile: .cache/profile.json, owned by the receiver (audio/server.py, GET/PUT /profile; schema in
audio/alerts.py). This module only reads it; a running recognizer reloads it within ~2 seconds.
"""
import json
import math
import re
import sys
import time
import unicodedata
import uuid

from audio.model import ROOT

KWS_NAME = 'sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01'
KWS_DIR = ROOT/'.cache'/'models'/KWS_NAME
PROFILE = ROOT/'.cache'/'profile.json'
RELOAD_CHECK_SECONDS = 2
COOLDOWN_SECONDS = 3
MAX_ALIASES = 8
MAX_LEARNED = 8
MAX_NAME_LENGTH = 40
WARMUP_SECONDS = 2.5   # streaming models ignore roughly the first 2 s after a stream starts

# Detection settings chosen on a synthetic multi-voice test (docs/name-detection.md).
DEFAULT_BOOST = 1.5
DEFAULT_THRESHOLD = 0.15
SENSITIVITY = {   # profile.name_detection.sensitivity -> (boost, threshold)
    'low': (1.0, 0.25),
    'balanced': (DEFAULT_BOOST, DEFAULT_THRESHOLD),
    'high': (2.0, 0.10),
}

# ---------- profile ----------

def default_profile():
    return dict(schema_version=1, profile_id='local', revision=0, display_name='',
                name_detection=dict(enabled=False, primary_name='', aliases=[], language='en',
                                    sensitivity='balanced', learned_spellings=[]))

def clean_name(value, field):
    if not isinstance(value, str):
        raise ValueError(f'{field} must be text')
    if any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError(f'{field} must be printable text')
    value = ' '.join(value.split())
    if len(value) > MAX_NAME_LENGTH:
        raise ValueError(f'{field} must be at most {MAX_NAME_LENGTH} characters')
    return value

def validate_profile(profile):
    """Validate and normalize a profile from the onboarding UI. Unknown top-level keys are kept
    (e.g. notification_preferences) so other workstreams can extend the same file."""
    if not isinstance(profile, dict):
        raise ValueError('profile must be a JSON object')
    result = default_profile()
    result.update({k: v for k, v in profile.items() if k not in ('revision', 'name_detection')})
    result['display_name'] = clean_name(profile.get('display_name', ''), 'display_name')
    detection = profile.get('name_detection', {})
    if not isinstance(detection, dict):
        raise ValueError('name_detection must be an object')
    enabled = detection.get('enabled', False)
    if type(enabled) is not bool:
        raise ValueError('name_detection.enabled must be true or false')
    primary = clean_name(detection.get('primary_name', '') or result['display_name'], 'primary_name')
    aliases = detection.get('aliases', [])
    if not isinstance(aliases, list) or len(aliases) > MAX_ALIASES:
        raise ValueError(f'aliases must be a list of at most {MAX_ALIASES}')
    aliases = [clean_name(a, 'alias') for a in aliases]
    if any(not a for a in aliases):
        raise ValueError('aliases cannot be empty')
    language = detection.get('language', 'en')
    if language != 'en':
        raise ValueError('only language "en" is supported by the current name model')
    sensitivity = detection.get('sensitivity', 'balanced')
    if sensitivity not in SENSITIVITY:
        raise ValueError(f'sensitivity must be one of {sorted(SENSITIVITY)}')
    if enabled and not primary:
        raise ValueError('a name is required to enable name detection')
    learned = detection.get('learned_spellings', [])
    if not isinstance(learned, list) or len(learned) > MAX_LEARNED:
        raise ValueError(f'learned_spellings must be a list of at most {MAX_LEARNED}')
    for item in learned:
        if (not isinstance(item, dict) or not isinstance(item.get('tokens'), str) or not isinstance(item.get('text'), str)
                or not 0 < len(item['tokens']) <= 200 or not 0 < len(item['text']) <= 60):
            raise ValueError('each learned spelling needs "text" and "tokens"')
    result['name_detection'] = dict(enabled=enabled, primary_name=primary, aliases=aliases,
                                    language=language, sensitivity=sensitivity,
                                    learned_spellings=[dict(text=i['text'], tokens=i['tokens']) for i in learned])
    return result

def load_profile():
    try:
        data = json.loads(PROFILE.read_text())
    except FileNotFoundError:
        return default_profile()
    profile = validate_profile(data)
    profile['revision'] = data.get('revision', 0) if type(data.get('revision', 0)) is int else 0
    return profile

def profile_stamp():
    try:
        return PROFILE.stat().st_mtime_ns
    except OSError:
        return None

# ---------- keywords ----------

def spoken_form(name):
    """Uppercase ASCII words for the English BPE model: 'José-Luis' -> 'JOSE LUIS'."""
    ascii_text = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r"[^A-Za-z']+", ' ', ascii_text).upper().split())

_bpe = None

def tokenize(text):
    global _bpe
    if _bpe is None:
        import sentencepiece as spm
        _bpe = spm.SentencePieceProcessor(model_file=str(KWS_DIR/'bpe.model'))
    return _bpe.encode(text, out_type=str)

def keyword_lines(profile):
    """sherpa-onnx keyword lines, one per spoken name: '▁JO H N :1.5 #0.15 @primary'."""
    detection = profile['name_detection']
    boost, threshold = SENSITIVITY[detection.get('sensitivity', 'balanced')]
    entries = [('primary', detection['primary_name'])]+[(f'alias-{i}', a) for i, a in enumerate(detection['aliases'])]
    lines, seen = [], set()
    for alias_id, name in entries:
        spoken = spoken_form(name)
        if not spoken:
            raise ValueError(f'"{name}" has no letters the English name model can match')
        tokens = ' '.join(tokenize(spoken))
        if tokens not in seen:
            seen.add(tokens)
            lines.append(f"{tokens} :{boost} #{threshold} @{alias_id}")
    vocabulary = model_vocabulary()
    for i, item in enumerate(detection.get('learned_spellings', [])):
        if item['tokens'] not in seen and all(t in vocabulary for t in item['tokens'].split()):
            seen.add(item['tokens'])
            lines.append(f"{item['tokens']} :{boost} #{threshold} @learned-{i}")
    return lines

# ---------- learning how the model hears a name ----------

_vocabulary = None
_common = None

def model_vocabulary():
    global _vocabulary
    if _vocabulary is None:
        _vocabulary = {line.split()[0] for line in (KWS_DIR/'tokens.txt').read_text().splitlines() if line.strip()}
    return _vocabulary

def common_words():
    """~1,000 common English words plus the model's own whole-word pieces (frequent by construction)."""
    global _common
    if _common is None:
        from pathlib import Path
        text = Path(__file__).with_name('common-words.txt').read_text()
        _common = {w.upper() for line in text.splitlines() if not line.startswith('#') for w in line.split()}
        _common |= {t[1:] for t in model_vocabulary() if t.startswith('▁') and len(t) >= 3 and t[1:].replace("'", '').isalpha()}
    return _common

def safe_spelling(tokens, allowed=()):
    """Strip common words at the edges; reject spellings that are or contain common words
    ("why" for Wei, "don't" for John) because they would fire constantly in conversation."""
    words = []
    for token in tokens:
        if token.startswith('▁') or not words:
            words.append([token])
        else:
            words[-1].append(token)
    text = lambda word: ''.join(word).replace('▁', '')
    common = common_words()-set(allowed)   # a user named Grace may say "Grace"
    while words and text(words[0]) in common:
        words.pop(0)
    while words and text(words[-1]) in common:
        words.pop()
    if not words:
        return None, 'only common words were heard'
    if any(text(w) in common for w in words):
        return None, 'it contains a common word'
    if sum(len(text(w)) for w in words) < 3:
        return None, 'too short to be reliable'
    return [t for w in words for t in w], None

_recognizer = None

def hear(waveform):
    """Decode a short recording with the keyword model as a tiny recognizer; returns its tokens."""
    global _recognizer
    import numpy as np
    import sherpa_onnx
    if _recognizer is None:
        model = lambda part: str(KWS_DIR/f'{part}-epoch-12-avg-2-chunk-16-left-64.int8.onnx')
        _recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(KWS_DIR/'tokens.txt'), encoder=model('encoder'), decoder=model('decoder'),
            joiner=model('joiner'), num_threads=1, decoding_method='modified_beam_search', max_active_paths=4)
    stream = _recognizer.create_stream()
    stream.accept_waveform(16000, np.concatenate([np.zeros(8000, np.float32), np.asarray(waveform, np.float32),
                                                  np.zeros(16000, np.float32)]))
    stream.input_finished()
    while _recognizer.is_ready(stream):
        _recognizer.decode_stream(stream)
    return [t.replace(' ', '▁') for t in _recognizer.get_result_all(stream).tokens]

def learn_spelling(waveform, profile):
    """How the model hears a recording of someone saying the name. Returns (updated profile or None, report);
    the caller saves the profile (the receiver owns the file)."""
    profile = json.loads(json.dumps(profile))
    detection = profile['name_detection']
    detection.setdefault('learned_spellings', [])
    detection.setdefault('aliases', [])
    if not detection['primary_name']:
        raise ValueError('set your name before recording it')
    heard = hear(waveform)
    heard_text = ' '.join(''.join(heard).replace('▁', ' ').split())
    names = [detection['primary_name']]+detection['aliases']
    tokens, problem = safe_spelling(heard, allowed={w for n in names for w in spoken_form(n).split()})
    if problem:
        raise ValueError(f'heard "{heard_text or "nothing"}"; not added because {problem}. Try again, saying only the name.')
    entry = dict(text=''.join(tokens).replace('▁', ' ').strip(), tokens=' '.join(tokens))
    typed = {' '.join(tokenize(spoken_form(n))) for n in names}
    known = typed | {i['tokens'] for i in detection['learned_spellings']}
    added = entry['tokens'] not in known
    if added:
        if len(detection['learned_spellings']) >= MAX_LEARNED:
            raise ValueError(f'at most {MAX_LEARNED} learned spellings; clear them first')
        detection['learned_spellings'].append(entry)
    return (profile if added else None), dict(heard=heard_text, spelling=entry['text'], added=added,
                         note=None if added else 'already covered by your typed name or an earlier recording')

# ---------- detection ----------

def make_name_event(profile, alias_id, source, timestamp_ms=None):
    """Name event in the receiver's v1 contract. Keyword spotting gives no calibrated score, so
    confidence is null (the receiver and companion accept a null score for name_called)."""
    return dict(schema_version=1, event_id=str(uuid.uuid4()), type='name_called', label='Your name',
                source=source, recognizer='sherpa-onnx-kws-zipformer-3.3M', confidence=None,
                confidence_kind='unavailable', matched_alias_id=alias_id,
                profile_revision=profile.get('revision', 0), priority_tier=3,
                timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time()*1000),
                direction_degrees=None, direction_confidence=None, distance_meters=None, proximity='unknown')

class NameDetector:
    """Feed audio as it arrives with accept(); returns name events. Reloads the profile on change."""
    def __init__(self, cooldown=COOLDOWN_SECONDS):
        import sherpa_onnx
        if not (KWS_DIR/'tokens.txt').exists():
            raise RuntimeError('Name model missing. Run: python -m audio.download_model --names')
        self.sherpa = sherpa_onnx
        self.cooldown = cooldown
        self.stamp = object()
        self.checked = -math.inf
        self.spotter = self.stream = None
        self.profile = default_profile()
        self.last = -math.inf
        self.decisions = []
        self.maybe_reload(force=True)

    @property
    def active(self):
        return self.stream is not None

    def maybe_reload(self, force=False):
        if not force and time.monotonic()-self.checked < RELOAD_CHECK_SECONDS:
            return False
        self.checked = time.monotonic()
        stamp = profile_stamp()
        if stamp == self.stamp:
            return False
        self.stamp = stamp
        try:
            profile = load_profile()
        except (ValueError, json.JSONDecodeError) as exc:
            print(f'Name detection: ignoring invalid profile ({exc})', file=sys.stderr)
            return False
        self.profile = profile
        detection = profile['name_detection']
        if not detection['enabled'] or not detection['primary_name']:
            self.spotter = self.stream = None
            print('Name detection: off (enable it in the profile)', file=sys.stderr)
            return True
        lines = keyword_lines(profile)
        keywords = ROOT/'.cache'/'name-keywords.txt'
        keywords.write_text('\n'.join(lines)+'\n')
        model = lambda part: str(KWS_DIR/f'{part}-epoch-12-avg-2-chunk-16-left-64.int8.onnx')
        self.spotter = self.sherpa.KeywordSpotter(
            tokens=str(KWS_DIR/'tokens.txt'), encoder=model('encoder'), decoder=model('decoder'),
            joiner=model('joiner'), keywords_file=str(keywords), num_threads=1)
        self.reset()
        names = [detection['primary_name']]+detection['aliases']
        print(f'Name detection: listening for {", ".join(names)} (profile revision {profile["revision"]})', file=sys.stderr)
        return True

    def reset(self):
        """Start a fresh stream, e.g. after an audio dropout. Warm it up with silence."""
        if self.spotter is None:
            return
        import numpy as np
        self.stream = self.spotter.create_stream()
        self.stream.accept_waveform(16000, np.zeros(int(WARMUP_SECONDS*16000), dtype=np.float32))
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            if self.spotter.get_result(self.stream):
                self.spotter.reset_stream(self.stream)

    def accept(self, samples, source, now=None, timestamp_ms=None):
        """Process new 16 kHz mono samples (any block size). Returns a list of name events."""
        self.maybe_reload()
        self.decisions = []
        if self.stream is None:
            return []
        now = time.monotonic() if now is None else now
        self.stream.accept_waveform(16000, samples)
        events = []
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            alias_id = self.spotter.get_result(self.stream)
            if not alias_id:
                continue
            self.spotter.reset_stream(self.stream)
            decision = dict(type='name_called', matched_alias_id=alias_id, profile_revision=self.profile['revision'])
            if now-self.last < self.cooldown:
                decision['reason'] = 'cooldown'
            else:
                event = make_name_event(self.profile, alias_id, source, timestamp_ms)
                events.append(event)
                self.last = now
                decision.update(reason='emitted', event_id=event['event_id'])
            self.decisions.append(decision)
        return events
