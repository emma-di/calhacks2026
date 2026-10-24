# Integration handoff

## First checkpoint

Recorded knock → model → JSON → visible laptop alert has been exercised.
The live-room recognition test and physical display handoff remain separate checkpoints.

## Provisional v1 event

```json
{
  "schema_version": 1,
  "event_id": "unique-uuid",
  "type": "knock",
  "label": "Door knock",
  "confidence": 0.58,
  "source": "microphone",
  "priority_tier": 2,
  "timestamp_ms": 1792788699751,
  "direction_degrees": null,
  "direction_confidence": null,
  "distance_meters": null,
  "proximity": "unknown",
  "inference_ms": 2.9
}
```

`confidence` is an uncalibrated model score, not a measured probability of correctness.
`inference_ms` excludes capture/windowing, transport, and display time.
Microphone timestamps approximate block completion; replay timestamps use the replay start
plus the audio window completion offset. They are not hardware-synchronized spatial timestamps.
Sources distinguish `mock`, `replay`, `simulation`, and `microphone`. The contract is proposed, not yet team-approved.
Recognition thresholds and label groups live in `audio/policy-<model>.json`.
Current notification tier defaults are in `audio/events.py`; user preference overrides belong in the priority stage.
The optional `model` field identifies the classifier. Generic `bell` means Bell / chime;
the `bicycle_bell` subtype is disabled in the default recognition policy.

## Yameen's handoff

1. Confirm audio access: USB audio device, streamed PCM, or a headset SDK input.
2. Supply native sample rate, channel count, channel order, and whether channels are synchronized.
3. Confirm display transport and pixel dimensions; render a fake Bicycle bell event first.

If the hardware appears as an OS microphone, select its device index in the existing CLI.
If it streams PCM, implement a capture adapter feeding normalized mono windows to the selected model's `predict` method.
Keep the original synchronized channels separately for future localization; never infer direction from mono.
For Quest 3, treat audio capture and display as new adapters until actual device APIs are verified.
This repo does not claim Quest microphone access or headset display integration already works.

## Next build order

The list below covers audio/hardware integration. Emma's parallel frontend-first work follows the
[browser mirror → backend plan](ui-ux-backend-plan.md); track both paths in the [master TODO](../TODO.md).

1. Five live trials of knock, bicycle bell, and barking, plus quiet/background conversation negatives.
   Record hits, misses, false alerts, and end-to-end delay. Tune per-class thresholds from those results.
2. Add a physical display adapter consuming the same active alert state.
3. Add local speech recognition in a separate worker and match typed names/aliases at word boundaries.
   Evaluate uncommon names and similar-sounding negatives before considering fuzzy matching.
   The [implementation plan and onboarding contract](name-detection-plan.md) are now prepared.
4. Add user preferences, proper queuing, interruption/resume rules, and recognition-worker heartbeat.
5. Only after synchronized capture is proven, prototype GCC-PHAT separately.

## Model choice

Zipformer Small INT8 is the default after the offline comparison; it uses two seconds of context
with one-second hops. YAMNet remains a faster, shorter-context baseline. The benchmark compares
the complete configured pipelines, so their different context windows should be considered with the results.
Neither model transcribes names. Whisper-family speech recognition is a candidate for the next stage,
not an installed or benchmarked dependency. No custom training is needed for preference mappings.

Sources: [TensorFlow YAMNet tutorial](https://www.tensorflow.org/hub/tutorials/yamnet),
[model class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv),
[official Zipformer audio-tagging models](https://k2-fsa.github.io/sherpa/onnx/audio-tagging/pretrained_models.html).
