# Custom sounds ("teach it your doorbell")

Status: **recognition implemented** (CLI + live detection). The onboarding HTTP endpoints below are a
**proposed contract** for the website; they are not built yet.

## How it works

The Zipformer backbone stays frozen. Its last layer averages per-frame encoder features before the
527-label classifier; that 256-number average is used as a sound **embedding**
(`audio/embeddings.py`). It comes from the same inference that produces the normal scores, so
built-in alerts are unchanged (scores verified identical to the sherpa-onnx path).

Each custom sound gets a tiny logistic-regression **head** (`audio/custom_sounds.py`):

- **Positives:** the user's 3–10 recordings, split into 2-second windows; silent windows are dropped.
- **Negatives:** a local background bank of everyday sounds, plus true silence.
- **Threshold:** set automatically so only 0.5% of held-out background windows would trigger
  (clipped to 0.5–0.97). Held-out background is split by whole recording, not by window.
- Training takes about a second on a laptop. No GPU, no backbone fine-tuning.

At runtime, every live window's embedding is scored by every enabled head. A hit emits a normal v1
event with `type: "custom"` and a 5-second per-sound cooldown.

## Commands

Install `requirements-audio.txt` (adds `onnx`, `onnxruntime`, `kaldi-native-fbank`), then:

```sh
# Once: build the background bank from the benchmark audio (run prepare_benchmark first)
.venv/bin/python -m audio.custom_sounds build-background

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
mic for the demo), at a normal distance, and keep each clip short (1–5 s) with little silence. Adding
10 seconds of the room's ordinary background as extra negatives is planned and will reduce false alerts.

## Storage

Everything lives in `.cache/custom-sounds/` (gitignored, never uploaded):

```
.cache/custom-sounds/
  background.npz              # background bank embeddings
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

## Proposed onboarding contract (not built yet)

The website records clips and talks to the local Python server; it never touches the model.

| Route | Body | Result |
| --- | --- | --- |
| `GET /custom-sounds` | | list of `meta.json` objects |
| `POST /custom-sounds` | `{"label": "Front doorbell", "priority_tier": 2}` | new `meta` with `id`, `status: "recording"` |
| `POST /custom-sounds/{id}/clips` | one WAV, **16 kHz mono**, ≤ 30 s, `Content-Type: audio/wav` | updated `meta` (`clip_count`) |
| `POST /custom-sounds/{id}/train` | `{}` | `meta` with `status: "ready"` or `"failed"` and a `training` report |
| `POST /custom-sounds/{id}/test` | one WAV | `{"detected": true, "score": 0.91, "threshold": 0.8}` for a "try it once more" step |
| `PATCH /custom-sounds/{id}` | `{"enabled": false}` or `{"label": …, "priority_tier": …}` | updated `meta` |
| `DELETE /custom-sounds/{id}` | | `{"ok": true}` |

`status` moves `recording → training → ready | failed`. Suggested UI: 5 recordings, then train,
then a test recording. Show `training.training_recall` and the error message on failure.

Integration notes for the website:

- **Audio format:** browsers record WebM/Opus by default. Convert to WAV 16 kHz mono in the browser
  (Web Audio API) before upload, so the server needs no ffmpeg.
- **CORS:** if the site runs on its own dev server (e.g. `localhost:3000`), the Python server must send
  CORS headers for that origin and answer `OPTIONS`. Alternatively, serve the built site from
  `audio.server` so they share an origin.
- The receiver binds to loopback with no authentication; keep it that way.
- The website can build against a mock of these routes now; the server functions already exist
  (`create_sound`, `add_clip`, `train_sound`, `remove_sound`, `list_sounds`).

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
