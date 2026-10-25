# Pi left/right spatial detection — October 25

## Implemented

Emma confirmed physical channel 0=LEFT and 1=RIGHT. Spacing is approximately 11–13cm; the
detector uses 13cm as its upper bound. Mac `audio/pi_spatial.py` analyzes the same 48kHz stereo
blocks used by recognition. Pi still runs capture/display only.

- GCC-PHAT checks arrival-time difference within the physical lag bound. At least 2 samples of
  delay and a distinct peak (ratio >=1.6 outside a ±2-sample neighbourhood) are required.
- A small volume difference does not prevent direction if timing is clear. Level evidence can
  supply direction at >=2.5dB; channel correlation must be >=.2, and >=.55 to use timing.
- Both channels must be above -85dBFS, with louder channel >=-75dBFS. DC, clipping, invalid
  lengths and contradictory timing/level signs yield unknown. These are provisional thresholds.
- Need >=3 supporting 100ms frames and >=80% agreement among directional frames. One noisy
  opposing frame no longer vetoes the whole window; genuinely mixed left/right remains unknown.
  Stable timing can tolerate ambiguous tonal frames; level-only evidence needs >=60% agreement.
  Classification ignores quiet beep pauses when counting that agreement. Monitor mode still
  requires recent evidence and clears on quiet. All-quiet windows never provide direction.
- Evidence travels with each queued audio block, not a later unrelated reading. Environmental
  events use their exact two-second recognition window. Multiple simultaneously emitted events
  receive no direction because one dominant stereo direction cannot identify each source.
- Name events remain directionless until their actual speech interval is associated.
- Existing fields: `direction_degrees=-90|90`, `direction_confidence`, `direction_source=pi_stereo`.
  Confidence is heuristic evidence quality, not measured probability of correctness.
- Existing 16-position triangle renderer accepts those degree values. Only left/right positions
  are used; two microphones do not resolve front/back. No distance or guessed fine azimuth.
- `/pi-audio/levels` includes a current `spatial` summary and optional numeric `spatial_frame`
  diagnostics. The site shows uncertain/no arrow when evidence is weak, stale or disconnected.

## Important transport fix

SSH normally coalesces multiple PCM blocks. Discarding every rapid arrival previously kept the
meters moving but prevented full recognition windows. Ordinary batching is now preserved; a >500ms
interruption resets buffers, drains for 300ms and starts a new generation. Overflow/disconnect also
clear buffers. Capture timestamps remain Mac receive time, not synchronized Pi timestamps; extreme
network backlog and physical disconnect/reconnect need further acceptance testing.

## Evidence and remaining acceptance

- Focused spatial/capture/phone tests and 58 frontend tests plus production build pass.
- Synthetic small-level-difference stereo timing resolves both sides. Canonical Fire/smoke events
  render matching left/right directions; unknown Pi evidence cannot be overwritten by phone data
  in the updated receiver code.
- Earlier close-up recording: first segment 30 left frames; second 56 right,14 unknown. No
  opposite-side frames in those segments. This is close-up evidence, not normal-distance accuracy.
- Real alarm recordings with artificially delayed stereo often remain unknown because periodic
  tones are ambiguous. They are synthetic direction fixtures, not real-room spatial accuracy.
- First live alarm trial detected alarms but mostly rejected direction (9 insufficient-consistency,
  8 no-current-evidence and 1 resolved-left alarm windows in the inspected interval). This exposed
  the beep-pause issue. Pulse-aware changes are loaded; **a repeat left/right trial is required**.
- Second trial produced several right-resolved alarm windows but no reliable left result. Most
  sampled monitor frames were below the old -65dBFS floor; it is now -75dBFS, retaining timing/
  coherence/consistency gates. **This sensitivity change still needs a fresh physical test.**
- Third trial after the lower floor still yielded 4 directionless alarm windows: 2 inconsistent,
  2 competing-side windows. The strict any-opposite-frame veto was relaxed to >=80% directional
  agreement, with tests for isolated outliers and balanced mixtures. **Not physically validated.**
- Gain offset defaults to zero; channel gain calibration and final-room wrong-side/unknown rates
  remain unmeasured. Echoes or competing sources may still mislead this heuristic.

Receiver 8766 was NOT restarted, preserving its memory-only Claude key. Its active phone spatial
status was verified disconnected with no devices. The new server guard against filling unknown Pi
directions from phone readings takes effect only on a future receiver restart; do not reconnect the
phone spatial experiment before then. The live Pi worker has the spatial changes loaded.

Run: `.venv/bin/python -m audio.cli mic --pi pi@glasses-pi.local --endpoint http://127.0.0.1:8766/events`.
This owns capture and meter port8768. Do not launch a second standalone meter/capture worker.

Phone-third-mic proposal and required synchronization/geometry gates:
[feasibility](third-microphone-feasibility.md). Not a connected third channel yet.
