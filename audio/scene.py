"""Play a simulated sound scene through the real recognizer into the live receiver.

Real labeled recordings (samples/benchmark) are mixed over background noise at the times and
simulated directions a scene file gives, then analysed window by window in real time exactly like
microphone audio. Recognized sounds are posted to the receiver with source "simulation" and the scene's
direction (marked direction_source "simulated"), so the companion and the glasses display react as they
would in the room. No microphone, phone or speakers are involved.

Run: .venv/bin/python -m audio.scene audio/scenes/demo.json --receiver http://127.0.0.1:8766
"""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

import numpy as np

from audio.benchmark import DATA
from audio.events import Detector, load_policy, runtime_model

RATE = 16000
SIDES = {'front': 0, 'right': 90, 'behind': 180, 'left': -90}


def clip_for(sound, manifest, pick=0):
    """A labeled recording for a sound type; held-out test clips first."""
    target = 'bicycle_bell' if sound == 'bell' else sound
    rows = [r for r in manifest['clips'] if target in r['expected']]
    rows.sort(key=lambda r: (r['split'] != 'test', r['id']))
    if not rows:
        raise ValueError(f'No recordings for {sound}')
    return rows[pick % len(rows)]


def build(scene, manifest, load_audio):
    """Mix the scene into one 16 kHz signal. Returns the signal and the placed sounds."""
    length = float(scene.get('length_seconds', 30))
    rng = np.random.default_rng(scene.get('seed', 1))
    signal = rng.normal(0, float(scene.get('noise_level', 0.01)), int(length * RATE)).astype(np.float32)
    placed = []
    for index, item in enumerate(scene['sounds']):
        row = clip_for(item['sound'], manifest, item.get('pick', index))
        audio = load_audio(DATA / row['path'])[:int(float(item.get('max_seconds', 5)) * RATE)]
        audio = audio * float(item.get('gain', 1.0))
        start = int(float(item['at']) * RATE)
        end = min(len(signal), start + len(audio))
        signal[start:end] += audio[:end - start]
        direction = item.get('direction')
        degrees = SIDES[direction] if isinstance(direction, str) else direction
        placed.append(dict(sound=item['sound'], start=start / RATE, end=end / RATE, clip=row['id'],
                           direction=direction, degrees=degrees))
    return np.clip(signal, -1, 1), placed


def post(endpoint, event):
    request = Request(endpoint, data=json.dumps(event).encode(), headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--receiver', default='http://127.0.0.1:8766')
    parser.add_argument('--model', choices=['yamnet', 'zipformer'], default=runtime_model())
    parser.add_argument('--speed', type=float, default=1.0, help='2 plays twice as fast (still real analysis)')
    parser.add_argument('--loop', action='store_true')
    args = parser.parse_args()
    from audio.model import create_model, load_audio

    scene = json.loads(args.scene.read_text())
    manifest = json.loads((DATA / 'manifest.json').read_text())
    signal, placed = build(scene, manifest, load_audio)
    print(f'Loading {args.model}…', file=sys.stderr)
    model = create_model(args.model)
    model.predict(np.zeros(model.window_samples, dtype=np.float32))
    endpoint = args.receiver.rstrip('/') + '/events'
    from audio.observations import ObservationPublisher, build_observation
    observer = ObservationPublisher(args.receiver.rstrip('/') + '/observations')
    print(f'Scene "{scene.get("name", args.scene.stem)}": {len(placed)} sounds over {len(signal) / RATE:.0f} s', flush=True)
    for p in placed:
        print(f'  {p["start"]:5.1f}s  {p["sound"]:<12} {p["direction"] or "no direction":<12} ({p["clip"]})', flush=True)

    from audio.custom_rules import CustomRules
    catalog = CustomRules()
    while True:
        detector = Detector(policy=load_policy(model_name=args.model))
        recognized = []
        start, base = time.monotonic(), int(time.time() * 1000)
        for offset in range(0, len(signal), model.hop_samples):
            window = signal[offset:offset + model.window_samples]
            if len(window) < model.window_samples:
                window = np.pad(window, (0, model.window_samples - len(window)))
            done = (offset + model.window_samples) / RATE  # scene time at the end of this window
            time.sleep(max(0, start + done / args.speed - time.monotonic()))
            scores, elapsed = model.predict(window)
            events = detector.detect(scores, 'simulation', now=done, timestamp_ms=base + int(done * 1000))
            events += catalog.detect(scores, 'simulation', now=done, timestamp_ms=base + int(done*1000))
            observer.publish(build_observation(
                scores, source='simulation', model=args.model, timestamp_ms=base + int(done * 1000),
                inference_ms=elapsed, window_rms=float(np.sqrt(np.mean(np.square(window)))),
                rule_decisions=detector.decisions, custom_decisions=catalog.decisions,
                custom_labels={r['id']:r['label'] for r in catalog.rules}, events=events,
                window_seconds=model.window_samples / RATE, hop_seconds=model.hop_samples / RATE))
            for event in events:
                # The scene sound playing in this window, if any, supplies the simulated direction.
                source = next((p for p in placed if p['start'] - 0.5 <= done <= p['end'] + 2.5
                               and (p['sound'] == event['type'] or {p['sound'], event['type']} <= {'bell', 'bicycle_bell'})), None)
                if source and source['degrees'] is not None:
                    event.update(direction_degrees=float(source['degrees']), direction_confidence=1.0,
                                 direction_source='simulated')
                try:
                    reply = post(endpoint, event)
                    outcome = reply.get('reason')
                except OSError as error:
                    outcome = f'receiver error: {error}'
                recognized.append((event['type'], source))
                where = source['direction'] if source and source['direction'] else 'no direction'
                print(f'[{done:5.1f}s] heard {event["type"]} ({event["confidence"]:.2f}, {where}) → {outcome}', flush=True)
        missed = [p for p in placed if not any(s is p for _, s in recognized)]
        false = [kind for kind, s in recognized if s is None]
        print(f'Scene done: {len(placed) - len(missed)}/{len(placed)} sounds recognized'
              + (f'; missed {", ".join(p["sound"] + "@" + format(p["start"], ".0f") + "s" for p in missed)}' if missed else '')
              + (f'; unexpected {", ".join(false)}' if false else ''), flush=True)
        if not args.loop:
            break


if __name__ == '__main__':
    main()
