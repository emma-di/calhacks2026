"""Few-shot evaluation of custom-sound heads on ESC-50 (no microphone).

Each of the 50 ESC-50 classes takes a turn as the "custom sound":
  * k training recordings from folds 1-3 (distinct source recordings),
  * test positives: that class in folds 4-5, excluding the training sources,
  * background bank: every other class in folds 1-3,
  * test negatives: every other class in folds 4-5 (about 1,560 recordings).
A recording counts as detected when any non-silent window scores above the head's threshold.

Embeddings are computed once and cached, since inference dominates the runtime:

    python -m audio.evaluate_custom --esc50 path/to/ESC-50 --shots 3 5 10 --repeats 3
"""
import argparse
import csv
import json
from pathlib import Path

from audio.model import ROOT

def embed_dataset(esc50, cache):
    import numpy as np
    from audio.custom_sounds import windows, rms
    from audio.embeddings import ZipformerEmbedder
    from audio.model import load_audio
    if cache.exists():
        return dict(np.load(cache))
    embedder = ZipformerEmbedder()
    rows = list(csv.DictReader(open(Path(esc50)/'meta'/'esc50.csv')))
    columns = {k: [] for k in ('emb', 'files', 'cat', 'fold', 'src', 'rms')}
    for index, row in enumerate(rows):
        for window in windows(load_audio(Path(esc50)/'audio'/row['filename'])):
            columns['emb'].append(embedder.embed(window))
            for key, value in (('files', row['filename']), ('cat', row['category']), ('fold', int(row['fold'])),
                               ('src', row['src_file']), ('rms', rms(window))):
                columns[key].append(value)
        if index % 100 == 0:
            print(f'{index}/{len(rows)}', flush=True)
    data = {k: np.asarray(v) for k, v in columns.items()}
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, **data)
    return data

def clip_hits(scores, files, threshold):
    """Map window scores to recording-level detections."""
    hits = {}
    for score, name in zip(scores, files):
        hits[name] = hits.get(name, False) or score >= threshold
    return hits

def evaluate(data, shots, repeats, seed=0):
    import numpy as np
    from audio.custom_sounds import ACTIVE_FRACTION, SILENCE_RMS, head_scores, train_head
    rng = np.random.default_rng(seed)
    emb, cat, fold, src, files, level = (data[k] for k in ('emb', 'cat', 'fold', 'src', 'files', 'rms'))
    loudest = {}
    for name, value in zip(files, level):
        loudest[name] = max(loudest.get(name, 0), value)
    active = np.array([value >= max(ACTIVE_FRACTION*loudest[name], SILENCE_RMS) for name, value in zip(files, level)])
    audible = level >= SILENCE_RMS
    tune, test = fold <= 3, fold >= 4
    results = {}
    for category in sorted(set(cat)):
        runs = []
        for _ in range(repeats):
            sources = rng.permutation(np.unique(src[(cat == category) & tune]))[:shots]
            train_files = []
            for source in sources:   # one recording per source recording
                options = np.unique(files[(cat == category) & (src == source)])
                train_files.append(rng.choice(options))
            positives = emb[np.isin(files, train_files) & active]
            bank = (cat != category) & tune
            head, report = train_head(positives, emb[bank], files[bank])
            threshold = head['threshold']
            test_pos = (cat == category) & test & ~np.isin(src, sources) & audible
            test_neg = (cat != category) & test & audible
            pos_hits = clip_hits(head_scores(head, emb[test_pos]), files[test_pos], threshold)
            neg_hits = clip_hits(head_scores(head, emb[test_neg]), files[test_neg], threshold)
            confused = {}
            for name, hit in neg_hits.items():
                if hit:
                    other = cat[files == name][0]
                    confused[other] = confused.get(other, 0)+1
            runs.append(dict(recall=np.mean(list(pos_hits.values())),
                             false_alert_rate=np.mean(list(neg_hits.values())),
                             false_alerts=int(sum(neg_hits.values())), negatives=len(neg_hits),
                             threshold=threshold, confused=confused))
        merged = {}
        for run in runs:
            for other, count in run['confused'].items():
                merged[other] = merged.get(other, 0)+count
        results[category] = dict(
            recall=round(float(np.mean([r['recall'] for r in runs])), 3),
            false_alert_rate=round(float(np.mean([r['false_alert_rate'] for r in runs])), 4),
            false_alerts_per_run=round(float(np.mean([r['false_alerts'] for r in runs])), 1),
            negatives=runs[0]['negatives'],
            threshold=round(float(np.mean([r['threshold'] for r in runs])), 3),
            most_confused_with=sorted(merged.items(), key=lambda x: -x[1])[:3])
    return results

def main():
    import numpy as np
    parser = argparse.ArgumentParser()
    parser.add_argument('--esc50', required=True, help='folder containing meta/esc50.csv and audio/')
    parser.add_argument('--cache', type=Path, default=ROOT/'.cache'/'esc50-embeddings.npz')
    parser.add_argument('--shots', type=int, nargs='+', default=[5])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path, default=ROOT/'reports'/'custom-sounds.json')
    args = parser.parse_args()
    data = embed_dataset(args.esc50, args.cache)
    report = {}
    for shots in args.shots:
        results = evaluate(data, shots, args.repeats)
        recall = np.mean([r['recall'] for r in results.values()])
        far = np.mean([r['false_alert_rate'] for r in results.values()])
        print(f'{shots}-shot: mean recall {recall:.3f}, mean false-alert rate {far:.4f} per negative recording')
        report[f'{shots}_shot'] = dict(mean_recall=round(float(recall), 3), mean_false_alert_rate=round(float(far), 4),
                                       classes=results)
    args.output.write_text(json.dumps(dict(dataset='ESC-50', protocol=__doc__.strip().splitlines()[2:9],
                                           repeats=args.repeats, results=report), indent=1))
    print(f'Wrote {args.output}')

if __name__ == '__main__':
    main()
