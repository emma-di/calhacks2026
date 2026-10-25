# CalHacks audio foundation

Recorded audio or microphone → local sound classifier → normalized event JSON → laptop alert monitor.
No API key, training, onboarding, or glasses required. Inference runs on the laptop.

**Default model: Zipformer Small INT8.** YAMNet remains available for comparison.
The current Zipformer suite covers 418 source recordings and 1,672 clean/quiet/noisy/echo cases.
The historical YAMNet comparison used the original 397-recording set.
Read [current results](../reports/summary.md) before choosing demo claims.

## One-command recorded demo (no microphone)

```sh
.venv/bin/python -m audio.demo --event dog_bark
```

Open http://127.0.0.1:8765. This starts/reuses the local receiver, classifies an actual
labeled recording, and leaves the monitor available. Ctrl+C exits.
Choose `knock`, `dog_bark`, `siren`, `alarm_clock`, `smoke_alarm`, or `bell`.
The last cue is labeled **Bell / chime**. Specific bicycle-bell recognition is disabled
in the default policy because it failed the benchmark. Generic bell recognition remains experimental.

Later, changing the input requires the same command with `--input mic --device <index>`.
An OS audio device can use that switch directly; a raw hardware stream or Quest display still needs an adapter.

## Run on this Mac

Complete the [project setup](demo.md#try-it-on-your-laptop) before running these project-root commands.
From the project directory, start the receiver:

```sh
.venv/bin/python -m audio.server
```

Open http://127.0.0.1:8765. In another terminal:

```sh
# Test the display without AI (explicitly labeled mock)
.venv/bin/python -m audio.cli fake bell

# List devices, then use the desired index (indices can change)
.venv/bin/python -m audio.cli devices
.venv/bin/python -m audio.cli mic --device 1 --debug --endpoint http://127.0.0.1:8765/events

# Reproduce the tested recorded knock
.venv/bin/python -m audio.cli file samples/door_wood_knock.wav --realtime --debug --endpoint http://127.0.0.1:8765/events

# Compare the original model explicitly
.venv/bin/python -m audio.cli --model yamnet file samples/dog.wav --debug
```

Ctrl+C stops capture. macOS may request microphone permission for the launching app.
Raw microphone audio is neither saved nor uploaded. Events go only to the endpoint you supply.
JSON goes to stdout; diagnostics go to stderr. Omit `--endpoint` for JSON-only operation.
`--seconds 10` bounds a microphone test. Replay events explicitly say `source: replay`.

## Fresh setup

Use Python 3.12 (tested on Apple Silicon), not the system Python 3.14:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m audio.download_model
.venv/bin/python -m audio.cli warmup
.venv/bin/python -m unittest discover -s tests -v
```

The initial model downloads require internet. Zipformer is cached in `.cache/models`;
YAMNet uses `.cache/tfhub` and downloads when selected for the first time.
`requirements.lock.txt` records the tested environment; `requirements.txt` states direct dependencies.
The setuptools constraint is required by TensorFlow Hub's legacy `pkg_resources` import.
On Linux, sounddevice may additionally require system PortAudio. Other platforms are untested.

## Implemented scope

- Zipformer and YAMNet adapters, with 16 kHz mono conversion.
- Default Zipformer uses two seconds of audio context and one-second hops; YAMNet uses ~0.975-second windows and 0.48-second hops.
- Microphone capture with a bounded queue; drops are reported and discontinuities reset the buffer.
- WAV/file replay, top-five diagnostics, per-window inference timing.
- Per-model rules tuned on designated source recordings, plus five-second per-class cooldown.
- Smoke and generic bell evidence is limited to a few source recordings; bicycle-specific output is disabled.
- Local HTTP receiver (`POST /events`), state (`GET /state`), dismiss (`POST /dismiss`, JSON `{}`).
- Browser monitor with source labels, basic tier precedence, auto-dismiss, and disconnect indication.

The monitor is integration scaffolding: lower-priority events during an active higher-priority alert
are logged but not queued for later display. Tier 4 has a deliberate 30-second timeout.
Preferences, a full alert queue, name recognition, OLED/Quest transport, and localization are not implemented.
The receiver is bound to loopback and has no authentication; do not expose it publicly.

## Reproduce offline tests

```sh
# Exact source list, attribution, and audio checksums are saved in this manifest
.venv/bin/python -m audio.prepare_benchmark --from-manifest reports/dataset-manifest.json
.venv/bin/python -m audio.benchmark --model zipformer --baseline-policy reports/round1-policy.json --tune-only bell bicycle_bell smoke_alarm alarm_clock
.venv/bin/python -m audio.benchmark --model yamnet
.venv/bin/python -m audio.simulate
```

The benchmark writes per-class reports and policy files. Tuning uses ESC-50 source folds 1–3;
evaluation uses folds 4–5. Supplemental recordings are separated by author.
All variants of a recording stay in its original split. Evaluation results have been inspected
during development; this is not a blind test. Synthetic noise/echo are controlled probes.
Public recordings may overlap model pretraining, and sparse labels may omit secondary sounds.

`audio/runtime.json` chooses the default model. `audio/policy-<model>.json` stores recognition
thresholds and label mappings. Notification preferences are a separate future stage.
No microphone or glasses are used by benchmark/simulation commands.

## Decision logs

File/microphone commands write bounded JSONL logs to `.cache/recognition-decisions.jsonl`.
Use `--decision-log <path>` to choose another file. They include the policy, per-window scores,
timestamps, recent context, emission/suppression reasons, and delivery results.
The receiver writes `.cache/alert-decisions.jsonl` for display/priority decisions and returns
recent decisions from `GET /state`. Each file rotates at 5 MB with two backups.
These logs contain metadata, not raw audio or transcripts.

The generic bell rule remembers recognized alarm context for four seconds, reducing duplicate
bell alerts on a fading alarm. [A real decision-log example](../reports/alarm-context-log-example.json)
shows an alarm clock recognized one second before a bell-like tail was suppressed.

## Name detection and onboarding (planned)

[Name-detection plan](name-detection-plan.md): a separate speech worker will consume the name,
aliases, language and enable/disable setting from the saved onboarding profile. It can first use
a local JSON profile so the website is not a prerequisite. No per-user model training or spoken
enrollment is planned. This contract is documented; name recognition and the profile endpoint
are not implemented yet.

## Event and hardware contract

See [integration notes](integration.md), [current results](../reports/summary.md), and [initial smoke tests](validation.md).
The source plan is [CalHacks 2026](https://app.notion.com/p/CalHacks-2026-402f37ac100480158629e54f772c8e88).
