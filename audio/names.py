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

# Attention calls: someone trying to get the wearer's attention without using their name. Common in
# everyday talk, so they use a stricter threshold than names. profile.name_detection.attention_calls.
# Very short or constant words (yo, hi, sorry, wait) are left out: they would fire all day.
ATTENTION_PHRASES = ('HEY', 'HEY YOU', 'EXCUSE ME', 'HELLO', 'OVER HERE', 'COME HERE', 'GET OVER HERE',
                     'HEY THERE', 'PARDON ME', 'WAIT UP')
# Warnings mean danger, not a chat: they show as an urgent cue (alerts.effective_tier, warning- ids).
WARNING_PHRASES = ('WATCH OUT', 'LOOK OUT')
ATTENTION_BOOST, ATTENTION_THRESHOLD = 1.0, 0.25
# Multi-word phrases are distinctive enough for a looser match; danger warnings lean toward recall.
PHRASE_BOOST, PHRASE_THRESHOLD = 1.5, 0.15
WARNING_BOOST, WARNING_THRESHOLD = 2.0, 0.1

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
                                    sensitivity='balanced', learned_spellings=[], attention_calls=True))

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
    attention = detection.get('attention_calls', True)
    if type(attention) is not bool:
        raise ValueError('attention_calls must be true or false')
    result['name_detection'] = dict(enabled=enabled, primary_name=primary, aliases=aliases,
                                    language=language, sensitivity=sensitivity, attention_calls=attention,
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
    names_on = detection.get('enabled') is not False and bool(detection.get('primary_name'))
    entries = [('primary', detection['primary_name'])]+[(f'alias-{i}', a) for i, a in enumerate(detection['aliases'])]
    entries = entries if names_on else []
    lines, seen = [], set()
    for alias_id, name in entries:
        spoken = spoken_form(name)
        if not spoken:
            raise ValueError(f'"{name}" has no letters the English name model can match')
        tokens = ' '.join(tokenize(spoken))
        if tokens not in seen:
            seen.add(tokens)
            lines.append(f"{tokens} :{boost} #{threshold} @{alias_id}")
    if detection.get('attention_calls', True):
        phrases = [(f'attention-{i}', p) for i, p in enumerate(ATTENTION_PHRASES)]
        phrases += [(f'warning-{i}', p) for i, p in enumerate(WARNING_PHRASES)]
        for alias_id, phrase in phrases:
            tokens = ' '.join(tokenize(phrase))
            if tokens not in seen:
                seen.add(tokens)
                boost, threshold = (WARNING_BOOST, WARNING_THRESHOLD) if alias_id.startswith('warning') else \
                    (PHRASE_BOOST, PHRASE_THRESHOLD) if ' ' in phrase else (ATTENTION_BOOST, ATTENTION_THRESHOLD)
                lines.append(f"{tokens} :{boost} #{threshold} @{alias_id}")
    if not names_on:
        return lines
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

# Filler the tiny model hears around a short recording (silence, breath); stripped from the edges.
FILLER = {'AND', 'THE', 'A', 'AN', 'UH', 'UM', 'OH', 'SO', 'HEY', 'HI', 'OKAY', 'OK', 'AH', 'ER'}

def collapse_repeats(words, text, common=frozenset()):
    """People often say the name several times in one recording. 'YOU MEAN YOU MEAN YOU MEAN' -> 'YOU MEAN'
    (exact repetition). If attempts differ ('YEAH I MEAN YAMING YEAH I MEAN', 'YEMY YEMMING YEMY'), the
    most frequent distinctive (uncommon) word wins; failing that, the longest phrase heard at least twice.
    Without any repetition it's one saying and is returned unchanged."""
    n = len(words)
    keys = [text(w) for w in words]
    for size in range(1, n//2+1):
        if n % size == 0 and all(keys[i] == keys[i % size] for i in range(n)):
            return words[:size]
    if len(set(keys)) == n:
        return words   # nothing repeats: a single saying, possibly several words ("MARY JANE")
    distinctive = [k for k in keys if k not in common]
    if distinctive:
        best = max(distinctive, key=lambda k: (distinctive.count(k), -keys.index(k)))
        return [words[keys.index(best)]]
    for size in range(min(4, n//2), 0, -1):
        counts = {}
        for i in range(n-size+1):
            counts.setdefault(tuple(keys[i:i+size]), []).append(i)
        repeated = [(len(at), at[0]) for gram, at in counts.items() if len(at) >= 2]
        if repeated:
            _, start = max(repeated)
            return words[start:start+size]
    return words

def safe_spelling(tokens, allowed=()):
    """Returns (tokens, problem, warning). Strips filler at the edges and collapses repeats. A single
    common word ("why" for Wei, "don't" for John) is rejected: it would fire constantly. A phrase made
    only of common words ("you mean" for Yameen) is kept, with a warning that it can also fire on that phrase."""
    words = []
    for token in tokens:
        if token.startswith('▁') or not words:
            words.append([token])
        else:
            words[-1].append(token)
    text = lambda word: ''.join(word).replace('▁', '')
    while words and text(words[0]) in FILLER:
        words.pop(0)
    while words and text(words[-1]) in FILLER:
        words.pop()
    if not words:
        return None, 'nothing but filler was heard', None
    common = common_words()-set(allowed)   # a user named Grace may say "Grace"
    words = collapse_repeats(words, text, common)
    distinctive = [i for i, w in enumerate(words) if text(w) not in common]
    if distinctive:   # "EMMA WHO" -> "EMMA": trim common words around the name-like part
        words = words[distinctive[0]:distinctive[-1]+1]
    if sum(len(text(w)) for w in words) < 3:
        return None, 'too short to be reliable', None
    phrase = ' '.join(text(w) for w in words)
    if len(words) == 1 and phrase in common:
        return None, f'"{phrase}" is a common word and would trigger constantly', None
    warning = None
    if all(text(w) in common for w in words):
        warning = f'"{phrase}" is made of everyday words, so it may also alert when someone says "{phrase.lower()}"'
    return [t for w in words for t in w], None, warning

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
    tokens, problem, warning = safe_spelling(heard, allowed={w for n in names for w in spoken_form(n).split()})
    if problem:
        raise ValueError(f'Heard "{heard_text or "nothing"}"; not added because {problem}. Try again, saying only the name.')
    entry = dict(text=''.join(tokens).replace('▁', ' ').strip(), tokens=' '.join(tokens))
    typed = {' '.join(tokenize(spoken_form(n))) for n in names}
    known = typed | {i['tokens'] for i in detection['learned_spellings']}
    added = entry['tokens'] not in known
    if added:
        if len(detection['learned_spellings']) >= MAX_LEARNED:
            raise ValueError(f'at most {MAX_LEARNED} learned spellings; clear them first')
        detection['learned_spellings'].append(entry)
    return (profile if added else None), dict(heard=heard_text, spelling=entry['text'], added=added, warning=warning,
                         note=None if added else 'already covered by your typed name or an earlier recording')

# ---------- detection ----------

def make_name_event(profile, alias_id, source, timestamp_ms=None):
    """Schema-v2 name event (audio/events.py validate_name_event). Keyword spotting gives no calibrated
    score, so confidence is null with confidence_kind 'unavailable'."""
    label = ("Watch out!" if alias_id.startswith('warning') else
             "Someone's calling" if alias_id.startswith('attention') else 'Your name')
    return dict(schema_version=2, event_id=str(uuid.uuid4()), type='name_called', label=label,
                source=source, recognizer='sherpa-onnx-kws-zipformer-3.3M', confidence=None,
                confidence_kind='unavailable', matched_alias_id=alias_id,
                profile_revision=profile.get('revision', 0),
                priority_tier=4 if alias_id.startswith('warning') else 3,
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
        self.last = {}   # per kind, so a "hey" cannot hold back a "watch out" right after it
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
        names_on = detection['enabled'] and bool(detection['primary_name'])
        if not names_on and not detection.get('attention_calls', True):
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
        heard = ([detection['primary_name']]+detection['aliases'] if names_on else []) + \
            (['attention calls (hey, excuse me…, watch out)'] if detection.get('attention_calls', True) else [])
        print(f'Name detection: listening for {", ".join(heard)} (profile revision {profile["revision"]})', file=sys.stderr)
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
            kind = alias_id.split('-')[0] if alias_id.startswith('warning') else 'call'
            if getattr(self, 'repeat_suppression', True) and now-self.last.get(kind, -math.inf) < self.cooldown:
                decision['reason'] = 'cooldown'
            else:
                event = make_name_event(self.profile, alias_id, source, timestamp_ms)
                events.append(event)
                self.last[kind] = now
                decision.update(reason='emitted', event_id=event['event_id'])
            self.decisions.append(decision)
        return events
