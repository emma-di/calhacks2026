# Leo's spatial branch review — October 24

Reviewed `origin/lragogna/audio-triangulation` at **ff840bc** (also includes f8ab296).
Tested an isolated archive; it is not merged into the companion branch. No microphone capture started.

## Verified

- All **17 spatial tests pass** on synthetic microphone signals.
- GCC-PHAT delay estimation, bearing candidates and two-mic front/back ambiguity are implemented.
- Front/back resolution uses a sequence of lateral estimates plus **measured head yaw**. The walking
  demonstration uses a simulated yaw trace, not a sensor on our current hardware.
- Standalone map simulator runs on `http://127.0.0.1:8878/` in this review session with `--no-audio`.
  It uses synthetic signals and positions, not live spatial measurements. To reproduce on Leo's branch:

```sh
.venv/bin/python -m spatial.server --port 8878 --no-audio
```

Port 8878 avoids our active alert receiver on 8766. Do not run the simulator's default 8766 command
on top of that receiver. Keeping --no-audio avoids assigning random simulated positions to real
classification events, which could be mistaken for measured direction.

## Findings before live integration

1. **Silence crashes the localizer.** `localize(np.zeros((2,4800)),48000,mics,ids)` reaches an empty
   peak list and raises IndexError. It should return no confident bearing / unknown, not index peaks[0].
2. **Validate capture shape.** One channel passed with two-mic geometry raises IndexError. Require
   synchronized matching channel counts, finite samples, valid sample rate and nonempty buffers.
3. **No live capture adapter yet.** The simulator synthesizes microphone signals per source. Real
   mixtures need measured-channel capture, input buffering, window association with classification,
   mic geometry and confidence gating; known per-source simulation is easier than competing sounds.
4. **Two mics retain front/back ambiguity without measured motion.** No IMU is in the confirmed
   hardware list. Walking alone is not a measurement. A phone orientation trace only describes the
   phone unless it is mounted to track the wearer's head.
5. **No alert adapter yet.** Preserve source=simulation for any demonstration. Send direction_degrees
   and direction_confidence to the shared receiver only after mapping conventions and confidence;
   unresolved/weak/invalid input stays null. Never infer distance from the simulator's placed sources.

The simulator's passing cases are feasibility evidence under its assumptions, not final-room accuracy.
Its documented omissions include room echoes, head shadow, mic mismatch and clock drift.

## Can the iPhone provide two microphone signals?

Current Mac device enumeration: **Emma Microphone has max_input_channels=1**. This Continuity route
therefore cannot feed two independent simultaneous channels into Leo's TDOA code. Camera selection
and choosing two copies of that mono signal cannot add spatial information. Combining the phone mic
with the Mac mic is also not a verified synchronized array.

Apple does support built-in stereo capture on supported iOS devices through AVAudioSession, and
AVCaptureMultiCamSession can expose front/back audio directions. That requires a native iOS capture
path and a physical-device capability check; it is not exposed by our current Continuity input.
Stereo/directional outputs may be processed, so we must verify sample alignment, effective geometry
and direction accuracy before treating them as the two raw glasses microphones. Native capture is a
possible experiment, not a verified drop-in replacement.

Sources:
- [Apple stereo capture sample](https://developer.apple.com/documentation/avfaudio/capturing-stereo-audio-from-built-in-microphones)
- [Apple simultaneous microphone-direction ports](https://developer.apple.com/documentation/avfoundation/avcaptureinput/port/sourcedeviceposition)

For now: spatial simulator is runnable; real spatial validation awaits synchronized inputs. Phone
mono classification can still be tested separately once Emma authorizes the deferred live test.
