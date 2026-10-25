# Experimental iPhone spatial microphone probe

Purpose: determine whether John's newer iPhone provides **real four-channel first-order Ambisonics
(FOA)** and whether a coarse dominant-sound bearing survives the room. This is a feasibility app,
not a completed localization integration or an alert source.

## What is ready

- Native capture code compiles successfully against Xcode 27.1's iPhoneOS SDK (deployment target iOS 26).
- `FOADirection.swift` passes **80 synthetic checks** across bearings and invalid/ambiguous input.
- Runtime capability check uses `isMultichannelAudioModeSupported(.firstOrderAmbisonics)`.
- Buffers must report four-channel ACN/SN3D float PCM; planar and interleaved buffers are supported.
- No capture on launch. User taps for an eight-second test; Stop/backgrounding ends capture.
- No raw audio recording or network upload. No changes to the companion, tiers or OLED from this probe.
- Physical capability, orientation/sign and noisy-room direction accuracy are **not yet verified**.

## Prepare / build

```sh
.venv/bin/python scripts/prepare_iphone_spatial_probe.py
```

This downloads Apple's official licensed project shell to `.cache/iphone-spatial-probe`, preserves its
license, and overlays this folder's probe sources. It refuses to overwrite an existing generated
project, because signing changes must remain local. Source of truth is this folder; do not commit
provisioning profiles, signing identities, generated projects, Apple Accounts or recordings.

Open `.cache/iphone-spatial-probe/SpatialAudioDemo.xcodeproj` in Xcode. Select a development Team,
connect/trust the target iPhone, and choose it as Run Destination. Device signing requires the account
owner's authorization. The user must handle any iPhone Developer Mode/trust prompts themselves.
The default project/sample display name is still SpatialAudioDemo; its UI says Aware spatial probe.

Unsigned compile check (no device / microphone):

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild \
  -project .cache/iphone-spatial-probe/SpatialAudioDemo.xcodeproj \
  -scheme SpatialAudioDemo -sdk iphoneos -destination 'generic/platform=iOS' \
  -derivedDataPath .cache/iphone-spatial-build CODE_SIGNING_ALLOWED=NO build
```

Math-only checks:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcrun swiftc \
  -module-cache-path /tmp/aware-swift-modules \
  native/PhoneSpatialProbe/FOADirection.swift \
  native/PhoneSpatialProbe/FOADirectionChecks.swift -o /tmp/aware-foa-checks
/tmp/aware-foa-checks
```

## Physical test

Use John's phone for this app and Emma's phone for the already-working Continuity Camera POV.
Do not expect the same phone to run a native capture app while locked as a Continuity camera.
Disconnect headphones/external microphones; use the built-in microphone array.

1. Keep the phone stationary, in a noted orientation. Tap the eight-second test and grant mic permission.
2. First confirm the status says **Verified FOA · 4 channels**. Unsupported mode or unexpected format
   means the probe stops short of making a direction claim. Note sample rate and format errors.
3. Place one broadband source (knock/clap) in front, right, behind, left, at roughly the same distance.
   Keep phone orientation fixed; repeat trials. Record which encoder bearing corresponds to each side.
4. Test quiet input: it should show unknown, not hold a previous bearing. Test competing sounds and
   room noise; count wrong/unknown estimates. Coherence is a heuristic, not calibrated confidence.
5. Repeat using a bell/siren. Tonal sounds, echoes and multiple sources can give misleading vectors.

Coordinates are **encoder-frame**, not wearer-frame. ACN channel order is W,Y,Z,X; the experiment
uses pressure/dipole covariance to obtain a dominant acoustic vector. The code maps ACN Y-left to
right-positive bearings. Physical encoder orientation and possible propagation/sign conventions still
require the cardinal test above. Phone orientation is not the wearer's head unless mounted/aligned.

## What remains before alerts

- Measure accuracy and timing on the physical device; calibrate orientation/sign.
- Stream timestamped FOA or estimates to the processing Mac; add stale/disconnect behavior.
- Feed recognition from the same captured sound/time window; do not attach the loudest source's
  direction to an unrelated classified event. Multiple simultaneous sources remain a difficult case.
- Map only supported, reliable estimates to the existing `direction_degrees` / `direction_confidence`
  event fields. Unknown stays null. The coherence metric must not be promoted directly into probability.
- Leo's GCC-PHAT expects physical microphone signals/geometry. FOA is a processed spatial encoding,
  so it uses this separate estimator; it is not four raw microphones for his TDOA code.

## Why this path

Continuity Camera on Emma's Mac exposes the iPhone microphone as **one channel**. Native APIs can
expose more information. Older supported phones can record stereo; Apple's FOA sample targets
spatial-capable devices such as iPhone 16 Pro or later. We target John's iPhone 18 Pro, but the runtime
query is authoritative. Apple's SoundAnalysis classification result does not provide a bearing.

References:
- [Live FOA output layout](https://developer.apple.com/documentation/avfoundation/avcaptureaudiodataoutput/spatialaudiochannellayouttag)
- [Runtime mode capability](https://developer.apple.com/documentation/avfoundation/avcapturedeviceinput/ismultichannelaudiomodesupported(_:))
- [Apple sample](https://developer.apple.com/documentation/avfoundation/capturing-spatial-audio-in-your-ios-app)
- [Apple stereo capture](https://developer.apple.com/documentation/avfaudio/capturing-stereo-audio-from-built-in-microphones)
- [Apple multi-beam microphone explanation](https://developer.apple.com/videos/play/wwdc2019/249/)
- [Recording support by generation](https://support.apple.com/guide/iphone/change-sound-recording-options-iph31c1ca6c7/ios)
