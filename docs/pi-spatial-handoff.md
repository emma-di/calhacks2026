# Pi audio → recognition → left/right: resume plan

Updated October 25, 2026. **Plan, not a completed spatial implementation.**

## Product decision

Emma wants the **two Pi microphones as primary input**, Mac microphone only as an explicitly
selected fallback. Emit **left, right, or unknown**. Do not infer front/back, distance, or precise
azimuth. The icon stays centered in the right-eye display; reuse the existing left/right triangles.
An arrow means lateral evidence, not proof that the source is exactly 90 degrees from the face.
Weak, equal, conflicting or unavailable evidence gives no arrow and never suppresses the sound alert.

## Proven / not proven

- Original Pi Zero W, two INMP441s sharing I²S clocks/data; opposite L/R selects.
- ALSA `hw:CARD=AwareINMP441,DEV=0`, 48,000 Hz, S32_LE, two interleaved channels.
- Near-each-mic trial showed independent responses: channel 0 advantage 14.82 dB and channel 1
  advantage 21.65 dB. See `reports/pi-stereo-mic-check.json`.
- Physical channel-to-left/right mounting is **not confirmed**. Mic separation is not measured.
- `audio/pi_levels.py` supplies live numeric meters to the site through `/pi-audio/levels`.
- **Recognition still uses the Mac mic at this checkpoint.** Merely showing Pi meters does not
  switch inference. Do not report Pi sound-to-alert integration or real direction as completed.
- Existing `audio/spatial.py` is a separate phone-FOA experiment. Do not send uncalibrated Pi
  readings into that buffer or attach Pi direction to independently captured Mac audio.

## Resume order (small commits)

1. **Switch recognition to the Pi capture, preserve meters.** One SSH/ALSA owner only. Reuse
   `CaptureBridge` in `audio/pi_levels.py`; fan out each complete stereo PCM block in memory to
   meters, localization and one bounded recognition queue. Do not start another `arecord` client.
   Add an explicit Pi input option to `audio/cli.py` and retain `mic --device` as manual fallback.
   Preserve raw stereo for localization. Downmix safely to mono and use a stateful antialiasing
   resampler from 48 kHz to 16 kHz for existing environmental/name/custom workers. Feed each
   fresh sample once; do not downsample by dropping samples without a low-pass filter.
   Reset recognition/resampler/localization buffers on reconnect, queue loss or capture gap.
   Never concatenate samples across an outage. Keep queues bounded; discard stale backlog.
   Surface the actual selected input in diagnostics. No automatic switch to Mac on failure.
2. **Offline left/right estimator.** Add a separate `audio/pi_spatial.py` with a pure estimator
   and focused tests; do not replace the phone API. Start with calibrated interchannel RMS
   difference, requiring clear evidence across multiple short frames. Initial *experimental*
   values: >=6 dB dominance for >=300 ms, above measured room noise; these need room tuning.
   Correct measured channel gain mismatch; reject silence, clipping, dead channel, nonfinite,
   malformed input, rapid side changes and stale frames. Quiet/equal levels immediately produce
   unknown; use hysteresis only to prevent chatter, never retain an arrow through disconnect.
   Level differences alone are not reliable at distance or with uneven microphone gains.
3. **Use Leo's GCC-PHAT where it improves real evidence.** Inspect
   `origin/lragogna/audio-triangulation` and `docs/leo-spatial-review.md` first. Reuse the delay
   core only with shape/silence guards. Measure mic spacing and constrain lag by spacing/343 m/s.
   Check lag sign with known synthetic delays and real known-side sound. Require a distinct
   plausible correlation peak; echoes, periodic tones, contradictory delay/level signs or multiple
   sources can be ambiguous. Leave unknown rather than force a side. No yaw/front/back logic.
4. **Calibration, diagnostic output first.** Confirm channel mapping by making a sound near a
   physically identified LEFT mic, then RIGHT. Capture centered reference for gain/noise offset.
   Mount microphones as worn before testing directions at normal listening distance; a close-up
   response is not direction accuracy. Persist only calibration numbers/geometry locally, with
   validity/version and explicit reset. Missing calibration disables arrows, not recognition.
5. **Attach evidence from the same recognition window.** Carry capture/session ID, sample index
   and interval with buffered audio. Aggregate localization over the exact classified window;
   do not grab the latest unrelated meter reading after inference. Send existing fields
   `direction_degrees=-90` (left), `90` (right), paired `direction_confidence`; otherwise both null.
   Use a conservative evidence score compatible with renderer gating, not an accuracy probability.
   Record provenance such as `direction_source=pi_stereo`; preserve `source=microphone` contract.
   Prevent the legacy phone matcher from filling unknown Pi events without explicit opt-in.
   Different simultaneous sounds cannot reliably inherit one global dominant-source direction;
   with competing/uncertain sources use unknown. Never assign random simulator bearings.
6. **Physical acceptance before demo arrows enabled.** Run the matrix below, then enable Pi
   arrows explicitly. Keep mock directions labeled simulated. Test browser and OLED with the
   same canonical receiver state. Only capture/display dependencies go on Pi; inference stays Mac.

## Required checks

| Check | Pass condition |
| --- | --- |
| Stereo/resampling unit tests | Correct independent channels, 48→16k length, alias rejection, chunk continuity |
| Left/right synthetic fixtures | Both signs, swapped mapping, gain offset, equal energy, silence, clipping, bad shape, NaN, delay bounds |
| Lifecycle | Reconnect/gaps/overflow clear buffers and direction; no stale arrow, no false alarm auto-clear |
| Same-source integration | Pi PCM causes actual model event and matching browser cue; Mac worker stopped; no duplicate name feed |
| Known-side room trials | Repeated left/right at multiple distances; log right/wrong/unknown counts and latency separately |
| Ambiguous trials | Front, back, centered alarm, background noise, competing sounds produce no forced side |
| Settings/display | Selected Baby crying/horn and Ignore still work; manual dismiss/priority/quiet alarm clearing unchanged |
| Failure/fallback | Pi disconnect is visible; no stale alerts; Mac input requires explicit selection and shows no Pi arrow |

Do not claim measured accuracy from synthetic tests. Report wrong-side rate and unknown rate;
fewer arrows is preferable to a confident wrong side. No promise of zero wrong-side results.

## Commands / running services

- Repo branch `codex/browser-mirror`, PR #2. Do not merge or force-push. Leave `.claude/` untouched.
- Site: `http://127.0.0.1:5174/` → Live. Pi meters are below the preview.
- Receiver: `http://127.0.0.1:8766/`. **Do not restart unnecessarily: Claude API key is memory-only.**
- Meter bridge: `.venv/bin/python -m audio.pi_levels --pi pi@glasses-pi.local --port 8768`.
  Already running at checkpoint; inspect before starting another. Stop gracefully with Ctrl+C.
- Pi access: `ssh pi@glasses-pi.local`; requires same reachable Wi-Fi/hotspot and existing SSH key.
  No password or private key belongs in docs, commands committed to Git, or chat handoffs.
- Check numerical feed: `curl http://127.0.0.1:8768/levels`; `connected=true` plus advancing
  sequence is required. SSH reachability alone does not prove capture resumed.
- Existing Mac fallback command: `.venv/bin/python -m audio.cli mic --device <enumerated-index>
  --endpoint http://127.0.0.1:8766/events`. Enumerate with `audio.cli devices` before using it.
- Private cached mic WAVs (if present) are in `.cache/pi-audio-tests/`; do not commit/upload them.
- Meter tests: `.venv/bin/python -m unittest tests.test_pi_levels -v`;
  `npm test --prefix frontend`; `npm run build --prefix frontend`.

Next agent: implement step 1 before enabling direction. Emma returned to the Pi hotspot after a
Wi-Fi change; SSH resolves again, but the meter bridge last reported a disconnected capture and
must recover/be checked before claiming live recognition.
