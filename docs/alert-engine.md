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

| Direction | Optional `direction_degrees` (0 front, +90 right, -90 left, 180 behind) with `direction_confidence`. At confidence ≥ 0.6 the cue moves to that edge of the display (each side covers 90°); otherwise it stays centred. A two-microphone worker cannot tell front from behind and should send null rather than guess. |
| Resolution | A cue ends by **expiring** (logged), **Dismiss**, or the wearer **looking toward it** (`POST /look`). Looking acknowledges it like Dismiss, so repeats stay quiet. Only a directed cue can be resolved by looking (front, right, behind or left). |

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
rejected. Nothing else changes: the engine buckets it, the cue moves to that edge of the glasses,
the browser shows the same frame, and `/look` resolution starts working. Until measured, leave both
null and every cue stays undirected, which is today's honest behavior.
