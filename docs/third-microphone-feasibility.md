# Phone as third microphone: experimental, not a drop-in input

The user proposed placing a connected phone in front of the glasses to form a noncollinear array.
In principle, three microphones with known fixed positions and synchronized audio can resolve
more horizontal direction information than the current two-mic line. This does not establish
unique full 3D position, distance, or reliable performance in an echoing room.

The phone and Pi have independent sampling clocks, capture offsets, processing and transport
delays. USB/Wi-Fi connectivity and matching 48kHz settings do not by themselves synchronize them.
At 13cm spacing, the maximum physical acoustic delay is only about 0.38ms (~18 samples at 48kHz).
A 1ms unknown recording offset corresponds to about 34cm of apparent acoustic path difference.
Never use network arrival time as acoustic arrival time.

Before trying actual three-channel TDOA:

1. Capture raw PCM on the native phone path (not FOA coefficients treated as a raw third mic).
2. Fix and measure phone position relative to the glasses; wearing/turning the head while holding
   a phone in place changes that geometry. "Somewhere in front" is insufficient.
3. Use a sound from a known location to estimate clock offset separately from acoustic delay;
   repeat later to measure drift and compensate sample-rate mismatch. A single unknown-position
   clap confounds clock offset with the propagation delay we are trying to estimate.
4. Preserve sample counters/timestamps and source identity; handle dropouts and asynchronous
   resampling explicitly. Run known-angle trials before supplying real alert directions.

The existing native phone FOA probe is a separate candidate direction sensor; see
docs/phone-direction-research.md. Its output is phone-relative and was not validated as a raw,
sample-synchronized third channel for the Pi. Do not reconnect its automatic event matcher while
the active receiver predates the Pi-source guard.

For the current demo, continue validating Pi left/right first. A third microphone captured on the
same multichannel clock would simplify synchronization, but needs suitable capture hardware; the
current shared I²S stereo bus offers two slots and is not itself a three-channel capture interface.
No third-phone implementation is running and no front/back claim should be made.

Primary references:
- https://arxiv.org/abs/2110.12820 (sampling time/rate offsets in distributed acoustic nodes)
- https://arxiv.org/abs/1610.02392 (microphone geometry and acoustic calibration)
- https://developer.apple.com/library/archive/documentation/Audio/Conceptual/AudioSessionProgrammingGuide/OptimizingForDeviceHardware/OptimizingForDeviceHardware.html

## Addendum — John's moving front-pocket phone experiment (October 25)

**A loose front-pocket phone is not currently a reliable front/back upgrade.** It remains worth a
separate feasibility experiment. Two different approaches have different requirements:

| Approach | What it needs | What a moving pocket changes |
| --- | --- | --- |
| Phone as a third TDOA channel beside the two Pi microphones | Raw, sample-aligned audio; estimated offset/drift; phone-to-head microphone geometry | The microphone position changes with walking, phone movement and independent head turns. Static calibration becomes invalid. USB does not solve clock alignment. |
| Phone as its own spatial direction sensor | Supported native FOA capture, valid local direction, time/source association, coordinate-frame mapping | Phone rotation changes its bearing axes; its pose does not reveal the direction the head is facing. Covered microphones and clothing noise can invalidate the measurement. |

Apple's [spatial capture explanation](https://developer.apple.com/videos/play/wwdc2025/251/)
describes FOA as transformed sound-field components, not separately exposed physical microphone
channels. This means the existing FOA probe is closer to the **second** approach. It is not already
a synchronized third Pi microphone. Asynchronous array research treats sensor geometry, relative
orientation, initial clock offset and sampling-rate difference as separate unknowns; solving them
jointly is a research/engineering task, not automatic USB behavior.
([Primary paper](https://arxiv.org/abs/2405.19813).)

**Current repo limitation:** `native/PhoneSpatialProbe/FOADirection.swift` estimates a horizontal
phone-frame bearing from W/X/Y and returns no full 3D direction vector. `ProbeController.swift`
subtracts a saved scalar “Set front” angle; there is no Core Motion pose stream or head-pose input.
Rotating or tilting a loose pocket phone invalidates this one-time calibration. A future pose-aware
version needs the full acoustic vector before projection and a sample-associated rotation into the
head frame. Phone motion alone cannot supply independent head orientation.

[Core Motion](https://developer.apple.com/documentation/coremotion/getting-processed-device-motion-data)
can report the **device's** attitude relative to a selected reference frame. It does not establish
the phone's current translation relative to the glasses or measure the wearer's independent head
turn. Even an Earth-referenced phone bearing would need head orientation to become a head-relative
arrow. For nearby sources, waist-versus-head position can also change the relevant bearing; this is
an engineering inference, not a tested property of our prototype.

Pocket fabric, body shadowing, rubbing and changes in microphone exposure are additional acoustic
risks to measure, rather than treating every coherent reading as valid direction. Apple advises
keeping [iPhone microphone openings clear](https://support.apple.com/en-au/101600); that guidance
does not validate a pocket placement for spatial inference.

### John's first deliverable and acceptance checks

Deliver a short **offline feasibility report**, not a live-arrow integration: choose one approach,
describe exactly which clock/geometry/frame assumptions it uses, and compare a fixed exposed-phone
baseline with the actual front-pocket placement. Keep all uncertain results out of real alerts.

1. **Separate the paths.** For TDOA, export raw PCM with sample counters/timestamps and measure
   clock offset plus drift against the Pi using known-position sounds. For standalone FOA, inspect
   supported capture/channel format and report phone-relative direction; do not name it head-relative
   until a measured frame transform exists. Reuse [the probe/handoff](phone-spatial-handoff.md).
2. **Fixed baseline:** at least ten independent airborne sounds from front and ten from behind,
   with wearer/head/phone held still. Record source angles, direction, abstentions and wrong-side
   counts. Include quiet gaps; do not use table taps coupled mechanically into the phone.
3. **Pocket challenge:** repeat with phone screen inward/outward, upside down, tilted and loose;
   then head turns while torso stays still, torso turns, and walking. Keep source positions known.
   Report each condition separately; a single “Set front” success is insufficient.
4. **Wrong-source and failure checks:** a fan/voice/music overlapping the target sound, rubbing
   clothing, blocked openings, silence, phone stop/lock/background, transport gaps and stale readings.
   Require explicit unknown/abstain instead of a retained or guessed front/back arrow.
5. **Decide from evidence:** publish front/back confusion counts, valid/abstained fractions,
   clock residuals/drift if using TDOA, and timing/source-match errors. If pose/geometry or sound
   association cannot be established, stop at phone-relative diagnostics. Prefer a fixed exposed
   mount or a synchronized third hardware channel for the next controlled experiment.

No pocket, pose-compensation or three-channel experiment was run for this addendum. The current
demo can retain validated Pi left/right and unknown front/back while John tests this separately.
