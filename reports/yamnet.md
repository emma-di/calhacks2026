# Offline sound benchmark — yamnet

Tuning uses source folds 1–3; held-out evaluation uses folds 4–5. Supplemental authors are assigned tune/test before inference. Related variants stay in the same split.
Evaluation recordings are held out from fitting thresholds, but results have been inspected during development; this is not a blind certification test.
Precision/recall are per recording (any qualifying window); these are not temporal localization or field reliability scores.
Public sources may overlap YAMNet pretraining. Negative sound labels are not exhaustively multi-label annotated.

Source recordings: 397. Cases including transformations: 1588.

| Condition | Event | Held-out hits / positives | Precision | False alarms / negatives | Baseline recall → tuned recall |
| --- | --- | --- | --- | --- | --- |
| clean | knock | 12/16 | 85.7% | 2/144 | 75.0% → 75.0% |
| clean | bicycle_bell | 0/2 | n/a | 0/158 | 0.0% → 0.0% |
| clean | dog_bark | 16/16 | 94.1% | 1/144 | 100.0% → 100.0% |
| clean | siren | 16/16 | 94.1% | 1/144 | 100.0% → 100.0% |
| clean | smoke_alarm | 2/2 | 100.0% | 0/158 | 100.0% → 100.0% |
| clean | alarm_clock | 16/16 | 88.9% | 2/144 | 100.0% → 100.0% |
| echo | knock | 11/16 | 84.6% | 2/144 | 68.8% → 68.8% |
| echo | bicycle_bell | 0/2 | n/a | 0/158 | 50.0% → 0.0% |
| echo | dog_bark | 15/16 | 75.0% | 5/144 | 87.5% → 93.8% |
| echo | siren | 15/16 | 83.3% | 3/144 | 93.8% → 93.8% |
| echo | smoke_alarm | 1/2 | 50.0% | 1/158 | 100.0% → 50.0% |
| echo | alarm_clock | 16/16 | 80.0% | 4/144 | 93.8% → 100.0% |
| noise10 | knock | 7/16 | 87.5% | 1/144 | 31.2% → 43.8% |
| noise10 | bicycle_bell | 0/2 | n/a | 0/158 | 0.0% → 0.0% |
| noise10 | dog_bark | 12/16 | 100.0% | 0/144 | 6.2% → 75.0% |
| noise10 | siren | 11/16 | 100.0% | 0/144 | 68.8% → 68.8% |
| noise10 | smoke_alarm | 2/2 | 100.0% | 0/158 | 100.0% → 100.0% |
| noise10 | alarm_clock | 13/16 | 81.2% | 3/144 | 68.8% → 81.2% |
| quiet | knock | 12/16 | 85.7% | 2/144 | 75.0% → 75.0% |
| quiet | bicycle_bell | 0/2 | n/a | 0/158 | 50.0% → 0.0% |
| quiet | dog_bark | 16/16 | 88.9% | 2/144 | 87.5% → 100.0% |
| quiet | siren | 14/16 | 100.0% | 0/144 | 81.2% → 87.5% |
| quiet | smoke_alarm | 1/2 | 100.0% | 0/158 | 50.0% → 50.0% |
| quiet | alarm_clock | 16/16 | 88.9% | 2/144 | 75.0% → 100.0% |

## Applied policy

```json
{
  "version": 1,
  "model": "yamnet",
  "cooldown_seconds": 5,
  "tuning": "ESC-50 folds 1\u20133 and designated supplemental authors only; false-positive rate <=1% on tuning cases",
  "rules": {
    "knock": {
      "labels": {
        "Knock": 1
      },
      "threshold": 0.15,
      "status": "tuned_on_source_split"
    },
    "bicycle_bell": {
      "labels": {
        "Bicycle bell": 1
      },
      "threshold": 0.95,
      "status": "tuned_on_source_split"
    },
    "dog_bark": {
      "labels": {
        "Bark": 1,
        "Bow-wow": 1,
        "Yip": 1
      },
      "threshold": 0.125,
      "status": "tuned_on_source_split"
    },
    "siren": {
      "labels": {
        "Siren": 1
      },
      "threshold": 0.275,
      "status": "tuned_on_source_split"
    },
    "smoke_alarm": {
      "labels": {
        "Smoke detector, smoke alarm": 1
      },
      "threshold": 0.875,
      "status": "tuned_on_source_split"
    },
    "alarm_clock": {
      "labels": {
        "Alarm clock": 1
      },
      "threshold": 0.075,
      "status": "tuned_on_source_split"
    }
  }
}
```

## Coverage gaps

- No final hardware microphone, speech/name matching, or real-room evaluation in this benchmark.
- Quiet means amplitude ×0.15; noise10 means deterministic white noise at +10 dB SNR; echo uses synthetic delayed reflections.
- These variants are robustness probes, not independent recordings or a substitute for acoustic testing.
- A false alert on a sparsely labeled clip needs listening review: a second sound may genuinely be present.

Inference median 2.03 ms; p95 2.36 ms. Excludes collection and display delay.
