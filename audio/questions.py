"""Questions someone asks the wearer, transcribed on the laptop right after their name or an attention call.

A hard-of-hearing wearer may notice someone said their name but miss what came next. When the name
spotter fires, this keeps the last PRE_SECONDS of audio plus up to CAPTURE_SECONDS after it, transcribes
that one clip with Moonshine tiny (sherpa-onnx, offline), and emits a "question" event when the clip
holds a question or request. Nothing else is transcribed and no audio is saved.

label is the short version for the glasses (font: A-Z 0-9 and ! - . / ?); transcript is what was said.
Shortening is local. With profile.name_detection.question_paraphrase on and a Claude key connected,
the receiver's POST /questions/paraphrase shortens it instead (text only, never audio).

Download the model: python -m audio.download_model --speech
"""
import json
import queue
import re
import threading
import time
import uuid
from urllib.request import Request, urlopen

import numpy as np

from audio.model import ROOT

MODEL = ROOT / '.cache' / 'models' / 'sherpa-onnx-moonshine-tiny-en-int8'
RATE = 16000
PRE_SECONDS = 2.0        # the name itself and anything just before it
CAPTURE_SECONDS = 6.0    # most questions finish within this after the name
MIN_SECONDS = 1.5        # never stop before the speaker has had a moment to start
QUIET_SECONDS = 0.8      # stop early once the speaker has paused this long
QUIET_RMS = 0.004
MAX_LABEL = 84           # 4 lines of 21 characters on the OLED (hardware/display.py render_question)

# Speech-to-text usually adds the '?'; these catch questions it leaves unpunctuated (first word only).
QUESTION_STARTS = {'what', 'when', 'where', 'who', 'whom', 'whose', 'why', 'how', 'which', 'is', 'are', 'am',
                   'were', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should', 'shall', 'may'}
REQUEST_STARTS = ('please', 'let me know', 'tell me', 'remember to', "don't forget", 'dont forget', 'make sure',
                  'come', 'grab', 'bring', 'hold on', 'wait', 'look', 'listen', 'help')
CALL_WORDS = ('hey you', 'hey there', 'excuse me', 'pardon me', 'hey', 'hello', 'hi', 'yo', 'oh', 'so', 'okay',
              'ok', 'um', 'uh', 'er', 'erm', 'well')
FILLERS = re.compile(r'\b(um+|uh+|er+m?)\b,?\s*', re.IGNORECASE)   # not "you know": "do you know where..."


def load_recognizer(threads=2):
    import sherpa_onnx
    if not (MODEL / 'tokens.txt').exists():
        raise RuntimeError('Speech model missing. Run: python -m audio.download_model --speech')
    return sherpa_onnx.OfflineRecognizer.from_moonshine(
        preprocessor=str(MODEL / 'preprocess.onnx'), encoder=str(MODEL / 'encode.int8.onnx'),
        uncached_decoder=str(MODEL / 'uncached_decode.int8.onnx'),
        cached_decoder=str(MODEL / 'cached_decode.int8.onnx'), tokens=str(MODEL / 'tokens.txt'),
        num_threads=threads)


def sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.?!])\s+', text.strip()) if s.strip()]


def strip_call(sentence, names=()):
    """Drop the vocative at the front: 'Hey Emma, um, are you coming?' -> 'are you coming?'."""
    words = sorted({w.lower() for w in (*CALL_WORDS, *names) if w}, key=len, reverse=True)
    lead = re.compile(r'^(?:' + '|'.join(re.escape(w) for w in words) + r')\b[\s,.!-]*', re.IGNORECASE)
    previous = None
    while previous != sentence:
        previous, sentence = sentence, lead.sub('', sentence, count=1)
    return sentence.strip()


def is_question(sentence):
    lowered = sentence.lower().strip()
    if lowered.endswith('?') or any(lowered == r or lowered.startswith(r + ' ') for r in REQUEST_STARTS):
        return True
    words = lowered.split()
    return bool(words) and re.sub(r'[^a-z]', '', words[0]) in QUESTION_STARTS and len(words) >= 3


def directed_question(transcript, names=()):
    """The question or request in the clip, without the name in front, or None."""
    for sentence in sentences(transcript):
        body = strip_call(sentence, names)
        if len(body.split()) >= 2 and is_question(body):
            first = re.sub(r'[^a-z]', '', body.split()[0].lower())
            return body + '?' if first in QUESTION_STARTS and body[-1] not in '.?!' else body
    return None


def for_display(text, limit=MAX_LABEL):
    """Short text the 5x7 OLED font can draw: no fillers, no commas or apostrophes, at most limit characters."""
    text = FILLERS.sub('', text)
    text = text.replace("'", '').replace('’', '')
    text = re.sub(r'[^A-Za-z0-9 !\-./?]+', ' ', text)
    text = ' '.join(text.split())
    if len(text) > limit:
        cut = text[:limit - 3].rsplit(' ', 1)[0]
        text = cut.rstrip(' .') + '...'
    return text[:1].upper() + text[1:]


def make_question_event(label, transcript, source, name_event, summary_source='local', timestamp_ms=None):
    return dict(schema_version=1, event_id=str(uuid.uuid4()), type='question', label=label,
                transcript=transcript[:600], summary_source=summary_source, confidence=None, source=source,
                priority_tier=3, timestamp_ms=timestamp_ms if timestamp_ms is not None else int(time.time() * 1000),
                # Same moment and speaker as the name, so the name's direction carries over.
                direction_degrees=name_event.get('direction_degrees'),
                direction_confidence=name_event.get('direction_confidence'),
                distance_meters=None, proximity='unknown',
                **{k: name_event[k] for k in ('direction_source', 'direction_reason') if k in name_event},
                after_event_id=name_event.get('event_id'))


def paraphrase(text, endpoint, timeout=4):
    """Ask the receiver to shorten with Claude; None when it is off, unconnected or slow."""
    try:
        request = Request(endpoint, data=json.dumps(dict(text=text)).encode(), method='POST',
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=timeout) as response:
            short = json.loads(response.read(4096)).get('short')
        return short if isinstance(short, str) and short.strip() else None
    except (OSError, ValueError):
        return None


class QuestionCatcher:
    """feed() every audio block; trigger() on a name/attention event. Questions arrive via on_event."""

    def __init__(self, on_event, profile=lambda: {}, paraphrase_url=None, recognizer=None, on_decision=None):
        self.recognizer = recognizer or load_recognizer()
        self.on_event, self.profile, self.paraphrase_url = on_event, profile, paraphrase_url
        self.on_decision = on_decision or (lambda decision: None)
        self.recent = np.zeros(0, dtype=np.float32)
        self.capture = None
        self.jobs = queue.Queue(maxsize=4)
        threading.Thread(target=self._work, daemon=True).start()

    def trigger(self, name_event, source):
        detection = self.profile().get('name_detection', {})
        if detection.get('questions', True) is False or self.capture is not None:
            return
        if str(name_event.get('matched_alias_id', '')).startswith('warning'):
            return   # "watch out" is the whole message
        self.capture = dict(samples=[self.recent.copy()], after=0, quiet=0, source=source, event=name_event)

    def feed(self, samples):
        samples = np.asarray(samples, dtype=np.float32)
        self.recent = np.concatenate((self.recent, samples))[-int(PRE_SECONDS * RATE):]
        capture = self.capture
        if capture is None:
            return
        capture['samples'].append(samples)
        capture['after'] += len(samples)
        loud = len(samples) and float(np.sqrt(np.mean(samples ** 2))) >= QUIET_RMS
        capture['quiet'] = 0 if loud else capture['quiet'] + len(samples)
        if capture['after'] >= CAPTURE_SECONDS * RATE or (
                capture['after'] >= MIN_SECONDS * RATE and capture['quiet'] >= QUIET_SECONDS * RATE):
            self.capture = None
            try:
                self.jobs.put_nowait(capture)
            except queue.Full:
                self.on_decision(dict(type='question', reason='busy'))

    def flush(self):
        """End a capture now (e.g. at the end of a recording) and wait for pending transcriptions."""
        if self.capture is not None:
            capture, self.capture = self.capture, None
            self.jobs.put(capture)
        self.jobs.join()

    def transcribe(self, samples):
        stream = self.recognizer.create_stream()
        stream.accept_waveform(RATE, samples)
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()

    def handle(self, capture):
        started = time.monotonic()
        transcript = self.transcribe(np.concatenate(capture['samples']))
        detection = self.profile().get('name_detection', {})
        names = [detection.get('primary_name') or '', *detection.get('aliases', [])]
        question = directed_question(transcript, names) if transcript else None
        # What people said is not written to the decision log; only its length.
        decision = dict(type='question', after_event_id=capture['event'].get('event_id'),
                        transcribe_ms=round((time.monotonic() - started) * 1000), words=len(transcript.split()))
        if not question:
            self.on_decision(dict(decision, reason='no_question'))
            return None
        label, source = for_display(question), 'local'
        if detection.get('question_paraphrase') and self.paraphrase_url:
            short = paraphrase(question, self.paraphrase_url)
            if short:
                label, source = for_display(short), 'claude'
        event = make_question_event(label, transcript, capture['source'], capture['event'], source)
        self.on_decision(dict(decision, reason='emitted', event_id=event['event_id']))
        self.on_event(event)
        return event

    def _work(self):
        while True:
            capture = self.jobs.get()
            try:
                self.handle(capture)
            except Exception as exc:   # one bad clip must never stop question capture
                self.on_decision(dict(type='question', reason='error', error=str(exc)[:200]))
            finally:
                self.jobs.task_done()
