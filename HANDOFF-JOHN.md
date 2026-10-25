# John — handoff: live sound → signals, and phone spatial (October 24)

## CURRENT October25: John owns the pocket-phone experiment

**This section supersedes the older snapshot below.** Pi stereo recognition and the real OLED path
have now worked. Pi is primary input; Mac mic is manual fallback. Hardware is disconnected for
assembly, so current work is prep. Do not auto-start capture or claim an offline feed is live.

Your assigned item is **SPACE-PHONE-01** in [TODO](TODO.md):
**[Pocket-phone feasibility, existing probe and first deliverable](docs/third-microphone-feasibility.md)**.
Emma proposes a phone in a front pocket without a fixed position. Establish whether the existing
native FOA probe gives useful front/back evidence there; it is not a synchronized third raw mic.
The document separates both approaches and gives known-position baseline, pocket motion, head-turn,
multiple-source and failure tests. Return measured wrong-side/unknown counts and a go/no-go.
Phone orientation is not wearer head orientation. Keep unverified bearings out of real Pi alerts.

Current Pi implementation: [rough front angles](docs/rough-front-angles.md). The deliberate demo
policy is eight buckets with a front-hemisphere assumption; rear direction remains unresolved.
Centered balance is−0.89dB, margin0.75dB; calibration is Mac-local, not in a normal clone. Do not
overwrite it or start a second arecord owner. Reuse native probe/USB transport already in repo;
inspect generated local Xcode/signing state before repeating setup. Read [HANDOFF-NEXT](HANDOFF-NEXT.md)
and [direction acceptance](docs/direction-calibration-acceptance.md) before older commands below.

Emma and Claude are moving to the display. You own the audio side from here. Everything is pushed on
`codex/browser-mirror` (not merged to main). Read [AGENTS.md](AGENTS.md) first; the receiver's rules and
API are in [docs/alert-engine.md](docs/alert-engine.md).

## How sound becomes a cue today (all working)

```
mic / recording / simulated scene → recognizer (Zipformer, 2 s windows every 1 s)
  → audio/events.py Detector rules (policy-zipformer.json thresholds)
  → POST /events  ─┐
  → POST /observations (every window, your format) ─┤→ receiver (audio/server.py + audio/alerts.py)
phone FOA direction → POST /spatial ─┘      → priorities, modes, repeats, queue → /state, /display
                                                      → companion site + glasses client
```

Run (repo root):
```sh
.venv/bin/python -m audio.server --port 8766
.venv/bin/python -m audio.cli mic --device 1 --endpoint http://127.0.0.1:8766/events   # live mic
.venv/bin/python -m audio.scene audio/scenes/demo.json --receiver http://127.0.0.1:8766  # simulated
AWARE_RECEIVER=http://127.0.0.1:8766 npm run dev --prefix frontend -- --port 5174          # site
```
`audio.cli devices` lists microphones. In the site choose **Receiver**; Log → **What it's hearing**.

## Built this session (yours to extend)

- **Simulated scenes — `audio/scene.py`, `audio/scenes/demo.json`.** Mixes real labeled recordings
  (samples/benchmark) over background noise at scripted times and simulated directions, analyses
  them in real time like live audio and posts events + observations. Prints what was heard, what the
  receiver did, and missed/unexpected sounds. Demo scene: 6/6 recognized. `--speed 2` runs faster
  (but compresses cue lifetimes), `--loop` repeats.
- **Your observations, integrated.** `audio/observations.py` and `tests/test_observations.py` are
  taken unchanged from `johnaou/observations` (8a440e1). Ported only `ObservationStore` +
  `POST/GET /observations?since=` into the current receiver (your older server.py was not merged:
  it would drop queue/profiles/controls/display envelope). `audio/cli.py` (when `--endpoint` is set)
  and `audio/scene.py` publish one observation per window.
- **Listening heartbeat:** `/health.capture.listening` is true while observations keep arriving (3 s),
  so silence no longer looks like a dead mic. The site's pill shows **Listening**.
- **Signal panel:** Log page, one row per window: top labels/scores, level, and why nearby rules did or
  didn't fire (sent / cooling down / below threshold / held back by alarm context).

Tests: `.venv/bin/python -m unittest discover -s tests` (55 pass) and `npm test --prefix frontend` (18).

## Next steps on signals, in priority order

1. **Doorbell is a real gap.** The `bell` rule listens to `Bell`, `Ding`, `Chime` but not the model's
   `Doorbell` / `Ding-dong` classes. Add a `doorbell` signal (or extend `bell`).
2. **Fire alarm:** add the `Fire alarm` label to `smoke_alarm` (currently only "Smoke detector, smoke alarm").
3. Candidates, highest value first: **baby crying**, **car horn** (both have ESC-50 clips in the benchmark
   set for tuning), **phone ringing / ringtone**, **appliance beep** (microwave/oven).
4. **Real-room tuning:** several thresholds are very low (alarm_clock 0.05, knock/bell 0.075) — fine
   offline, risky for false alarms live. Use the signal panel + `audio/benchmark.py` with the final mic.
5. **Let people add any sound the model already knows (Emma's request).** Onboarding already saves
   custom sounds (e.g. "saxophone") but marks them *Recognition pending*. Zipformer scores ~527
   AudioSet classes every window (`Saxophone` is one; see
   `.cache/models/sherpa-onnx-zipformer-small-audio-tagging-2024-04-15/class_labels_indices.csv`), so a
   typed name can map to one or more model labels with no training:
   - match the typed name against the class list (exact/synonym, then fuzzy) and let the person confirm;
   - create a rule on the fly (labels + a default threshold, tighten with the signal panel), with the
     person's chosen priority from the profile and a generic icon on the glasses;
   - show "Recognized from the model's sound list" vs "needs teaching" in onboarding.
   Your custom-sounds branch (trained heads) then covers sounds *outside* the model's list. Both need the
   same receiver plumbing: custom event ids through the parser, per-custom-id repeat/ack identity,
   profile tier lookup and a generic OLED icon.

**Checklist for each new signal** (so the site, rules and glasses stay consistent):
- `audio/events.py` `TARGETS`: label, display name, default tier, base threshold.
- `audio/policy-zipformer.json` (+ `policy-yamnet.json`): rule labels + threshold; tune with
  `audio/benchmark.py` / `prepare_benchmark.py` if clips exist.
- `audio/alert-policy.json`: preset tiers (balanced/gentle/active) and `icons` mapping. A test checks the
  presets match `frontend/mana/AwareOnboarding.jsx` `AWARE_PRESET_DEFAULTS` — update both.
- `hardware/icons.py`: draw a 32×32 icon, run `python3 -m hardware.icons` then
  `python3 -m hardware.render_fixtures` (browser frames must stay byte-identical to Python).
- `frontend/src/lib/events.ts` (`EventType`, `soundCatalog`, `knownTypes`) and the Mana onboarding
  sound list so people can set its priority.
- Add a scene line in `audio/scenes/` that plays it, and check it in the signal panel.

## Phone spatial

Unchanged from [docs/phone-spatial-handoff.md](docs/phone-spatial-handoff.md): FOA verified on your
iPhone, USB bridge works, calibration still empty, background-noise lock-on and time matching open.
Also note Yameen's link to a **reSpeaker XVF3800** (4-mic array with on-chip direction over USB): if the
team gets one, it supplies both direction and the recognition audio from one device.

## Running on Emma's Mac right now

Receiver :8766, site :5174, phone USB bridge, old Codex receiver :8765 / site :5173 (old code — ignore).
The live Mac mic recognizer is **stopped**.
