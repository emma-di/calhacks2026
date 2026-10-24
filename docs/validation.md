# Initial validation — 2026-10-23

These are the initial YAMNet smoke tests. The later model comparison and tuned default are in
[current benchmark summary](../reports/summary.md) and [Zipformer detail](../reports/zipformer.md).

Environment: Apple Silicon Mac, Python 3.12.14, TensorFlow 2.20.0, YAMNet v1.

| Check | Observed result |
| --- | --- |
| Weight load and zero-input inference | Passed |
| Five unit tests: thresholds/cooldown, invalid scores, unknown spatial data, priority/expiry, ignore tier | Passed |
| Mock bicycle bell → HTTP receiver | Active alert returned correctly |
| Recorded door knock → model → HTTP → browser | Door knock visibly displayed, replay source, first emitted score 0.578 |
| Recorded dog clip | No Bark event at threshold 0.30; miss. Broader Dog label reached 0.722 in top-five diagnostics |
| Recorded speech/whistling fixture | Inference completed; no target events emitted |
| Target clips, 11 windows each | Median inference 2.4 ms, maximum 2.9 ms, after warmup |
| Five-second MacBook microphone capture | Passed; five inference windows, predominantly silence, no target alerts; capture stopped |
| Dependency consistency | pip check passed |

These are smoke tests, not an accuracy benchmark. One recording per target is insufficient to establish
reliability; public audio may overlap model training data. Inference timing is not end-to-end latency.
Bicycle bell, siren, and smoke alarm have mappings but have not been validated on real examples.

## Fixture provenance

Fixtures are downloaded locally and excluded from Git. Do not redistribute without observing source licenses.

- `samples/door_wood_knock.wav`: ESC-50 `1-101336-A-30.wav`, category `door_wood_knock`, fold 1.
- `samples/dog.wav`: ESC-50 `1-100032-A-0.wav`, category `dog`, fold 1.
- Dataset and licensing: https://github.com/karolpiczak/ESC-50
- `samples/speech_whistling2.wav`: https://storage.googleapis.com/audioset/speech_whistling2.wav

Downloaded ESC-50 files can be reproduced from:
`https://raw.githubusercontent.com/karolpiczak/ESC-50/master/audio/<filename>`.
