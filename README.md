# CalHacks 2026 · Situational Awareness Glasses

Turn relevant sounds into readable visual cues for Deaf and hard-of-hearing users.

**Sound → local recognition → event JSON → priority rules → laptop / glasses cue.**

The audio-to-laptop pipeline works. Hardware integration, spatial direction, name detection,
and the full onboarding UI are still being built. The default audio model is pretrained
**Zipformer Small INT8** with tuned recognition rules; its weights have not been fine-tuned.

## Start here

**[Current work status](WORK-STATUS.md)** · [Another Mac setup](docs/mac-setup.md)

**Latest decisions and caveats: [TEAM-NOTES.md](TEAM-NOTES.md). Coding agents start at [AGENTS.md](AGENTS.md).**

1. Accept your GitHub invitation and clone the repo.
2. Choose the mock-only or audio setup below.
3. Read [CONTRIBUTING.md](CONTRIBUTING.md) and create your task branch before editing.
4. Use [team workstreams](docs/team-workstreams.md) to coordinate interfaces and ownership.
5. Follow the [master TODO](TODO.md) and [browser/UI → backend build plan](docs/ui-ux-backend-plan.md).
6. Read the [distilled team build instructions](docs/team-build-instructions.md) and [sponsor and track build instructions](docs/sponsor-build-guide.md) before choosing frontend tools or a new backend.

```sh
gh repo clone emma-di/calhacks2026
cd calhacks2026
git switch -c yourname/short-task-name
```

## Polished browser companion

The [frontend guide](frontend/README.md) covers the simulator, audience mirror, exact 128×64 OLED
preview and connection to the existing receiver. Use Node 22.12+ to run it:

```sh
npm ci --prefix frontend
npm run dev --prefix frontend
```

Open http://127.0.0.1:5173. "This browser" mode needs no microphone or model. With
`python3 -m audio.server` running, choose Receiver: saved preferences, Work/Do not disturb, pause and
dismiss then drive the real receiver. The [alert engine doc](docs/alert-engine.md) covers the rules,
API and the Pi glasses client (`python3 -m hardware.oled_client`).
Read [AGENTS.md](AGENTS.md) for the agent entry point and [hardware stack](docs/hardware-stack.md)
for the original Pi Zero W + two INMP441s + SSD1306 plan. The [offline OLED renderer](docs/display-renderer.md)
can export fake 128×64 cues before device integration. Read [display UX](docs/display-ux.md) for
icon-first/peripheral design limits and [Mana onboarding](docs/mana-onboarding.md) for source handoff status.

## UI / hardware: run mock alerts immediately

This path needs only Python; no model, microphone, recordings, or ML packages.
From the project root, run:

```sh
python3 -m audio.server
```

Open **http://127.0.0.1:8765**. In a second terminal in the same folder:

```sh
python3 -m audio.cli fake knock
python3 -m audio.cli fake bell
python3 -m audio.cli fake smoke_alarm
```

Events are labeled `mock`. A smoke alarm has higher priority and persists for up to 30 seconds;
use **Dismiss alert** before checking lower-priority cues. Ctrl+C stops the server.

## Audio / ML: recognize a recording

Use **Python 3.12**. Apple Silicon macOS is the tested platform; other platforms need validation.
Commands below are for macOS/Linux; on Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-audio.txt
.venv/bin/python -m audio.download_model
.venv/bin/python -m audio.prepare_benchmark --from-manifest reports/dataset-manifest.json
.venv/bin/python -m audio.demo --event dog_bark
```

Open **http://127.0.0.1:8765**. The demo classifies a real labeled recording and sends its events
to the monitor. Initial downloads include the model and roughly 166 MB of public evaluation audio;
these files stay in your local cache. Choose `dog_bark`, `knock`, `siren`, `alarm_clock`, `smoke_alarm`, or `bell`.

For microphone input later:

```sh
.venv/bin/python -m audio.cli devices
.venv/bin/python -m audio.demo --input mic --device <device-index>
```

Replace `<device-index>` with an input index from the first command. macOS may ask for microphone
permission. Raw microphone audio is not saved. Decision logs contain scores, timestamps and rule reasons.

To also use the YAMNet baseline, install `requirements.txt`. `requirements.lock.txt` records the
full tested Mac environment. See the [audio guide](docs/audio-guide.md) for benchmark commands and diagnostics.

## Where things live

| Location | Purpose |
| --- | --- |
| `audio/model.py`, `audio/cli.py` | Local inference and capture/replay |
| `audio/events.py`, `audio/policy-*.json` | Event contract, thresholds, cooldown and recent-context rules |
| `audio/server.py` | Local event receiver and alert priority/state |
| `audio/monitor.html` | Basic debug monitor, with a live "Hearing now" meter |
| `audio/custom_sounds.py`, `audio/embeddings.py`, `audio/teach.html` | User-taught custom sounds; `/teach` page |
| `audio/names.py` | Name detection (streaming keyword spotter, learned spellings) |
| `audio/questions.py` | Transcribes the few seconds after your name and shows any question on the glasses (`python -m audio.download_model --speech`) |
| `audio/observations.py` | Per-window "what it heard" stream (`GET /observations`) |
| `audio/benchmark.py`, `audio/simulate.py` | Reproducible evaluation and multi-event scenarios |
| `tests/` | Fast unit checks; no weights or microphone required |
| `docs/` | Team handoffs, setup detail and planned contracts |
| `reports/` | Measurements, source manifests and example decision logs |

## Current readiness

- Environmental recognition, event JSON, mock events, laptop cues and decision logs are implemented.
- The current Zipformer evaluation covers **418 recordings / 1,672 transformed cases**.
- Generic bells improved, but false alerts remain. Bicycle-specific labeling stays disabled.
- Smoke-alarm evidence is limited; the final microphone and room still need testing.
- [Custom sounds](docs/custom-sounds.md): teach a sound from ~5 recordings at
  http://127.0.0.1:8765/teach; each taught sound is its own cue (generic sound icon, user's label).
  92% recall / 0.35% false alerts in an offline ESC-50 test; not yet validated live.
- [Name detection](docs/name-detection.md): listens for the name and nicknames from the profile (set them in
  the companion's Preferences), plus spellings learned from a short recording on `/teach`. 62% of name
  mentions caught on synthetic voices; not yet validated with real voices.
- `GET /observations` streams every analysis window (top labels, every rule's decision) for live views.
- Notification policy is implemented in one receiver engine (preferences, repeats, dismiss, Work/DND,
  pause, queue) with a matching browser simulator. A glasses client and SSD1306 driver exist and are
  tested in software; they have not yet driven the physical OLED.
- Spatial audio awaits synchronized capture. Direction is currently unknown.

Read [measured results](reports/summary.md) for counts, misses and false alerts. This prototype is
an awareness aid, not a certified emergency alert system.

## Shared interfaces and team workflow

- [Event / hardware contract](docs/integration.md)
- [Name detection and onboarding plan](docs/name-detection-plan.md)
- [Proposed profile example](docs/onboarding-profile.example.json) — not implemented yet
- [Branches, pull requests and testing](CONTRIBUTING.md)
- [Team responsibilities and first handoffs](docs/team-workstreams.md)

Keep `main` runnable. Push work to task branches and open pull requests; Python checks run on pushes
and PRs. Coordinate changes to the event schema, settings contract and shared dependencies.

**Never commit model weights, recordings, logs, environments or credentials.** Source manifests
include attribution and checksums so teammates can download the same test audio locally.
