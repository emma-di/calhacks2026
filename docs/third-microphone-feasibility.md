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
