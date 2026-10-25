# Name detection

Status: **implemented and running in the live pipeline.** Accuracy has been measured on synthetic voices only;
validate with real people and the demo microphone before making claims.

When someone says the user's name, the pipeline emits a `name_called` event (label **"Your name"**,
tier 3). It interrupts tier 1–2 alerts but never replaces a tier-4 smoke alarm.

## How it works

- **Model:** sherpa-onnx Zipformer keyword spotter (3.3M parameters, English, trained on GigaSpeech).
  It's a streaming model in the same library as the sound classifier, so it listens continuously and
  fires about when the name finishes. No transcripts are produced or stored.
- **Keywords come from the profile:** the typed name and nicknames, converted to the model's word pieces.
  No per-user training.
- **Learned spellings (optional, recommended):** the model's 500-piece vocabulary spells uncommon names
  from fragments and may hear them differently ("Yameen" → "YEMY"). Recording someone saying the name
  adds *how the model hears it* as extra keywords. Spellings that are or contain common English words
  ("why" for Wei, "don't" for John) are rejected, because they would fire constantly. The ~1,000-word list
  is `audio/common-words.txt`, plus the model's own whole-word pieces.
- **Shared capture:** the microphone now delivers 0.2 s blocks. The name spotter gets every block
  immediately; the sound classifier still analyzes 2 s windows every 1 s. The mic is opened once.
- **Hot reload:** a running `audio.cli mic`/`file` process picks up profile changes within about 3 seconds.
- **Cooldown:** 3 s between name alerts.

## Setup

```sh
.venv/bin/python -m pip install -r requirements-audio.txt     # adds sentencepiece
.venv/bin/python -m audio.download_model --names              # ~17 MB keyword model
.venv/bin/python -m audio.server                              # then open http://127.0.0.1:8765/teach
```

On `/teach`: type the name and nicknames, tick **on**, Save, then have a friend say only the name 3 times
with **Record someone saying your name**. Start the mic (`audio.cli mic … --endpoint …`) and say the name.
`--no-names` turns name detection off for a session.

## Profile and routes

`.cache/profile.json` (gitignored) follows [onboarding-profile.example.json](onboarding-profile.example.json).
Other keys (e.g. `notification_preferences`) are preserved, so the onboarding UI can own the whole file.

| Route | Body | Result |
| --- | --- | --- |
| `GET /profile` / `PUT /profile` | | the receiver's profile; see docs/alert-engine.md |
| `POST /profile/name-samples` | WAV of someone saying only the name | `{"heard", "spelling", "added", "note", "profile"}`; `400` if only common words were heard |
| `DELETE /profile/name-samples` | | profile with learned spellings cleared |

`name_detection` fields: `enabled` (bool), `primary_name` (defaults to `display_name`), `aliases` (≤ 8),
`language` (`"en"` only), `sensitivity` (`"low"`, `"balanced"`, `"high"`), `learned_spellings`
(`[{text, tokens}]`, ≤ 8, written by the server).

## Event (schema v2)

```json
{
  "schema_version": 2,
  "event_id": "uuid",
  "type": "name_called",
  "label": "Your name",
  "source": "microphone",
  "recognizer": "sherpa-onnx-kws-zipformer-3.3M",
  "confidence": null,
  "confidence_kind": "unavailable",
  "matched_alias_id": "primary",
  "profile_revision": 4,
  "priority_tier": 3,
  "timestamp_ms": 1792800000000,
  "direction_degrees": null,
  "direction_confidence": null,
  "distance_meters": null,
  "proximity": "unknown"
}
```

`confidence` is `null`: keyword spotting gives a yes/no match, not a score. The receiver validates name
events as schema v2 (`validate_name_event` in audio/events.py) and the companion parses them. `matched_alias_id` is `primary`, `alias-N` or `learned-N`.
Name alerts also appear in the observation stream's `emitted` list.

**Who owns the profile:** the receiver (`audio/server.py`, schema in `audio/alerts.py`). The companion
pushes its saved Preferences, including the name, whenever it connects, so set the name there.
`sensitivity` and `learned_spellings` belong to the name worker: a save that omits them keeps them, and
learned spellings are dropped only when the name itself changes. `GET /health` reports `name_worker` as
`off`, `model_missing`, `idle` or `listening` (a capture source sent something in the last 10 s).

## Results (synthetic voices)

10 names (John, Emma, Yameen, Priya, Mateo, Grace, Kai, Siddharth, Wei, Olivia). 534 synthetic utterances
from 904 voices: each name in 8 sentence positions, 15 sound-alike utterances per name ("Joan", "Bolivia",
"tomato"), 144 name-free sentences. Each name ran as one continuous stream, like a live mic.
Full data: [reports/name-detection.json](../reports/name-detection.json).

| Setting (balanced sensitivity) | Quiet | Everyday noise, 10 dB SNR |
| --- | --- | --- |
| Typed name only | 43% caught | 40% |
| **Typed name + learned spellings** | **62%** | **55%** |

Per name (quiet, learned): Olivia 92%, Grace 83%, Yameen 83% (0% without learning), Siddharth 83%
(0% without), Mateo 79%, John 75%, Kai 67%, Emma 46%, Priya 17%, **Wei 0%** (the model hears "why").

False alerts (quiet, learned): **2 on ordinary speech in 75 minutes** of name-free talk across all names
(~2–3 per hour of continuous conversation), 1 on another name, and 18 on the 150 deliberate sound-alikes
(12%), e.g. "Bolivia" for Olivia, "Grayson" for Grace, "tomato" for Mateo. Alerts fire about when the
name finishes being spoken.

Caveats: synthetic voices, not real people. The learning and test voices share the synthesizer's
pronunciation of each name, so learned-spelling gains are likely optimistic. Real accents and the
glasses mic may do better or worse. Names that sound like common words (Wei, Ray, Will, Grace in some
accents) are a known weakness. For those, choose `high` sensitivity or a nickname.

## What would improve it

1. Test with teammates' real voices in the actual room; tune `sensitivity` from that.
2. Record several different people for learned spellings.
3. For names this model can't separate from common words, a larger keyword or speech model.
4. "Trying to get your attention" beyond the name: add "excuse me" / "hey" keywords, or classifier
   rules for Shout / Yell (AudioSet labels the sound model already scores).
