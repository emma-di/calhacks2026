# Custom sounds ("teach it your doorbell")

Status: **implemented**: training, live detection, room background, and the onboarding HTTP routes.
A reference page at **http://127.0.0.1:8765/teach** runs the whole flow in the browser.

## How it works

The Zipformer backbone stays frozen. Its last layer averages per-frame encoder features before the
527-label classifier; that 256-number average is used as a sound **embedding**
(`audio/embeddings.py`). It comes from the same inference that produces the normal scores, so
built-in alerts are unchanged (scores verified identical to the sherpa-onnx path).

Each custom sound gets a tiny logistic-regression **head** (`audio/custom_sounds.py`):

- **Positives:** the user's 3–10 recordings, split into 2-second windows; silent windows are dropped.
- **Negatives:** a local background bank of everyday sounds plus true silence, **and recordings of the
  user's own room** (chatter, HVAC, music). Adding room audio retrains every trained sound.
- **Threshold:** set automatically so only 0.5% of held-out background windows would trigger
  (clipped to 0.5–0.97). Held-out background is split by whole recording, not by window.
- Training takes about a second on a laptop. No GPU, no backbone fine-tuning.

At runtime, every live window's embedding is scored by every enabled head. A hit emits a normal v1
event with `type: "custom"` and a 5-second per-sound cooldown. A running `audio.cli mic`/`file` process
**reloads sounds within ~2 seconds** when one is trained, retrained, enabled, disabled or deleted, so
sounds taught in the UI work without restarting the microphone.

## Commands

Install `requirements-audio.txt` (adds `onnx`, `onnxruntime`, `kaldi-native-fbank`), then:

```sh
# Once: build the background bank from the benchmark audio (run prepare_benchmark first)
.venv/bin/python -m audio.custom_sounds build-background

# Optional: add recordings of your ordinary room as extra negatives (retrains all sounds)
.venv/bin/python -m audio.custom_sounds add-room room1.wav room2.wav

# Teach a sound from recordings (WAV/FLAC/OGG; any sample rate, converted to 16 kHz mono)
.venv/bin/python -m audio.custom_sounds add "Front doorbell" bell1.wav bell2.wav bell3.wav --tier 2

.venv/bin/python -m audio.custom_sounds list
.venv/bin/python -m audio.custom_sounds test another-recording.wav   # per-second scores
.venv/bin/python -m audio.custom_sounds retrain front-doorbell
.venv/bin/python -m audio.custom_sounds remove front-doorbell
```

`audio.cli file …` and `audio.cli mic …` (and therefore `audio.demo`) automatically load every ready
custom sound when the model is Zipformer. Use `--no-custom` to turn them off. Decision logs include
per-sound scores and reasons (`below_threshold`, `cooldown`, `silent_window`, `emitted`).

**Recording tips:** record each example on the device that will listen (the glasses mic, or the laptop
mic for the demo), at a normal distance, and keep each clip short (1–5 s) with little silence.
Record 10 seconds of the room as it normally sounds. Heads learn *your* sound, not the category:
in a browser test, the taught church bell scored 0.97 on a new recording, a different church's bell
scored 0.60 (below the 0.7 threshold), and room noise scored 0.04. To cover several variants
(e.g. two doorbells), record each variant in the same sound or teach them separately.

## Storage

Everything lives in `.cache/custom-sounds/` (gitignored, never uploaded):

```
.cache/custom-sounds/
  background.npz              # everyday-sound embeddings (build-background)
  room.npz                    # the user's room recordings, as embeddings only
  version                     # touched on every change; live detectors reload
  front-doorbell/
    meta.json                 # label, tier, status, training report
    clips/00.wav …            # 16 kHz mono recordings
    head.npz                  # weights, normalization, threshold
```

`meta.json` is written atomically, so the live detector never reads a partial file.

## Event

```json
{
  "schema_version": 1,
  "event_id": "uuid",
  "type": "custom",
  "custom_sound_id": "front-doorbell",
  "label": "Front doorbell",
  "confidence": 0.93,
  "source": "microphone",
  "priority_tier": 2,
  "timestamp_ms": 1792800000000,
  "direction_degrees": null,
  "direction_confidence": null,
  "distance_meters": null,
  "proximity": "unknown"
}
```

`label` is the user's own name for the sound, so the monitor and future display adapters show it
without special handling. `confidence` is the head's score, not a calibrated probability.
The receiver accepts `type: "custom"` only with a `custom_sound_id`.

## Onboarding HTTP routes (implemented)

Run `.venv/bin/python -m audio.server`. The website records audio in the browser and calls these
routes on `http://127.0.0.1:8765`; it never touches the model. Errors return `{"error": "…"}`.

| Route | Body | Result |
| --- | --- | --- |
| `GET /custom-sounds` | | `{"sounds": [meta…], "background": {…}}` |
| `POST /custom-sounds` | `{"label": "Front doorbell", "priority_tier": 2}` | `201`, new `meta` with `id`, `status: "recording"` |
| `GET /custom-sounds/{id}` | | `meta` |
| `POST /custom-sounds/{id}/clips` | one recording, `Content-Type: audio/wav`, ≤ 30 s | updated `meta` (`clip_count`) |
| `DELETE /custom-sounds/{id}/clips` | | `meta` with recordings cleared ("start over") |
| `POST /custom-sounds/{id}/train` | `{}` | `meta` with `status: "ready"` and a `training` report |
| `POST /custom-sounds/{id}/test` | one recording | `{"detected": true, "score": 0.97, "threshold": 0.7, "window_scores": […]}` |
| `PATCH /custom-sounds/{id}` | any of `{"label", "priority_tier", "enabled"}` | updated `meta` |
| `DELETE /custom-sounds/{id}` | | `{"ok": true}` |
| `GET /background` | | `{"base_windows", "room_windows", "room_clips", "ready"}` |
| `POST /background/clips` | one room recording | status plus `retrained: [{id, status}]` |
| `DELETE /background` | | clears room recordings, retrains |

`status` moves `recording → training → ready | failed`; adding a recording after training sets
`needs_training`. Status codes: `400` bad input (no recordings, silent audio, bad WAV),
`404` unknown sound, `503` missing model, dependency or background bank. Training takes about a
second; the first audio request also loads the model (a few seconds).

Suggested flow (what `/teach` does): record 10 s of room → name + tier → 5 recordings → train →
test with one new recording → show "Recognized" or "add more recordings and retrain".

Integration notes for the website:

- **Audio format:** the server reads 8/16/32-bit PCM WAV at any sample rate and channel count with
  NumPy only; 16 kHz mono is smallest. Browsers record WebM/Opus, so convert before upload: copy
  `recordWav()` / `toWav16k()` from `audio/teach.html`. Turn off `echoCancellation`,
  `noiseSuppression` and `autoGainControl` in `getUserMedia`; those filters treat many alert sounds as noise.
- **CORS:** allowed automatically for `http://localhost:*` and `http://127.0.0.1:*` (any dev-server
  port). Add other origins with `CALHACKS_CORS_ORIGINS=https://a.example,https://b.example`.
- **Microphone permission** needs a secure context; `localhost` counts.
- The server binds to loopback with no authentication; keep it that way.

## Evaluation (ESC-50, offline)

Each of the 50 ESC-50 classes took a turn as the custom sound: k training recordings from folds 1–3,
tested on folds 4–5 recordings **from different source recordings**, with the other 49 classes
(784 recordings) as false-alert candidates. A recording counts as detected if any window crosses the
threshold. Averages over 3 random draws; full per-class results in
[reports/custom-sounds.json](../reports/custom-sounds.json).

| Training recordings | Mean recall | False alerts per negative 5 s recording |
| --- | --- | --- |
| 3 | 81.5% | 0.24% |
| **5 (suggested)** | **92.2%** | **0.35%** |
| 10 | 94.8% | 0.52% |

Household examples at 5 recordings (recall / false alerts out of 784): church bells 100% / 0,
toilet flush 100% / 0, alarm clock 98% / 0, car horn 94% / 0.7, door knock 94% / 3.3,
vacuum 92% / 2.7, glass breaking 90% / 0.3, crying baby 100% / 3.7.
Weakest: **washing machine 56%** and **wind ~55%** (steady broadband noise is easily confused with
engines and sea waves). Most false alerts come from near-identical classes (coughing ↔ sneezing,
pouring ↔ dripping water, airplane ↔ helicopter).

Threshold floor sweep (5 recordings): floor 0.5 → 94.1% recall / 0.70% false alerts;
**0.7 (default) → 90–92% / 0.36%**; 0.8 → 87.2% / 0.22%; 0.9 → 77.6% / 0.08%.

Caveats: ESC-50 clips are clean and may overlap the model's AudioSet pretraining. Training and test
come from different sources, which is harder than the real use case (same doorbell, same mic) but
says nothing about a noisy room or the glasses microphone. Validate live before demo claims.

Reproduce (downloads not included; point at a local ESC-50 copy):

```sh
.venv/bin/python -m audio.evaluate_custom --esc50 path/to/ESC-50 --shots 3 5 10 --repeats 3
```
