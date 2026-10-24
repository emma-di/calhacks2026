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
