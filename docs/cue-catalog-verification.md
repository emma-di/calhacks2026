# Approved 50-cue verification — October 24

## Wiring checks that pass

Run without a microphone, network receiver, profile mutation or physical display:

```sh
.venv/bin/python -m unittest discover -s tests -p test_cue_catalog_pipeline.py -v
```

Four test methods cover:

- All 50 approved cue IDs and icon IDs exist; all 50 OLED bitmaps are distinct.
- All 43 custom cue selections survive one receiver profile save, retaining their specific approved
  cue IDs and icons. Each model-label alias activates its own selected ID, and empty scores activate
  none. These are fabricated model scores, not classifier accuracy tests.
- Every environmental cue is checked at priority tiers 0–4 through saved profile → detector/custom
  rule → event validation → isolated `AlertState` receiver → presentation validation → 128×64 pixels.
  A producer's attempted tier override loses to the saved preference. Tier zero renders blank.
- Five tier cases for the speech-worker `name_called` event validate the separate name route and its
  specific approved icon. These events are synthetic and do not exercise speech recognition.
- Bicycle-specific recognition remains disabled at all five tiers. The icon's existence does not
  claim that this subtype has been validated.

That is 250 cue/tier combinations: 245 supported cue/tier wiring checks and five intentional
bicycle rejections. Built-ins use their existing detector and canonical labels; custom selections
use `cue_id` and `custom_sound_id`. Receiver HTTP transport is covered by the existing HTTP suite;
these tests call the actual receiver state directly and do not open a listening socket.

## Actual recorded classifier spot-checks

```sh
.venv/bin/python scripts/verify_cue_recordings.py --report reports/cue-recording-spotchecks.json
```

The script loads the real pretrained Zipformer and existing public WAVs. It downloads nothing,
records nothing, and changes no live receiver or profile. One available held-out source is tested
per mapped cue, using the normal window size and hop. Results, source IDs/checksums and peak scores
are in [the report](../reports/cue-recording-spotchecks.json).

**13 of 16 recorded spot-checks qualify** under current built-in or provisional catalog thresholds.

| Cue | Highest selected-label score | Result |
| --- | --- | --- |
| Baby cry | 0.8763 | Qualifies |
| Car horn | 0.8802 | Qualifies |
| Cat meow | 0.6781 | Qualifies |
| Rain | 0.5127 | Qualifies |
| Thunder | 0.8469 | Qualifies |
| Wind | 0.3389 | Qualifies |
| Drip | 0.6786 | Qualifies |
| Train | 0.9650 | Qualifies |
| Laughter | 0.9372 | Qualifies |
| Siren, knock, dog bark, alarm clock | See report | Qualify under built-in policies |
| Breaking | 0.1976 | Misses provisional 0.25 threshold |
| Clapping | 0.0419 | Misses provisional 0.25 threshold |
| Footsteps | 0.2042 | Misses provisional 0.25 threshold |

This small, inspected sample is **not an accuracy benchmark** and provides no false-positive rate.
Do not lower thresholds from one missed clip alone: evaluate more independent positives and
negative sounds before changing a default. Thirty-four catalog cues have no mapped fixture in this
script, including saxophone; names require the separate speech evaluation. The existing synthetic
name report and environmental benchmark remain useful but measure different tasks.

Custom spot-check results compare actual model label scores with the catalog rule threshold; the
synthetic wiring suite separately verifies that qualifying custom scores reach a receiver and frame.
The recorded script does not upload its scores/events to the running demo receiver.

## Still required before calling recognition accurate

Independent positives and hard negatives for each intended demo sound; final microphone/room
trials; real-voice name checks; overlapping/repeated cues; full acoustic-onset-to-display latency;
and physical OLED readability/orientation once the Pi returns. A 50-cue icon gallery and passing
synthetic wiring do not establish 50-sound recognition accuracy.
