# Phone direction feasibility — October 24

The earlier **mono Continuity connection is a transport limit, not proof that phone direction is
impossible**. Native iOS capture is the promising experiment. Full setup/test criteria:
[native probe](../native/PhoneSpatialProbe/README.md).

| Path | Evidence | Decision |
| --- | --- | --- |
| Current Continuity mic | Mac lists one input channel | Use for classification; cannot recover stereo TDOA from it |
| iPhone 15 Pro stereo | Apple documents stereo capture on older supported iPhones | Possible native/recorded stereo experiment; processing/geometry require validation |
| Newer iPhone FOA | Apple exposes live four-channel ACN/SN3D buffers with a runtime support query | Native probe prepared and compiled; target John's phone for real test |
| Front/back microphone ports | Apple documents simultaneous directional beam outputs | Not independent raw mics; do not blindly use a glasses mic-spacing model |
| Apple SoundAnalysis | Results contain classifications/time ranges | No documented general environmental-sound bearing result found in reviewed APIs |
| Multiple unsynchronized devices | Two separate devices are not a verified sample-synchronous array | Do not claim measured TDOA from Mac mic + phone mic |

FOA provides pressure plus directional components; experimental covariance gives a coarse dominant
vector. It still needs calibration and room tests. Unlike two collinear mics, the encoded directional
components can in principle carry front/back information without head rotation. That is an inference
from the encoding, not a measured result on our phone. No distance claim.

Xcode 27.1 was downloaded from Apple's authenticated site, installed in /Applications and used to
compile the iPhone app. The older configured Downloads/Xcode path was missing; no matching Xcode
was found via normal app locations/Spotlight or Finder's Trash search. System components were
installed after Emma handled the Mac administrator prompt. Personal Team signing was explicitly
authorized by Emma; all account/device identifiers and generated project state stay local.

John's observations branch (`johnaou/observations`, 8a440e1) was also reviewed: **six observation
build/validation/HTTP/nonblocking-publisher tests passed** in isolation. It provides per-window top-k
scores, rule/custom decisions, levels and emitted events, without raw audio. It is not merged into
our current backend yet; preserve the newer queue/preferences/display APIs when porting it. John's
speech work remains separate. No phone microphone recognition test has been started during this work.

Sources and precise API links are in the native probe README. Physical probe status is updated in
TEAM-NOTES.md / WORK-STATUS.md; compiled is not the same as confirmed live localization.


Recorded replay follow-through: ran cached `samples/dog.wav` through John's observations CLI and
an isolated ephemeral receiver using the real Zipformer model. Exit 0; **five observations and one
dog_bark event** delivered with source=replay. Custom heads were explicitly disabled because the
onnx/onnxruntime/kaldi-native-fbank dependencies are not installed in this environment. This verifies
the built-in recognition + observations delivery path, not the custom-trained heads or speech worker.

## Physical results on John's iPhone 18 Pro — October 24 (Claude session)

- **FOA verified on device:** "Verified FOA · 4 channels · 48000 Hz". First coherence reading in a
  normal room was 0.30 (diffuse), correctly reported as direction unknown.
- **Pose matters.** Lying flat/face down mirrored left/right; upright portrait first appeared to give
  only front/behind. Working setup: phone upright in portrait, screen toward the user, front = where
  the back camera points ("Set front" from a clap there).
- **Knocks needed a shorter window.** Over 250 ms a knock was diluted by room noise (coherence
  0.35–0.52). Estimating from the loudest 40 ms block lifted real knocks to 0.60–1.0.
- **Portrait compresses and mirrors the lateral axis:** knocks at the right read about −29°, at the
  left about +31°. The receiver now applies a right reference (`POST /spatial/calibrate
  {"right_degrees": -29}`, saved in `.cache/spatial-calibration.json`) mapping right to +90.
- After correction, 4 of 8 table knocks landed cleanly on right/left with the correct side; the rest
  leaned the correct way but stayed in the front zone. Likely cause: knocking on the same table the
  phone stands on couples vibration into the phone body. Retest with airborne knocks (door, wall,
  book held at the side) before claiming accuracy.
- **Transport:** venue Wi-Fi isolates clients and USB hotspot was flaky, so readings go over the
  cable: probe streams JSON lines on TCP 5178, `scripts/phone_usb_bridge.py` forwards through macOS
  usbmuxd to the receiver's `/spatial`. `scripts/phone_spatial_relay.py` (pairing code) remains for
  networks that allow device-to-device traffic.
- The receiver attaches the most coherent calibrated phone reading from the 3 s before a recognized
  sound (time match only). Test sounds never receive phone directions.
- Each reinstall of the personal-team build required re-verifying the developer on the phone
  (Settings → General → VPN & Device Management), with the phone online.
