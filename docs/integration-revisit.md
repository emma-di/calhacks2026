# Integration revisit list — October 24

Current checkpoint: keep one active OLED cue, with a fresh bounded queue and a full laptop log.
Freeze the visual direction around the fixed right-side optical patch, centered icon and surrounding
compass arrow. Unknown direction has no arrow. Browser patch scale is illustrative, not calibrated FOV.

| Revisit item | Trigger / owner | Acceptance check |
| --- | --- | --- |
| Physical OLED optics | Yameen supplies assembled glasses | Read all icons and urgent labels at eye position; verify mirror/flip and brightness |
| Panel placement/scale | Through-optics view and wearer feedback | Calibrate right-side patch size/position; keep the icon centered within the panel |
| Pi → laptop audio | Yameen + ML share capture details | Sample rate/channels/sync documented; live sound → event → both displays |
| Spatial direction | Measured synchronized inputs from ML | Verify coordinate frame/error; unknown stays unknown; compass points correctly |
| Name recognition | Speech worker supplied | Name/aliases → one deduplicated name cue; negative-name tests |
| Camera gesture tuning | Deferred at Emma's request after live trial | Several users, lighting, false/accidental dismissals and latency; reliable release/rearm. Keep manual Dismiss available |
| Physical dismiss control | Final input hardware agreed | Wearer can acknowledge exact current cue without laptop assistance; stale input cannot clear a newer cue |
| iPhone synchronized alert viewer | Implemented; real Safari/Wi-Fi trial pending | Connect real phone; validate latency, orientation, permissions, disconnect/reconnect and source labeling |
| iPhone camera POV | Continuity Camera selected; software help/device refresh implemented | Emma verifies actual selected device, movement, overlay, stop and reconnect; see iphone-camera.md |
| Custom sound recognition integration | John branch reviewed; 14 targeted tests passed | Port routes into current receiver, per-ID repeat/ack/settings, parser and OLED fallback; see john-audio-review.md |
| Cross-client preferences | More than one settings-owning companion | Revision/conflict ownership; opening a fresh viewer must not overwrite saved choices |
| Final room recognition | Audio owners + final mic | Miss/false-alert rates and total sound-to-cue latency |
| End-to-end health | Capture worker supplies heartbeat | Distinguish silence, listening, stalled inference and disconnected display |
| Contextual location/proximity rules | Reliable readings and agreed schema | Do not promote uncertain context into safety evidence |
| Submission readiness | Full team | Sign off event/profile contract; real hardware demo; fresh second Mac; truthful claims |

Phone status: access-key-protected read-only viewer implemented and tested at phone viewport size;
actual iPhone connection awaits Emma. See [setup](phone-mirror.md). It consumes authoritative receiver
state without saving settings. The laptop must use Receiver mode for matching cues. Browser-only
simulation stays local to that browser. Existing Use POV camera is a browser-visible webcam input,
not a remote phone camera streaming service.

Audio monitor: keep `audio/monitor.html` as a basic debug view, not a second product UI. Use it during
bring-up to isolate model → receiver versus receiver → polished site failures. No monitor redesign
is needed to freeze the simulator.

Multiple alerts: the OLED deliberately shows one cue. Higher priority interrupts; fresh eligible cues
wait in the queue. The laptop log exposes concurrent arrivals and outcomes for judges/debugging.
Revisit simultaneous visual cues only if wearer testing demonstrates a need.
