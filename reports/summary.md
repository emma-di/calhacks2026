# Current audio validation — 2026-10-23

Default: Zipformer Small INT8; 2-second windows, 1-second hops.
Round 2: **418 source recordings, 1,672 clean/quiet/noisy/echo cases**. Added 21 reviewed public recordings: 14 bicycle bells and 7 smoke alarms.
Source/author splits were fixed before inference. Thresholds use the tuning split; evaluation results have been inspected during development. Public audio may overlap pretraining.

## A — Bell and alarm improvements

The table compares old and new policies on the **same expanded evaluation set**. Quiet/noisy/echo variants are not independent recordings.

| Bell condition | Old hits / positives | New hits / positives | Old false alerts | New false alerts |
| --- | --- | --- | --- | --- |
| clean | 7/7 | 7/7 | 3 | 3 |
| quiet | 5/7 | 7/7 | 3 | 2 |
| noise10 | 4/7 | 6/7 | 2 | 2 |
| echo | 7/7 | 7/7 | 5 | 0 |

The generic bell rule now includes Bell, Ding and Chime. Recognition of an alarm clock, smoke alarm, or siren suppresses the generic bell cue for four seconds after that context is last recognized. This avoids a fading alarm being presented as a second sound. It can also suppress a genuine new bell within that interval; the log retains the triggering context for review.

Smoke alarms: **7/7** evaluation recordings detected in clean, added noise, and echo; **6/7** in quiet. No smoke-alarm false alerts in these evaluation cases. There are 11 smoke recordings total, including two perspectives by one tuning author, so evidence is still limited.

Specific bicycle identification stays disabled. Generic Bell / chime is the deployed cue; clean bell detection remains 7/7 with 3 apparent false alerts, so it is still experimental. Barking, knock, and siren rules were frozen during this tuning pass.

## Current clean and added-noise results

| Cue | Clean hits / positives | Noise hits / positives | Clean false alerts / negatives |
| --- | --- | --- | --- |
| dog_bark | 16/16 | 15/16 | 0/152 |
| knock | 15/16 | 13/16 | 1/152 |
| siren | 16/16 | 16/16 | 0/152 |
| alarm_clock | 15/16 | 13/16 | 1/152 |
| smoke_alarm | 7/7 | 7/7 | 0/161 |
| bell | 7/7 | 6/7 | 3/161 |

## Decision logs

- `.cache/recognition-decisions.jsonl`: window scores, thresholds, emitted/cooldown/disabled/suppressed reason, recent context, and HTTP delivery result. Session headers record the policy used.
- `.cache/alert-decisions.jsonl`: displayed/ignored/lower-priority alert decisions. The receiver also returns recent decisions from `GET /state`.
- Each log rotates at 5 MB with two backups. Logs contain event metadata and scores; no raw audio or full transcripts.
- [Real alarm-clock regression log](alarm-context-log-example.json): bell score 0.269 exceeded threshold 0.075, but an alarm clock recognized one second earlier suppressed the cue.

## Evidence and reproduction

- [Detailed current benchmark, policies, precision and missed/false IDs](zipformer.md)
- [Exact 418-recording source manifest, attribution, splits and checksums](dataset-manifest.json)
- [Round 1 policy](round1-policy.json) and [original 397-recording manifest](dataset-manifest-round1.json)
- [Actual-model sequence/overlap/repeat/silence scenarios](zipformer-scenarios.json)
- [Historical YAMNet comparison on the original set](yamnet.md); YAMNet was not rerun on the added recordings.

```sh
.venv/bin/python -m audio.prepare_benchmark --from-manifest reports/dataset-manifest-round1.json --extension audio/fixtures-round2.json
.venv/bin/python -m audio.benchmark --model zipformer --baseline-policy reports/round1-policy.json --tune-only bell bicycle_bell smoke_alarm alarm_clock
.venv/bin/python -m audio.simulate
.venv/bin/python -m unittest discover -s tests -v
```

## B and C

[B: Name-detection plan and onboarding contract](../docs/name-detection-plan.md) is prepared; speech recognition is not implemented.
C: Hardware adapter implementation awaits the supplied hardware stack. No microphone or glasses were used for this offline pass.
