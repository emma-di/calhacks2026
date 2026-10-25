"""Spot-check approved cues against existing public recordings, without capture or a live receiver.

One held-out source per available category is a wiring/recognition spot-check, not an accuracy
benchmark. Prints and optionally saves real model scores, including failures. No downloads.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from audio.benchmark import windows
from audio.events import Detector, load_policy
from audio.model import Zipformer, load_audio

SOURCES = {
    'baby_cry': 'crying_baby', 'car_horn': 'car_horn', 'cat_meow': 'cat',
    'rain': 'rain', 'thunder': 'thunderstorm', 'wind': 'wind', 'clap': 'clapping',
    'footsteps': 'footsteps', 'train': 'train', 'laughter': 'laughing',
    'dog_bark': 'dog', 'knock': 'door_wood_knock', 'alarm_clock': 'clock_alarm',
    'emergency_siren': 'siren', 'breaking': 'glass_breaking', 'drip': 'water_drops',
}


def run():
    cues = json.loads((ROOT / 'audio/cue-catalog.json').read_text())['cues']
    manifest = json.loads((ROOT / 'samples/benchmark/manifest.json').read_text())
    model = Zipformer()
    results = []
    for cue in cues:
        category = SOURCES.get(cue['id'])
        rows = [row for row in manifest['clips'] if row['category'] == category
                and (ROOT / 'samples/benchmark' / row['path']).is_file()]
        rows.sort(key=lambda row: (row['split'] != 'test', row['id']))
        if not rows:
            continue
        row = rows[0]
        signal = load_audio(ROOT / 'samples/benchmark' / row['path'])
        detector = Detector(policy=load_policy(model_name='zipformer'))
        maxima, emitted = {}, set()
        for offset, window in windows(signal, model.window_samples, model.hop_samples):
            scores, _ = model.predict(window)
            for label in cue['model_labels'] + cue.get('fallback_labels', []):
                maxima[label] = max(maxima.get(label, 0), scores.get(label, 0))
            emitted.update(event['type'] for event in detector.detect(scores, 'replay', now=offset))
        peak = max(maxima[label] for label in cue['model_labels'])
        fallback_peak = max((maxima[label] for label in cue.get('fallback_labels', [])), default=0)
        recognized = ((peak >= cue['threshold'] or fallback_peak >= cue.get('fallback_threshold', 1)) if cue['event_type'] == 'custom'
                      else cue['event_type'] in emitted)
        result = dict(cue_id=cue['id'], source_id=row['id'], source_category=category,
                      split=row['split'], source_path=row['path'], source_sha256=row['sha256'],
                      peak_label_scores=maxima, catalog_threshold=cue['threshold'],
                      fallback_peak=fallback_peak, fallback_threshold=cue.get('fallback_threshold'),
                      recognition_path='catalog_rule' if cue['event_type'] == 'custom' else 'builtin_policy',
                      qualifies=recognized, builtin_emitted=sorted(emitted))
        results.append(result)
        print(f"{cue['id']}: {'detected' if recognized else 'MISSED'} ({peak:.4f})", flush=True)
    unavailable = [cue['id'] for cue in cues if cue['id'] not in {r['cue_id'] for r in results}]
    return dict(method='Real pretrained Zipformer inference on one existing held-out public recording per available mapped cue. No microphone, download, live receiver, profile changes or training. '
                       'This is not a representative accuracy evaluation: examples are few, classes overlap, and results have been inspected. Catalog thresholds are provisional.',
                model=model.model_id, recorded_cases=len(results),
                qualifying_cases=sum(r['qualifies'] for r in results),
                results=results, no_mapped_fixture=unavailable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = run()
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['qualifying_cases']}/{report['recorded_cases']} recording spot-checks qualified; "
          f"{len(report['no_mapped_fixture'])} cues have no mapped fixture here.")
