# Aware — resume here (October 24, 2026)

Emma requested this handoff because Codex usage is nearly exhausted. Continue from the current
checkout; do not restart or redesign the simulator. Read AGENTS.md, TEAM-NOTES.md and WORK-STATUS.md.

## Repository / branch

- Repo: https://github.com/emma-di/calhacks2026
- Working branch: `codex/browser-mirror`.
- PR #2: https://github.com/emma-di/calhacks2026/pull/2
- PR #2 targets `codex/ui-ux-backend-plan` (planning PR #1), **not main**. Nothing here is merged into main.
- Recent pushed checkpoints: ef00531 native spatial probe; ae5ed18 Leo review; 8c6bb2f phone audio setup;
  3bfb95e Continuity Camera support; c4acaac simulator freeze + read-only phone mirror.
- This handoff commit also includes the final diagnostic preservation change and real replay evidence.
- `.claude/` is Emma's existing untracked config. Do not add/delete/overwrite it.
- No credentials, signing identities, device identifiers, model weights or runtime audio belong in Git.

## IMMEDIATE NEXT ACTION: finish the native iPhone spatial test

The compiled/signed probe is open in Xcode and Run was pressed for **John’s iPhone**.
Latest observed Xcode activity: **“Extracting OS library symbols for John’s iPhone”**.
It finished copying symbols and is doing first-connect preparation. Leave the phone plugged in and
unlocked; do not start duplicate installs, repeatedly press Run, or kill Xcode while it prepares.
The app has **not yet been confirmed launched**. No spatial microphone capture has started.

Once it launches:
1. Ask John/Emma to confirm the app says **Aware spatial probe**.
2. Have them tap **Test spatial mic for 8 seconds** and allow microphone access on the phone.
3. Critical result: does it say **Verified FOA · 4 channels**, or unsupported/unexpected format?
4. If verified, fix the phone in one orientation and test one source at front/right/behind/left.
   The reported angle is encoder-frame, not yet calibrated wearer-frame. Check sign and rotation.
5. Test silence/room noise. Do not wire this into production alerts until physical evidence supports it.

The probe runs only after a tap, stops after 8 seconds or backgrounding, saves no audio and uploads
nothing. It currently displays experimental direction **on the phone only**. There is NO live
native-phone → Mac spatial transport, classifier association or OLED adapter yet.

### Xcode setup already completed — DON'T repeat it

- Full Xcode 27.1 downloaded from Apple's authenticated official download site and installed at
  `/Applications/Xcode.app`. The old xcode-select path in Downloads was stale.
- System components installed after Emma handled the Mac administrator prompt.
- Emma signed into Xcode and explicitly authorized **Emma Di (Personal Team)** signing and its
  development certificate/profile. Team selected; signed deployment was attempted.
- John connected/trusted the phone and enabled Developer Mode, restarted, reconnected/unlocked.
- CoreDevice verified **iPhone 18 Pro**, Developer Mode **enabled**, connection **connected**.
- Do not ask for these permissions again unless a materially different action is needed.
- Never collect passwords in chat. Installer/keychain prompts use the Mac login password; Xcode
  Apple Account sign-in uses the Apple Account password. Emma already resolved both.

### Native source / generated project

Source: `native/PhoneSpatialProbe/` and `scripts/prepare_iphone_spatial_probe.py`.
Generated project (ignored, SIGNING CONFIG LIVES HERE):
`.cache/iphone-spatial-probe/SpatialAudioDemo.xcodeproj`.
Unsigned build products/log: `.cache/iphone-spatial-build/` and `.cache/iphone-spatial-build.log`.
The Xcode GUI may use its own DerivedData for signed Run.

Preparation downloads Apple's licensed project shell; LICENSE is retained. The generated
`SpatialAudioDemo/AudioRecorder.swift` concatenates our FOADirection.swift + ProbeController.swift;
ContentView.swift is our UI. The unused Apple visualizer is stubbed. Preserve the generated project
and signing config. The preparation script refuses to overwrite an existing destination. If editing
our source, sync those generated source files without replacing project.pbxproj or the signing team.
No generated project/account state is committed.

Build verification (already passed):
```
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project .cache/iphone-spatial-probe/SpatialAudioDemo.xcodeproj \
  -scheme SpatialAudioDemo -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath .cache/iphone-spatial-build CODE_SIGNING_ALLOWED=NO build
```
Math-only checks: native/PhoneSpatialProbe/README.md — **80 synthetic cases passed**.
Avoid a bare xcrun if the global xcode-select path is still stale; set DEVELOPER_DIR per command.

### Spatial findings / limits

- Emma's iPhone 15 Pro / iOS 26.6 successfully supplies Continuity Camera video to the Mac.
- Continuity audio advertises **one mono channel** (“Emma Microphone”), even though native iOS can
  access richer microphone configurations. Mono cannot provide two-channel TDOA.
- Apple supports live FOA buffers via AVCaptureAudioDataOutput.spatialAudioChannelLayoutTag and
  runtime isMultichannelAudioModeSupported(.firstOrderAmbisonics). Probe targets John's newer phone.
- FOA is processed W,Y,Z,X encoding, NOT four raw physical microphones. Our experimental covariance
  estimator is separate from Leo's physical-array GCC-PHAT. Coherence is not calibrated probability.
- Silence, malformed/nonfinite data, low coherence and near-vertical vectors stay unknown in math tests.
- Input decoder verifies float PCM, four-channel ACN/SN3D layout, handles planar/interleaved buffers.
  iOS does NOT support setting AVCaptureAudioDataOutput.audioSettings; that compile issue is fixed.
- No Apple general “dog at 90°” API was found. SoundAnalysis supplies classifications/time ranges.
- Need actual format support, coordinate calibration, room accuracy, stream/clock handling and matching
  direction to the SAME sound/window recognized by ML. Never assign the loudest source to a different event.
- One phone should not simultaneously be a locked Continuity camera and run the native probe.
  Use Emma's phone for POV, John's for native spatial audio during the experiment.

Details + primary Apple links: docs/phone-direction-research.md and native/PhoneSpatialProbe/README.md.

## Running services — leave the working demo intact

Snapshot at handoff (PIDs can change; check ports first):
- Companion: http://127.0.0.1:5174/ — Vite PID 19481; current proxy uses receiver 8766.
- Current priority/settings receiver: http://127.0.0.1:8766/ — Python PID 29809.
- Older monitor/receiver: http://127.0.0.1:8765/ — Python PID 9238. Don't assume this is the new engine.
- Read-only phone alert mirror: Wi-Fi interface 10.60.22.103:5176 — Python PID 30534.
  Requires the temporary access key already shared privately. Do NOT commit/publish it. Script:
  scripts/phone_mirror.py. Only authenticated GET state + build assets; writes blocked. No camera there.
- Leo's standalone simulated map: http://127.0.0.1:8878/ — Python PID 32307, running from
  `/tmp/aware-leo-review-20261024`, with `--no-audio` to avoid fake directions on real events.
- No microphone classifier was started by Codex during this session. Don't auto-start one.

Use **Receiver** mode in the companion for cross-device alerts. Browser simulation is local to one
browser and does not mirror across devices. The phone alert viewer cannot overwrite preferences.
Use only one settings-owning companion; multiple full companions can auto-sync competing profiles.
Venue Wi-Fi can isolate devices. Phone viewer uses trusted-LAN HTTP, no public tunnel.

## John's branches — checked but NOT merged

`origin/johnaou/custom-sounds` at 87aff0d / 9146609:
- Frozen Zipformer embeddings + small per-sound heads, local teaching/background/test routes.
- **8 model/storage tests + 6 HTTP tests passed** in isolated archive `/tmp/aware-john-review-20261024`.
- Branch starts from an older receiver. DO NOT replace our current server with it: that loses queue,
  profiles, controls, display envelope, scoped dismiss, health, etc.
- Need custom event parser support, per-custom-ID repeat/ack/settings identity, and a generic OLED icon.
  Current onboarding arbitrary names remain **pending metadata**, not recognized sounds.
- Missing local deps for heads: onnx, onnxruntime, kaldi-native-fbank. Not installed yet.
- See docs/john-audio-review.md and John's branch docs/custom-sounds.md.

`origin/johnaou/observations` at 8a440e1:
- Per-window top-k scores, rule/custom outcomes, levels and emitted event IDs; no audio/transcript.
- **6 observation tests passed**, including nonblocking publisher under a stalled receiver.
- ALSO tested a real cached dog.wav through its actual Zipformer CLI + ephemeral isolated receiver:
  exit 0, **5 observations + 1 dog_bark event**, all source=replay. No microphone, custom heads disabled.
- Isolated branch copy: `/tmp/aware-john-observations-20261024`. Model files linked read-only from main cache.
- NOT integrated into our current backend/UI. Preserve current APIs when porting. John is now working
  on speech/name recognition separately; don't duplicate that work or claim it is already connected.

## Leo's spatial branch — checked but NOT merged

`origin/lragogna/audio-triangulation` at ff840bc / f8ab296:
- **17 synthetic spatial tests pass**. Standalone simulator running on 8878.
- Found reproducible live blocker: all-zero two-channel input crashes localize with empty peak list.
  One-channel input with two-mic geometry also crashes. Add guards before any real capture adapter.
- Two physical mics give front/back mirror ambiguity. His head-motion resolver needs measured yaw;
  walking simulation generates yaw, but no IMU is in the confirmed hardware list.
- No real capture → localized event adapter exists yet. Simulator positions are synthetic/random,
  not measured. No distance inference. See docs/leo-spatial-review.md.

## Emma's UI/backend role — checkpoint / freeze

Already implemented: five tiers; per-sound → optional category → preset → producer fallback;
ordering/interruption/fresh bounded queue; repeats/cooldowns/scoped dismiss; Work/DND/Pause;
browser-local + atomically persisted receiver onboarding; names/aliases; pending custom labels;
shared laptop/OLED renderer; diagnostics/log/audience mode; exact 128×64 layout.

Physical display is only on RIGHT side of FOV. Icon stays CENTERED inside that patch with surrounding
compass arrows for supported directions. Unknown gets no arrow. Optical patch size in browser is
illustrative until glasses are calibrated. OLED is monochrome; browser accents are illustrative.
One visible OLED cue; competing events queue. No multi-alert redesign requested.
Pause hides urgent alerts too (labeled); DND admits Urgent. Gestures are explicitly deferred after
Emma's real thumbs-up trial was finicky. Keep manual Dismiss; don't spend time retuning gestures now.
The glasses have NO camera. The simulator's camera is optional demo POV only.

Validation at freeze: 43 Python tests; 18 frontend tests; 18 shared scenarios; 127 exact renderer
fixtures; production build; latest native-probe push CI green at time checked. 10k cross-language
parity after policy changes; prior 150k stress report is simulated time, not physical uptime.
Real glasses optics/orientation/display, final mic capture, room accuracy and end-to-end latency
still need physical validation. See docs/simulator-freeze.md and docs/integration-revisit.md.

## User communication rules

- Always finish with TLDR: done, or a concrete question/options stating what is needed.
- Don't suggest a next action and idle: start it or ask the required clarification.
- Keep updates concise and frequent; distinguish built/tested/simulated/physically verified.
- Commit/push coherent checkpoints frequently. Don't merge or force-push teammates' branches blindly.
