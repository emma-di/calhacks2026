# John's audio branch review — October 24

Reviewed `origin/johnaou/custom-sounds` at **87aff0d**, including **9146609**.
Fetched and tested an isolated archive; the active receiver/checkout were not replaced or merged.
No microphone was started and no accuracy benchmark was rerun for this review.

## What arrived

- Frozen Zipformer embeddings plus per-sound lightweight classifiers.
- Local recordings/background bank, training/testing and enable/disable/delete APIs.
- Live custom-head reload in the microphone/file CLI.
- `/teach` reference recording page and `docs/custom-sounds.md` / `docs/handoff-live-site.md`.
- Event extension: `type: custom`, required `custom_sound_id`, user label and chosen producer tier.

Verification in an isolated branch copy with the existing Python environment:
**8 custom model/storage tests and 6 custom HTTP tests passed.** These use synthetic/fake embeddings;
they do not validate noisy-room accuracy or the final glasses microphones. The branch's ESC-50
results are John's reported offline measurements, not freshly verified live performance.

## Integration work before the polished site can use it

| Boundary | Current mismatch | Required integration |
| --- | --- | --- |
| Server | John's branch started from the old monitor server | Port custom routes into our current server; preserve /profile, /display, /controls, scoped dismiss, health, persistence and queue |
| Event validator | Our server and TS parser only accept known built-in types | Add bounded custom_sound_id support on both sides; preserve name/gesture and nullable-score support |
| Sound identity | Current repeats/acks use event.type | Use a stable type + custom_sound_id identity for custom sounds, so acknowledging one doesn't silence every custom sound |
| Priority settings | Current overrides use fixed event type keys | Agree custom per-ID priority/disable storage and inheritance; preserve explicit Ignore (0) |
| OLED | Policy icon map lacks custom, so there is no valid custom presentation | Choose a generic custom-sound icon or explicit user mapping; preserve urgency labels and exact renderer parity |
| Onboarding | Current custom labels are pending metadata only | Link a request to a trained backend ID after successful recording/train/test; show readiness and errors honestly |
| Capture/transport | Reference teach page records WAV; phone viewer is read-only | Keep teaching on the local companion with explicit microphone permission; don't open write/recording routes through the phone viewer |
| Dependencies | Adds onnx, onnxruntime, kaldi-native-fbank | Validate installation/model cache on the processing Mac and preserve a built-in-only fallback |

The handoff's “no queue/preferences” and old bare /state description refer to its branch baseline;
our companion already has those features. The current authority for priority is docs/alert-engine.md.
Do **not** replace our server with the branch's older implementation to integrate custom sounds.

Pending acceptance: port/rebase, tests for two independent custom sounds and their overrides,
custom event → receiver → companion → 128×64 OLED, then actual room/microphone trial.
Speech/name recognition remains separate and is not part of this branch.
