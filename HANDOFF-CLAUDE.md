# Aware — current handoff, October 25, 2026

Start with AGENTS.md, HANDOFF-NEXT.md and WORK-STATUS.md. Use the current checkout; older handoff
snapshots describing unfinished Xcode installation or Mac-primary audio are obsolete.

## Repository and ownership

- Repo: https://github.com/emma-di/calhacks2026
- Active branch: codex/browser-mirror. PR #2 is not merged to main. Do not force-push or merge it.
- Emma: onboarding, simulator, tier backend and display interaction. Root owns current UI prep.
- John: audio/speech and new **SPACE-PHONE-01** pocket-phone direction feasibility.
- Yameen: Pi, microphone wiring, display, optics and final physical assembly.
- Never stage/delete .claude/, credentials, signing state, private recordings, runtime logs or models.

## Actual checkpoint

Two INMP441 microphones on original Pi Zero W capture synchronized stereo48kHz S32_LE.
Channel0 physical LEFT,1 RIGHT; measured approximate spacing11–13cm. Mac performs inference.
One SSH/arecord capture feeds environmental/name recognition, direction evidence and numeric meters.
Do not open a second capture owner; no models/frontend belong on the Pi.

Real sound→event→priority→browser and actual SSD1306 OLED worked. User confirmed the display.
149/149 sampled active receiver state/display IDs matched in one live trial. The calibrated trial
had17 real fire-alarm detections:10 left diagonal,5 right diagonal,2 assumed-front. These repeated
counts are not localization accuracy, and source positions were not precisely timestamped.

**Hardware is now disconnected for assembly. Current work is prep only.**
Current rough-direction policy: eight45° buckets, front hemisphere assumed on ambiguous events.
Two mics do not measure rear direction or distance. Nominal angle geometry12cm;13cm lag limit.
Local centered reference corrected gain_offset_db−0.89, margin_db0.75. This is stored only in
.cache/pi-spatial-calibration.json and is not automatically transferred by Git. Inspect actual
loaded values through /pi-audio/levels → spatial_calibration after restarting.
See docs/rough-front-angles.md and docs/direction-calibration-acceptance.md.

## Live software and safe restart

Site http://127.0.0.1:5174/; receiver http://127.0.0.1:8766/; Pi telemetry8768.
Inspect ports/processes before restarting or creating duplicates. Receiver may hold an Anthropic
key in memory; restarting it clears that session key. UI suggestions work without blocking manual setup.

When hardware is back and capture is authorized:

```sh
.venv/bin/python -m audio.cli mic --pi pi@glasses-pi.local --endpoint http://127.0.0.1:8766/events
bash scripts/glasses_up.sh live
```

The first command also serves meter8768. Do not run audio.pi_levels beside it. Mac mic fallback is
explicit audio.cli mic --device <enumerated-index>; never silently switch inputs on Pi failure.
A noninteractive worker previously inherited ignored SIGINT and kept old settings. CLI now handles
SIGINT/SIGTERM explicitly; verify it actually exited and replacement settings loaded.
An orphan arecord once held ALSA after Wi-Fi loss. Inspect fuser/process identity before cleanup;
never indiscriminately kill audio services.

Dancing Bear /home/pi/oled_hello_bear.py PID1076 was paused with SIGSTOP to stop fighting the OLED.
Verify identity before any resume. Optical --flip-x / --flip-y review remains for final mounting;
no flip was applied in the spatial work. Repeat suppression was turned OFF for hardware tests;
choose final demo behavior explicitly afterward. Manual dismiss/optional phone gesture remain;
snap is parked. Alarm quiet clearing remains separate from an offline stream.

## John's pocket-phone task

Read HANDOFF-JOHN.md and docs/third-microphone-feasibility.md. A loose pocket phone is not a
sample-synchronized third Pi microphone. Separate raw3-channel TDOA (clock offsets/drift + changing
geometry) from existing native FOA direction (phone-relative vector + head-frame mapping).
The native probe and USB transport already exist; do not repeat Xcode/signing setup without checking.
John's first deliverable is a measured baseline/pocket-motion/head-turn/failure go/no-go report,
not speculative bearings attached to real alerts. Keep this outside the Pi demo critical path.

## Website and profile safeguards

First-use setup opens Preferences; defaults already active, optional typed name, curated sound
search with dedicated icons, optional reviewed Claude suggestions. Catalog choices need no training.
Unsupported free text is pending; optional recordings are advanced. Root is streamlining this flow
and testing it offline. Check the latest UI commit/status before modifying the same files.

Preserve receiver-authoritative profile hydration, existing Ignore choices, learned name spellings,
category inheritance, and explicit-edit synchronization. Do not turn a cold reload into a save.
Never treat Claude availability as an actual provider test. API keys are session-only; do not print
or copy one into a handoff. Personal descriptions/audio must not be sent to providers as test data.

80 relevant Python checks,58 frontend checks and build passed at the calibrated hardware checkpoint;
new UI work must record its own validation. Physical all-sound accuracy, mounted directional errors,
optical readability and disconnect/reconnect acceptance remain open.
