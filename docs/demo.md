# Spidey Sense · sound, made visible

Half of deaf and hard-of-hearing people in one study missed an important sound daily. Spidey Sense
glasses show what you missed and where: alarms, knocks, even someone calling your name.

Two microphones on the glasses hear the room, a laptop recognizes the sound, and a small display at
the edge of your vision shows an icon, how urgent it is, and which side it came from. The companion
website (labeled **Aware**) shows the same cue, the full transcript of questions, and your settings.

**Sound → glasses mics → laptop recognition → priority rules → glasses display + website**

**Try it in your browser:** https://emma-di.github.io/calhacks2026/ (test sounds, no install). Live
microphones run on a laptop: see [Try it on your laptop](#try-it-on-your-laptop).

## What to look for in the demo

- **Any important sound, as an icon with an arrow.** Smoke alarm, siren, door knock, doorbell, dog,
  baby crying and 500+ more the model knows. Urgent sounds interrupt; quieter ones wait their turn.
- **Your name, and the question after it.** Say "Hey Emma, are you coming to lunch?" The glasses
  show *Your name* with an arrow, then *Are you coming to lunch?* The full sentence stays on the site.
- **"Hey", "excuse me", "watch out".** Attention calls show *Someone's calling*; "watch out" and
  "look out" are urgent.
- **Pick any sound in your own words.** Type "my kettle" in setup, ask Claude, approve a match, and it
  alerts as *my kettle*.
- **Focus modes.** Everyday, Work (only name and urgent) and Do not disturb (urgent only).

## Two-minute demo script

1. Open the site → **Preferences**: enter a name (step 1), show the alerts already set up (step 2),
   type "my kettle" → **Ask Claude** → pick a match (step 3) → **Start Aware**.
2. **Live** view: play a smoke alarm or knock near the glasses. The cue and its side arrow appear on
   the glasses and the site; tap **Dismiss** (or thumbs up to the camera) to resolve it.
3. From one side, say "Hey Emma, do you know where the charger is?" Watch *Your name* become the
   question, with the transcript under **Heard**.
4. Switch to **Do not disturb**: a knock is held back, a smoke alarm still comes through.

## Try it on your laptop

### A. Website only (no microphone, no Python) — 1 minute

Needs Node 22.12+.

```sh
npm ci --prefix frontend
npm run dev --prefix frontend
```

Open http://127.0.0.1:5173 and choose **Browser**. Tap test sounds to see exactly what the glasses
would show, including the 128×64 display preview and simulated directions.

### B. Live recognition with your laptop microphone — about 10 minutes

Needs Python 3.12 (Apple Silicon macOS tested). Models download once into `.cache/` (a few hundred MB).

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-audio.txt
.venv/bin/python -m audio.download_model --names --speech
```

Then, in three terminals:

```sh
.venv/bin/python -m audio.server
```

```sh
.venv/bin/python -m audio.cli devices
```

```sh
.venv/bin/python -m audio.cli mic --device <index> --endpoint http://127.0.0.1:8765/events
```

Pick your microphone's index from `devices`; macOS will ask for microphone permission. Start the site
(step A) and choose **Receiver**. A laptop microphone is mono, so cues have no direction arrow;
direction needs the glasses' two microphones. Raw audio is never saved.

**Claude features (optional):** in Preferences → step 3 → *Tell us about you*, connect an Anthropic
API key. It stays in the receiver's memory only and clears when the receiver stops.

### C. The glasses (Raspberry Pi Zero W + two INMP441 mics + SSD1306 OLED)

`scripts/glasses_up.sh` deploys the display client to the Pi; run recognition with
`audio.cli mic --pi pi@glasses-pi.local`. Step-by-step: [glasses checklist](glasses-checklist.md),
[Pi stereo direction](pi-spatial-live.md).

### Repeatable demo microphone controls

Use `.venv/bin/python scripts/recognizer.py pi` to start Pi input in the background;
`status`, `stop`, `devices` and `mac --device INDEX` handle the rest without duplicate workers.
This controller defaults to the current demo receiver on8766. A fresh receiver defaults to8765;
pass `--endpoint http://127.0.0.1:8765/events` in that case.
See [recognizer controls and reflected OLED testing](recognizer-controls.md).

## Where AI is used

| What | Model | Runs | Why |
| --- | --- | --- | --- |
| Sound recognition | Zipformer audio tagging (527 sounds) | Laptop, offline | Detect alarms, knocks, voices… every second |
| Name and attention calls | sherpa-onnx keyword spotter | Laptop, offline | Your name, "hey", "excuse me", "watch out" |
| Question after your name | Moonshine tiny speech-to-text | Laptop, offline | Only the few seconds after your name; never saved |
| Match "my kettle" to a known sound | Claude Haiku 4.5 | Anthropic API, opt-in | People describe sounds in their own words; you approve every match |
| Shorten a question for the display | Claude Haiku 4.5 | Anthropic API, opt-in | Fits 4 short lines; the full sentence stays on the site |
| Suggest sounds from your routine | Claude Haiku 4.5 | Anthropic API, opt-in | Suggestions only; nothing changes until you apply |
| Setup page and preference-saving code | Mana | Build time | See [Mana onboarding](mana-onboarding.md) and `frontend/mana/provenance.json` |

Safety-critical parts (detection, priority, display) stay local and deterministic. Claude only ever
receives text you typed or a transcribed question, never audio.

## Honest limits

- An awareness aid, not a certified emergency alert system. It can miss sounds or raise false alerts.
- Direction is left/right/diagonal from two mics about 12 cm apart; front is assumed when unclear and
  behind cannot be measured. See [direction limits](rough-front-angles.md).
- Name spotting and questions were tuned on synthetic voices and short live tests; real noisy rooms
  need more testing. Bicycle-bell detection is disabled pending evidence.
- Measured recognition results: [reports/summary.md](../reports/summary.md).

## Repo map

| Location | Purpose |
| --- | --- |
| `frontend/` | Companion website: Live view, Preferences (Mana-built setup), Log, OLED preview |
| `audio/server.py`, `audio/alerts.py` | Receiver and the alert engine (priority, focus modes, dismiss) |
| `audio/cli.py`, `audio/model.py` | Microphone/recording capture and sound recognition |
| `audio/names.py`, `audio/questions.py` | Name/attention spotting and question transcription |
| `audio/pi_spatial.py`, `audio/pi_input.py` | Pi stereo capture and direction |
| `audio/sound_match.py`, `audio/setup_suggestions.py`, `audio/question_paraphrase.py` | Claude features |
| `hardware/` | OLED renderer, icons and the Pi display client |
| `tests/` | Python checks (no weights or microphone needed); frontend tests run with `npm test --prefix frontend` |

Team docs: [work status](../WORK-STATUS.md) · [team notes](../TEAM-NOTES.md) · [design decisions](design-decisions.md)
· [event contract](integration.md) · [alert engine](alert-engine.md) · [contributing](../CONTRIBUTING.md)
· coding agents start at [AGENTS.md](../AGENTS.md).

**Never commit model weights, recordings, logs, environments or credentials.**
