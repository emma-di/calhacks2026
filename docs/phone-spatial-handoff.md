# Phone spatial audio — handoff to John (October 24)

Emma is moving to the display; this is everything needed to continue the iPhone direction work.
Findings and history: [phone-direction-research.md](phone-direction-research.md). Probe source:
`native/PhoneSpatialProbe/`.

## What works (verified on John's iPhone 18 Pro)

- **Real spatial audio:** the probe gets "Verified FOA · 4 channels · 48000 Hz".
- **Direction streaming to the Mac over the USB cable** (~5 readings/s). Venue Wi-Fi blocks phone→Mac
  traffic, so don't rely on Wi-Fi.
- **End to end:** sounds recognized by the Mac's mic (knocks, doorbells) arrive with the phone's
  direction attached and cues move to that side.

## Run it

1. Phone upright in **portrait**, screen toward you, plugged into the Mac. Front = where the back camera
   points. Open **SpatialAudioDemo**, tap **Start listening**, clap in front, tap **Set front**.
   Listening stops after 3 minutes (tap Start again).
2. Mac, from the repo root:
   ```sh
   .venv/bin/python -m audio.server --port 8766
   .venv/bin/python scripts/phone_usb_bridge.py --receiver http://127.0.0.1:8766
   .venv/bin/python -m audio.cli mic --device 1 --endpoint http://127.0.0.1:8766/events
   ```
   (`audio.cli devices` lists microphones.) Companion: `AWARE_RECEIVER=http://127.0.0.1:8766 npm run dev
   --prefix frontend -- --port 5174`, Receiver mode.
3. Check the link: `curl -s localhost:8766/health` → `spatial.connected: true`.

## Rebuilding / reinstalling the app

```sh
.venv/bin/python scripts/prepare_iphone_spatial_probe.py --sync   # copies sources, keeps signing
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project .cache/iphone-spatial-probe/SpatialAudioDemo.xcodeproj -scheme SpatialAudioDemo \
  -sdk iphoneos -destination 'id=<phone UDID>' -derivedDataPath .cache/iphone-spatial-signed \
  -allowProvisioningUpdates build
xcrun devicectl device install app --device <UDID> .cache/iphone-spatial-signed/Build/Products/Debug-iphoneos/SpatialAudioDemo.app
```

Signed with Emma's free Personal Team. **After every reinstall the phone must re-verify the developer**
(Settings → General → VPN & Device Management → Verify/Trust, phone online) or iOS refuses to launch.
Math checks: see `native/PhoneSpatialProbe/README.md` (81 synthetic cases pass).

## Open problems, in priority order

1. **Calibration.** The phone's angles are mirrored and uneven: right sounds read negative, left
   positive, the left side weaker, and behind lands around 160°. The receiver maps phone bearings
   through four learned example points: `POST /spatial/calibrate {"examples": {"front": [..], "right":
   [..], "behind": [..], "left": [..]}}`. **Calibration is currently empty** (raw bearings are used).
   Emma's run blended the sides together; redo it with clear gaps, or build the planned guided capture:
   record 5 s per side, keep the loudest readings, then apply.
2. **Background sound.** In the last run the phone locked onto a steady quieter source at about −15° for
   40+ s (fan, music, a looping doorbell or voices). Readings pass the 0.60 coherence bar, so any sound
   recognized meanwhile gets that direction. Consider a level/onset gate (only readings well above the
   recent noise floor) before matching.
3. **Matching by time.** Direction comes from the phone, recognition from the Mac's mic, matched by
   receive time (3 s window). Better: make the phone the microphone too (its W channel is mono audio)
   so one device hears, recognizes and locates the same sound.
4. **Table knocks** couple vibration into the phone and read weak/compressed; test with airborne sounds.
5. **3-minute listening cap** in `ProbeController.start()` will cut a demo short; raise it before demos.

Logged readings for analysis (numbers only): `.cache/spatial-readings.jsonl`.
