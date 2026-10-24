# Handoff: live site (simulation + real-time mirroring)

For Emma, from John's audio work (branch `johnaou/custom-sounds`). This is everything the live site
needs to show alerts from the audio pipeline, in either **simulation** or **real-time** mode, and to
host the "teach a sound" onboarding.

## TL;DR

- **Ready now:** the local Python server at `http://127.0.0.1:8765` publishes the current alert and
  recent events at `GET /state`. Poll it (the existing monitor polls every 250 ms). CORS is open to any
  `localhost` / `127.0.0.1` port, so a dev server such as `localhost:3000` can call it directly.
- **Simulation** = feed it fake or recorded events. **Real-time** = run the microphone CLI. The site
  code is identical for both; only `event.source` differs (`mock`, `replay`, `simulation`, `microphone`).
- **Custom sounds** (user-taught, e.g. "Front doorbell") arrive as normal events with `type: "custom"`
  and the user's own `label`. Onboarding routes are in [custom-sounds.md](custom-sounds.md);
  a working reference page is at `http://127.0.0.1:8765/teach`.
- **Not built yet:** name detection ("someone is saying your name"), a raw per-window classification
  stream, user preferences / a real alert queue, and direction (always `null`).

## How the pipeline fits together

```
mic / recording ──► classifier (Zipformer, every 1 s, 2 s window)
                        │  527 AudioSet scores + 256-number embedding
                        ├──► built-in rules (thresholds, cooldown)  ─┐
                        └──► custom-sound heads (user-taught)        ├─► event JSON ─► POST /events
                                                                     │
   [planned] speech model ──► name matcher ──────────────────────────┘
                                                                          │
                                       server: priority tiers, active alert, decision log
                                                                          │
                                         GET /state  ◄── live site / monitor / glasses (poll)
```

The classifier scores every window continuously. What reaches the user is decided after that, in two
places: the recognition rules (per-sound thresholds, 5 s cooldown, alarm-suppresses-bell) and the
server's priority stage (which alert is on screen, for how long). Every window's top-5 scores and
every decision go to `.cache/recognition-decisions.jsonl` for debugging, but they are **not** streamed
to the site today (see "Proposed next interfaces").

## Run it

One-time setup is in the [README](../README.md) (Python 3.12, `requirements-audio.txt`,
`audio.download_model`, `audio.prepare_benchmark`). Then from the repo root:

```sh
# Server only (needs nothing but Python): the site can poll /state immediately
python3 -m audio.server

# --- Simulation ---
python3 -m audio.cli fake knock            # one mock event (any type below)
python3 -m audio.cli fake smoke_alarm      # tier 4, stays up to 30 s
.venv/bin/python -m audio.demo --event dog_bark          # real model on a labeled recording
.venv/bin/python -m audio.cli file some.wav --realtime --endpoint http://127.0.0.1:8765/events

# --- Real time ---
.venv/bin/python -m audio.cli devices                    # find the mic index
.venv/bin/python -m audio.cli mic --device 1 --endpoint http://127.0.0.1:8765/events
```

The mic process loads custom sounds automatically and picks up newly taught ones within about
2 seconds, so the mic can stay running while someone teaches a sound in the UI.

## The API the site uses

### `GET /state` (poll it)

```json
{
  "active": { …event… } | null,
  "events": [ …last 50 events received, oldest first… ],
  "decisions": [ …last 50 display decisions… ]
}
```

- `active` is the alert to show right now, or `null`. It expires on the server by tier:
  tier 1: 2 s, tier 2: 3 s, tier 3: 5 s, tier 4: 30 s (or until dismissed).
- A new event replaces the active one if its tier is **greater than or equal to** the current tier.
  Lower-tier events during a higher-tier alert are recorded in `events`/`decisions` but are **not
  queued** for later display. Tier 0 is never shown.
- To detect "a new alert appeared", compare `active.event_id` with the last one you rendered
  (that's what `audio/monitor.html` does; copy its `poll()`).
- `decisions` entries: `{event_id, type, priority_tier, reason, active_type}` where `reason` is
  `displayed`, `suppressed_lower_priority` or `ignored_tier_zero`. Useful for a debug panel or for
  showing "also heard: dog barking" under a smoke alarm.

### `POST /dismiss`

Body `{}` with `Content-Type: application/json`. Clears the active alert.

### `POST /events` (for site-driven simulation)

The site can inject its own scripted events, e.g. a "play scenario" button. Send a full v1 event
with `source: "simulation"`; the server validates it and returns `400` with a reason if it's wrong.

```json
{
  "schema_version": 1,
  "event_id": "any-unique-string",
  "type": "knock",
  "label": "Door knock",
  "confidence": 0.8,
  "source": "simulation",
  "priority_tier": 2,
  "timestamp_ms": 1792800000000,
  "direction_degrees": null,
  "direction_confidence": null,
  "distance_meters": null,
  "proximity": "unknown"
}
```

Rules: `confidence` is 0–1; `priority_tier` is an integer 0–4; `timestamp_ms` is a non-negative
integer; the direction and distance fields must be `null` (non-null values are rejected until
localization exists); body ≤ 8 KB.

### Event types

| `type` | Default `label` | Tier | Notes |
| --- | --- | --- | --- |
| `smoke_alarm` | Smoke alarm | 4 | limited test evidence; stays up 30 s |
| `siren` | Siren | 3 | |
| `knock` | Door knock | 2 | |
| `alarm_clock` | Alarm clock | 2 | |
| `bell` | Bell / chime | 2 | generic bell; still experimental (some false alerts) |
| `dog_bark` | Dog barking | 1 | |
| `custom` | *the user's name for it* | user-chosen 1–4 | has `custom_sound_id` |
| `bicycle_bell` | Bicycle bell | 2 | disabled in the default policy; may appear from `fake` |

Display `event.label` and use `priority_tier` for urgency styling. Don't hard-code labels per type;
custom sounds make labels user-defined. `confidence` is a model score, **not** a probability. Don't
show it as "92% sure". `model` and `inference_ms` may be present on real events.

### Custom-sound onboarding

Full route table, status codes, and audio-format notes: [custom-sounds.md](custom-sounds.md#onboarding-http-routes-implemented).
The short version: `POST /custom-sounds` (name + tier) → `POST …/{id}/clips` five times (WAV) →
`POST …/{id}/train` → `POST …/{id}/test`. Optionally `POST /background/clips` with 10 s of room audio
first. Copy `recordWav()` and `toWav16k()` from `audio/teach.html` for browser recording; browsers
record WebM, and the server wants WAV.

## Simulation vs real-time on the site

The site never needs to know which mode it's in. It always polls `/state`. Suggested UI:

- Show a small source badge from `event.source` so a judge can tell a simulated alert from a live one.
- **Simulation mode:** buttons that `POST /events` scripted events (or call the CLI scenarios above).
  A good demo script: dog bark (tier 1) → knock (tier 2, replaces it) → smoke alarm (tier 4, holds) →
  knock during the alarm (stays hidden; it shows up in `decisions`) → dismiss.
- **Real-time mode:** run `audio.cli mic …` on the same laptop; the site just keeps polling.
- If `/state` fails, show "disconnected" (the monitor does this). The server can restart independently.

## Known limitations to design around

- **Polling only.** There's no WebSocket or server-sent events; 250 ms polling is fine on loopback.
- **No queue.** A lower-tier alert that arrives during a higher one is never shown later.
- **Latency.** Windows are 2 s with 1 s hops, so expect about 1–2 s from sound to alert.
- **Direction is unknown.** Show no arrow; `proximity` is always `"unknown"`.
- **Loopback only, no auth.** The site must run on the same machine as the server.
- **Not validated live.** All accuracy numbers come from offline recordings. A noisy hackathon room and
  the glasses mic still need testing before any claims.

## Proposed next interfaces (not built; tell John what you need)

1. **Raw classification stream.** Something like `GET /observations` with each window's top-k labels and
   scores and any custom-sound scores, so the site can show a live "what the glasses hear" meter and so
   post-processing (preferences, mute, per-user thresholds) can move out of the recognizer.
2. **Name detection.** Planned `type: "name_called"`, label "Your name", tier 3, from a local speech model
   reading the onboarding profile. See [name-detection-plan.md](name-detection-plan.md).
3. **Preferences.** Per-type mute or tier override from the onboarding profile, applied in the server's
   priority stage.
