# Alert engine, receiver API and glasses bring-up

Status, October 23 (Emma's lane): **implemented and tested in software.** Saved preferences change
receiver priority; dismiss, repeats, Work/Do not disturb, pause, the waiting queue and stale-cue
clearing work end to end through HTTP, the browser and a glasses client writing frames. Not yet
shown on the physical SSD1306, with final microphones, or across two machines.

## One engine, two copies, one set of rules

`audio/alerts.py` is authoritative in Receiver mode. `frontend/src/lib/alerts.ts` is a line-for-line
port so the browser simulator behaves identically. Both replay `audio/alert-scenarios.json` in their
tests; change behavior by editing the scenarios first. Timing and presets live in
`audio/alert-policy.json` (Balanced agreed; Gentle/Active provisional) and a test checks they match
the Mana onboarding defaults.

| Situation | Behavior |
| --- | --- |
| Effective tier | Explicit user rule, else the preset, else the producer's legacy tier. Producers no longer decide. |
| Tier 0 | Logged as Ignored; never shown. |
| Higher or equal tier arrives | Takes over. An interrupted Notify/Attention cue waits and returns if still fresh. |
| Lower tier arrives | Ambient is skipped. Notify/Attention waits (max 5, dropped after 10 s, never shown late). |
| Same sound repeats while shown | Merged into the same cue; lifetime and animation do not restart. An Urgent sound that keeps going stays up to 2 minutes. |
| Dismiss | Acknowledges that sound: repeats stay quiet while they continue (15 s after the last one). Dismiss names the event ID, so a stale click cannot clear a newer urgent cue. |
| Work / Do not disturb | Work passes Attention and Urgent. Do not disturb passes Urgent only. Switching clears anything now below the bar. |
| Pause | Hides everything, Urgent included, and clears the queue. The UI says so. It does not stop capture. |
| Duplicate event ID | Counted once. |
| Lifetimes | Ambient 2 s, Notify 3 s, Attention 5 s, Urgent 30 s (unchanged from before). |

| Direction | Optional `direction_degrees` (0 front, +90 right, -90 left, 180 behind) with `direction_confidence`. At confidence ≥ 0.6 a compass arrow appears around the centered icon (each side covers 90°); otherwise no arrow appears. A two-microphone worker cannot tell front from behind and should send null rather than guess. |
| Gesture to dismiss | A `thumbs_up` event (hand held up for ⅓ s, seen by a camera) dismisses the showing cue; with nothing showing it is ignored. The companion runs MediaPipe's hand-gesture model in the browser on the lens camera (the glasses' camera when it appears as a webcam, or the laptop's) and posts the event with `source: "camera"`; any other camera worker can post the same event. Audio `finger_snap` is still accepted but its recognizer rule is disabled: quiet snappers and loud alarms make it unreliable. `gesture_to_dismiss.count: 2` would require two. |
| Confirmation | Whenever the wearer resolves a cue (thumbs-up, Dismiss, Look) the glasses and lens show a check mark for 0.6 s where the cue was; a waiting cue resumes after it. Expiry shows nothing. |
| Resolution | A cue ends by **expiring** (logged), **Dismiss**, a **thumbs-up**, or the wearer **looking toward it** (`POST /look`). Looking acknowledges it like Dismiss, so repeats stay quiet. Only a directed cue can be resolved by looking (front, right, behind or left). |

Every decision has a reason code and a plain-language sentence (`frontend/src/lib/explain.ts`) shown
on the Live screen and in the Event log.

## Receiver API (`python3 -m audio.server`)

| Endpoint | Purpose |
| --- | --- |
| `GET /state` | Companion snapshot. Keeps `active/events/decisions`; adds `session_id`, `state_sequence`, `remaining_ms`, `focus_mode`, `paused`, `queue`, `health`, `display`. `active.priority_tier` is the effective tier; `producer_tier` keeps the original. |
| `GET /display?client=NAME` | Glasses envelope (`hardware.display.Presentation` with optional `direction`, plus `show_labels`, `age_ms`). Polling it marks that display connected in `/health` for 3 s. |
| `GET /health` | Receiver, capture (recent events per source; silence is not disconnection), display clients, `name_worker` and `spatial` reported as unavailable. |
| `GET/PUT /profile` | Validated profile, server-assigned revision, written atomically to `.cache/profile.json` and reloaded on restart. The companion pushes it automatically whenever it connects or preferences change. |
| `POST /events` | v1 events. Now also accepts `name_called` and `confidence: null` (NAME-04) for the planned speech worker. Replies with the decision. |
| `POST /dismiss` | `{"event_id": "..."}`; omit the ID to dismiss whatever is showing. |
| `POST /controls` | `{"focus_mode": "everyday" \| "work" \| "dnd", "paused": bool}`. |
| `POST /look` | `{"direction": "front"\|"right"\|"behind"\|"left"}` or `{"heading_degrees": n}` from a head-orientation source (none in today's hardware; the companion's Look button simulates it). Replies `{"resolved": bool}`. |

The receiver binds to 127.0.0.1. `--host 0.0.0.0` exposes it to the local network so the Pi can poll
`/display`; use that only on a trusted network. `--port` changes the port; point the dev server at
it with `AWARE_RECEIVER=http://HOST:PORT npm run dev --prefix frontend`.

## Glasses bring-up for Yameen

`hardware/oled_client.py` polls `/display`, keeps `DisplayState`'s expiry and stale-sequence guards,
clears the screen after three failed polls, and only writes when pixels change. The browser preview
draws the same frames (`frontend/src/lib/oled.ts` is checked byte for byte against
`hardware/render-fixtures.json`).

```sh
# On the Pi: enable I2C (raspi-config), then
pip install smbus2
python3 -m hardware.oled_client --sink ssd1306 --self-test          # HW-03: fake cues, no network
python3 -m hardware.oled_client --sink ssd1306 --flip-x --self-test # if the combiner mirrors it
# Laptop: python3 -m audio.server --host 0.0.0.0
python3 -m hardware.oled_client --receiver http://LAPTOP_IP:8765 --sink ssd1306 [--flip-x] [--flip-y]
```

No OLED yet? `--sink ascii` draws frames in a terminal; `--sink pbm --output file.pbm` writes images.
The client logs roughly how long after the receiver accepted each cue it was drawn (receiver to
display only; add capture and inference time for the full sound-to-screen figure). The SSD1306
initialisation is the standard 128×64 I²C sequence at address 0x3C and is unit-tested against a fake
bus, not yet against the module. Check orientation, contrast and readability through the optics.

## Camera

Show my room puts the browser camera behind the cue so a judge sees cues over their own surroundings.
It starts only from a click, stays in the tab and is never recorded or sent. If the glasses later
expose a camera as a webcam, pick it from the camera menu that appears when more than one exists.
The hardware list does not include a camera, and nothing on the glasses depends on one.

## Verified on October 23

- 34 Python tests (shared scenarios, profile validation, HTTP receiver, persistence across restart,
  glasses client against a fake I²C bus, render fixtures) and 9 frontend tests (same scenarios, preset
  parity, explanations, byte-identical frames). Production build and taste lint/inspector pass.
- Live run: browser Ignore rule → receiver (revision bump) → dog ignored, knock drawn by the glasses
  client 71 ms after the receiver accepted it; Work/DND/pause through the UI; killing the receiver
  cleared the browser and glasses; restarting reloaded preferences and did not replay the alarm.
- Camera path tested with a synthetic stream (feed, stop, blocked permission). A real webcam was not
  opened during testing.

## Direction handoff for the spatial work (John and Leo)

Send direction on the normal event: `direction_degrees` in −180..180 relative to the wearer's face
(0 ahead, +90 right, −90 left) and `direction_confidence` in 0..1. Both or neither; distance stays
rejected. Nothing else changes: the engine buckets it, a compass arrow appears around the centered icon,
the browser shows the same frame, and `/look` resolution starts working. Until measured, leave both
null and every cue stays undirected, which is today's honest behavior.

## Camera gesture

`frontend/src/lib/gesture.ts` loads MediaPipe Tasks Vision 1.1.1 only while the lens camera is on,
checks about 15 frames a second, and fires once per 1.5 s when "Thumb_Up" (score > 0.6) is held
for 330 ms. Runtime and model are served from `frontend/public/mediapipe/` (filled by
`scripts/vendor-mediapipe.mjs` before dev/build; the 8 MB model stays out of Git and falls back to
Google's copy if missing). Video never leaves the tab. The lens shows "Thumbs up to dismiss" while
watching and turns amber while a thumbs-up is being held.

## Camera correction — October 24 (current)

The physical glasses have no camera. The camera backdrop is demonstration-only. The app no longer
runs gesture recognition or exposes the thumbs-up button. Earlier camera-gesture sections describe
experimental code retained outside the current flow, not the physical build. Use manual Dismiss or
expiry. A future physical input adapter can reuse the receiver contract if hardware is supplied.

## Session-only recognition testing — October 24

Live → **Show every detection** sends `POST /controls {"repeat_suppression": false}`.
The receiver bypasses acknowledgement holds and same-sound merging; distinct detections restart
the cue. The microphone/file CLI polls receiver health at most once per second and bypasses
built-in, name and taught-sound cooldowns too. Thresholds, context suppression, tier 0, focus, pause,
queue ordering and duplicate IDs remain active. This is a session control, not a saved preference:
receiver restart restores normal suppression. Missing/unreachable control data restores recognition
cooldowns. A standalone recognizer without a receiver keeps normal cooldowns.

Hearing now shows name-recognizer emitted/cooldown decisions when present; Event log shows whether
the receiver displayed, queued, merged or suppressed the emitted event. A missing name match is
not evidence that the person did not say the name.

The urgent `smoke_alarm` event now accepts both exact model labels `Fire alarm` and
`Smoke detector, smoke alarm`, and is labeled Fire / smoke alarm. Both suppress a competing bell
rule. Generic Alarm/Alarm clock are not directly mapped to fire. Broader alias matching remains
provisional: cached recorded-score evaluation found additional false positives (including alarm
clocks and crickets); see reports/fire-alarm-alias-review.json. Real room calibration is still needed.

## Ongoing fire-alarm lifecycle and camera-free input — October 24

Fresh `/observations` windows from the active alarm's own capture source now feed the alert engine.
The urgent fire/smoke cue clears after 4,000 ms of continuous below-threshold evidence; a positive
window restarts that quiet hold. A gap over two seconds resets continuity. Missing capture, stale
uploads and another source's quiet windows do not prove the alarm stopped. Windowing adds capture
latency to the quiet hold. Automatic clearing logs `sound_stopped`, does not acknowledge the sound
or show a wearer-confirmation check, and resumes a fresh waiting cue. The original maximum lifetime
remains the fallback if evidence stops arriving. This is absence of model evidence, not proof that
a physical fire or danger has ended.

Live → **Snap to dismiss** sets session-only `snap_to_dismiss` via `/controls`. Off by default; enabled
for Emma's requested test. CLI enables Finger snapping only while a cue exists, requires score >=0.8,
and scopes the resulting gesture to the current `target_event_id`; a stale snap cannot dismiss a
replacement cue. An overlapping high-score window stays latched until the score drops below0.4.
Camera thumbs-up remains optional and independent; neither glasses nor snap dismissal need a camera.
Snap accuracy and latency are experimental until actual wearer/room tests pass. Inference uses 2s
windows, so this is not an instant hardware button. Manual Dismiss remains available.

Claude's centered icon + solid direction triangles remain byte-identical in Python and browser
renderers. No direction feed means no triangle. Simulated directions remain confined to mock cues.


## October 25: direction refresh and rail/horn presentation stability

A merged repeat keeps its original displayed event ID/start time, but fresh confident direction
from the same source updates its bearing and display sequence. Delayed, low-confidence and
foreign-source updates do not replace it. Direction provenance follows the new evidence; the
original event-history record is not rewritten. Existing urgent lifetime extension still applies.

The four curated custom symbols Train, Train horn, Car horn and Truck horn form a narrow
presentation family: a different family label from the same source at the same/lower tier merges
into the currently shown cue until its existing lifetime expires, instead of rapidly replacing it
or queuing alternate icons. This applies even with repeat suppression off. Higher-tier and
unrelated alerts retain normal interruption behavior. It is not proof that labels came from one
physical source; the raw observations remain available in Log.

Both engines share timeline fixtures for direction changes, expiry, alternate icons and urgent
interruption. Python receiver changes require a receiver restart; hot frontend updates alone do
not update an already-running Python process.
