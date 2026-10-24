# Offline sound benchmark — zipformer

Tuning uses source folds 1–3; held-out evaluation uses folds 4–5. Supplemental authors are assigned tune/test before inference. Related variants stay in the same split.
Evaluation recordings are held out from fitting thresholds, but results have been inspected during development; this is not a blind certification test.
Precision/recall are per recording (any qualifying window); these are not temporal localization or field reliability scores.
Public sources may overlap YAMNet pretraining. Negative sound labels are not exhaustively multi-label annotated.

Source recordings: 418. Cases including transformations: 1672.

| Condition | Event | Held-out hits / positives | Precision | False alarms / negatives | Baseline recall → tuned recall |
| --- | --- | --- | --- | --- | --- |
| clean | knock | 15/16 | 93.8% | 1/152 | 87.5% → 93.8% |
| clean | bicycle_bell | 0/5 | n/a | 0/163 | 60.0% → 0.0% |
| clean | dog_bark | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| clean | siren | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| clean | smoke_alarm | 7/7 | 100.0% | 0/161 | 100.0% → 100.0% |
| clean | alarm_clock | 15/16 | 93.8% | 1/152 | 93.8% → 93.8% |
| clean | bell | 7/7 | 70.0% | 3/161 | 100.0% → 100.0% |
| echo | knock | 14/16 | 87.5% | 2/152 | 87.5% → 87.5% |
| echo | bicycle_bell | 0/5 | n/a | 0/163 | 40.0% → 0.0% |
| echo | dog_bark | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| echo | siren | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| echo | smoke_alarm | 7/7 | 100.0% | 0/161 | 100.0% → 100.0% |
| echo | alarm_clock | 16/16 | 88.9% | 2/152 | 93.8% → 100.0% |
| echo | bell | 7/7 | 100.0% | 0/161 | 100.0% → 100.0% |
| noise10 | knock | 13/16 | 92.9% | 1/152 | 62.5% → 81.2% |
| noise10 | bicycle_bell | 0/5 | n/a | 0/163 | 20.0% → 0.0% |
| noise10 | dog_bark | 15/16 | 100.0% | 0/152 | 31.2% → 93.8% |
| noise10 | siren | 16/16 | 100.0% | 0/152 | 93.8% → 100.0% |
| noise10 | smoke_alarm | 7/7 | 100.0% | 0/161 | 100.0% → 100.0% |
| noise10 | alarm_clock | 13/16 | 92.9% | 1/152 | 43.8% → 81.2% |
| noise10 | bell | 6/7 | 75.0% | 2/161 | 57.1% → 85.7% |
| quiet | knock | 15/16 | 93.8% | 1/152 | 93.8% → 93.8% |
| quiet | bicycle_bell | 0/5 | n/a | 0/163 | 20.0% → 0.0% |
| quiet | dog_bark | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| quiet | siren | 16/16 | 100.0% | 0/152 | 100.0% → 100.0% |
| quiet | smoke_alarm | 6/7 | 100.0% | 0/161 | 85.7% → 85.7% |
| quiet | alarm_clock | 15/16 | 93.8% | 1/152 | 87.5% → 93.8% |
| quiet | bell | 7/7 | 77.8% | 2/161 | 85.7% → 100.0% |

## Applied policy

```json
{
  "version": 1,
  "model": "zipformer",
  "cooldown_seconds": 5,
  "tuning": "ESC-50 folds 1\u20133 and designated supplemental authors only; false-positive rate <=1% on tuning cases",
  "rules": {
    "knock": {
      "labels": {
        "Knock": 1
      },
      "threshold": 0.075,
      "status": "tuned_on_source_split"
    },
    "bicycle_bell": {
      "labels": {
        "Bicycle bell": 1
      },
      "threshold": 0.05,
      "status": "disabled_source_specificity_unvalidated",
      "enabled": false
    },
    "dog_bark": {
      "labels": {
        "Bark": 1,
        "Bow-wow": 1,
        "Yip": 1
      },
      "threshold": 0.175,
      "status": "tuned_on_source_split"
    },
    "siren": {
      "labels": {
        "Siren": 1
      },
      "threshold": 0.225,
      "status": "tuned_on_source_split"
    },
    "smoke_alarm": {
      "labels": {
        "Smoke detector, smoke alarm": 1
      },
      "threshold": 0.35,
      "status": "provisional_small_sample"
    },
    "alarm_clock": {
      "labels": {
        "Alarm clock": 1
      },
      "threshold": 0.05,
      "status": "tuned_on_source_split"
    },
    "bell": {
      "labels": {
        "Bell": 1,
        "Ding": 1,
        "Chime": 1
      },
      "suppressors": {
        "Alarm clock": 0.05,
        "Smoke detector, smoke alarm": 0.35,
        "Siren": 0.225
      },
      "suppressor_hold_seconds": 4,
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

Inference median 13.90 ms; p95 30.79 ms. Excludes collection and display delay.
