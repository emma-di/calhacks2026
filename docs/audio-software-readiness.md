# Audio software readiness — October 24

This audit separates implemented wiring from recognition accuracy. It reads the current code and
checked-in measured reports; it does not start capture, change a running worker, or claim a fresh
room test. Inference stays on the Mac. Only the display client, renderer and assets go on the Pi.

## Already implemented

- Environmental classification: pretrained Zipformer Small INT8, 16 kHz mono, 2-second windows
  every second; recording, simulation and microphone inputs remain distinguishable.
- Streaming name keyword spotting shares the microphone's 0.2-second blocks. Typed names, aliases,
  optional learned spellings, sensitivity, profile reload and name decision diagnostics exist.
- Environmental events and name events reach the common receiver, priority engine and pixel renderer.
  Observations explain low scores, cooldowns and emitted detections separately from display decisions.
- Fire alarm and Smoke detector, smoke alarm both map to the urgent fire/smoke cue. Generic Alarm
  and Alarm clock do not independently qualify as fire. Four seconds of fresh negative evidence can
  clear the cue; missing capture is not quiet evidence.
- Show every detection is available for testing. Snap dismissal is deliberately off; manual Dismiss
  and optional camera thumbs-up remain. Snap tuning is not a remaining demo requirement.
- Taught custom-sound infrastructure is integrated. The optional embedding dependencies must be
  present on the processing Mac; its fallback must not silently imply custom recognition is active.
- The 527-label pretrained catalog and `audio/custom_rules.py` exist. At the start of this audit,
  selecting catalog sounds through Preferences was still unfinished; inspect the current branch
  because that wiring is being completed separately.

## Implemented since this audit began

The 527-label picker, normalized recognized profiles, hot-reloaded catalog rules, per-ID priorities
(including Ignore0), and category OLED icons are now connected. Recorded Whistling produced4 events,
max score0.9125, person icon/tier3 in an isolated receiver. Mana's generated profile adapter also
passed real Python integration for Rain/drop/tier3. These are wiring checks, not527 validated sounds.
The optional ONNX/embedding dependencies are now installed on Emma's Mac and produce score outputs
identical to the original path on the checked sample (max difference0.0).

Dog-specific guarded parent fallback is implemented from same-window analysis; however Emma then
explicitly requested a broader TEMPORARY Domestic animals,pets → Dog barking mapping. That demo
mapping is active in both policies and can label cats/pets as dogs. Do not apply the guarded-rule
zero-false-positive result to the broader override. Snap remains parked.

## Remaining acceptance work, in order

| Priority | Deliverable | Acceptance evidence |
| --- | --- | --- |
| Done wiring; P0 accuracy | Validate chosen catalog sounds in the demo room. | Pick a model-known sound, replay a positive, see the chosen label/icon/tier; edit/delete it while the worker runs; two custom IDs remain independent. Default thresholds are experimental, not 527 independently validated detectors. |
| P0 | Check names with the demo voices and microphone. | Name alone and in sentences, repeated calls, similar names, background conversation, silence and alarms; record hits/misses and false alerts per negative minute. Verify onboarding saves preserve learned spellings and changed names stop matching the old target. |
| P0 | Tune the final microphone in the final room. | Replay or perform knocks, bells, barking, clocks and fire alarms plus background negatives; separate raw recognition, recognizer cooldown, display policy and actual cue. Measure acoustic-onset-to-screen latency, not only HTTP/OLED transport. |
| P0 | Reproduce on the processing Mac. | Fresh audio dependency install, model download/warmup, saved profile, name recognition, and opt-in capture device selection. An empty custom model bank should leave environmental/name recognition working. |
| P1 | Close the doorbell-label gap without inventing confidence. | `Doorbell` and `Ding-dong` are known model classes but are absent from the current generic bell rule. Obtain/replay independent doorbell positives and alarm/clock negatives before choosing their threshold. |
| P1 | Finish phone spatial calibration and sound association. | Airborne sounds on all four sides, known phone orientation, measured angular error, stale/missing readings, background-source rejection and timing association. Sixteen rendered arrow positions are not evidence of sixteen-direction accuracy. |
| P2 | Expand additional default sounds only if time and evidence justify it. | Baby cry, car horn, ringing telephone and appliance signals can first use explicit catalog choices; promote a built-in default only after a labeled positive/negative evaluation and shared UI/policy/icon updates. |

No new backbone training is justified by the current wiring gaps. Existing pretrained classes,
rule calibration and name-spelling evaluation should come first. Taught custom heads are a separate
optional feature for sounds outside the pretrained list.

## What the recorded evidence actually supports

[Environmental report](../reports/summary.md): 418 source recordings, 1,672 transformed cases;
transforms of the same recording are not independent examples. Clean evaluation positives:
dog 16/16, knock 15/16, siren 16/16, clock 15/16, smoke 7/7, generic bell 7/7.
The old report's statements that speech, profiles and hardware are unimplemented are historical and
superseded by current code and the handoffs. Do not rerun the benchmark's policy-writing tuning
command blindly over newer fire-alias rules.

[Fire alias review](../reports/fire-alarm-alias-review.json) reuses cached model scores; it is not
a fresh recording trial. On Zipformer's 672 test recording-condition cases, adding `Fire alarm`
keeps 27 true positives and one miss while false positives rise from zero to two. Those cases are
noisy crickets (`esc50-5-204352-A-13`, fire score 0.762) and an alarm clock
(`esc50-5-210612-A-37`, score 0.507). The existing positive set is smoke-oriented, so unchanged
recall does not measure coverage of independent fire-alarm recordings. Retain the requested alias,
collect the user's fire clip and hard negatives, then tune from source-separated data. Raising a
threshold or requiring two windows now could hide true fire alarms or brief events.

[Name results](../reports/name-detection.json) are explicitly synthetic. Balanced sensitivity with
learned spellings reports 62.5% recall in quiet and 55.4% with 10 dB noise; Emma alone is 46%/42%.
Quiet false alerts total 22 across that evaluation, including 18 on sound-alikes. The report's
approximately 2–3 false alerts/hour refers to generic name-free speech, not all negative speech.
These figures do not establish accuracy on real voices. Higher sensitivity offers only a small
aggregate synthetic recall increase and adds false alerts; it is not a demonstrated universal fix.

[Custom-head results](../reports/custom-sounds.json) evaluate few-shot frozen-embedding classifiers
on ESC-50. They do not validate a generic 0.25 threshold for all pretrained catalog classes or the
user's actual few recorded examples.

Cached `reports/zipformer-cases.json` contains only 16 selected model labels. It has no `Doorbell`,
`Ding-dong`, baby-cry or horn scores, even when corresponding background recordings exist. Therefore
those cached scores cannot establish thresholds for the missing classes. Full-score inference on
existing labeled recordings can supply new evidence without recording a microphone or training a model.

## Spatial and physical checks deliberately awaiting devices

The [phone handoff](phone-spatial-handoff.md) records verified four-channel FOA capture and USB
transport. It also records empty calibration, mirrored/uneven raw angles, background-source lock-on,
3-second receive-time matching between two microphones, and a 3-minute native listening cap.
These need device evidence; synthetic renderer tests cannot close them. Prefer the same phone's
audio and direction for association if that transport is completed, otherwise reject uncertain or
stale direction rather than making a classification appear spatially certain.

When the Pi returns: deploy only the audited display files, verify physical icon/arrow orientation,
check optical readability, disconnect recovery and sound-to-pixels latency. A receiver connection
alone does not verify physical pixels. Until then, prerecorded audio → receiver → browser/PBM
renderer is the reproducible software integration path.

## Minimal rule recommendations

1. Keep the fire/smoke alias, current threshold and generic-alarm exclusion while collecting fire
   positives; retain the existing explicit false-positive report.
2. Add doorbell aliases only together with positive/negative replay evidence and a regression test;
   do not assume the generic Bell threshold transfers to other model outputs.
3. Avoid a blanket two-consecutive-window gate: a brief knock/name/bell can legitimately occupy
   only one window. Use per-class temporal behavior only after testing short positives.
4. Keep bicycle subtype disabled and snap parked. Do not expand urgency to arbitrary Alarm/Buzzer
   labels; the catalog can expose experimental opt-in classes without promoting them to fire alerts.
