# Dog label audit — October 24

The user's clip can appear in Hearing now as `Dog` or `Domestic animals, pets` without triggering
`Dog barking`. The current bark rule only accepts `Bark`, `Bow-wow` and `Yip`, at threshold 0.175.
The parent animal labels are not proof of barking; they must not be indiscriminately promoted.

## Recorded-score comparison

I re-evaluated all 1,672 stored Zipformer recording-condition cases using their actual cached
per-window arrays. Each recording-condition counts once if any window qualifies. For conjunctive
gates, both scores must occur **in the same window**; independently maximized scores cannot be
combined. No inference, recording or runtime changes were performed.

Let `B = max(Bark, Bow-wow, Yip)` and `D = Dog` for one window.

| Candidate | Tune TP / FN / FP / TN | Evaluation TP / FN / FP / TN |
| --- | --- | --- |
| Existing `B ≥ 0.175` | 96 / 0 / 1 / 903 | 63 / 1 / 0 / 608 |
| Lower bark threshold: `B ≥ 0.15` | 96 / 0 / 1 / 903 | 63 / 1 / 0 / 608 |
| Lower bark threshold: `B ≥ 0.125` | 96 / 0 / 2 / 902 | 63 / 1 / 1 / 607 |
| Broad parent: `B ≥ 0.175 OR D ≥ 0.7` | 96 / 0 / 6 / 898 | 64 / 0 / 6 / 602 |
| Guarded parent: `B ≥ 0.175 OR (D ≥ 0.7 AND B ≥ 0.08)` | 96 / 0 / 1 / 903 | 64 / 0 / 0 / 608 |

The guarded parent is the strongest minimal candidate found in this exploratory comparison.
The recovered evaluation case is `esc50-5-9032-A-0`, added white noise: one window has
`Dog = 0.72493` and `Yip = 0.09530`. The existing false-positive tuning case is a cat recording,
`esc50-1-34094-A-5`, clean. Broad parent detection adds snoring, coughing and sheep conditions on
the evaluation split; tuning also adds brushing teeth, pig, snoring and sneezing conditions.

All candidates and false-positive/missed IDs are in
[machine-readable results](../reports/dog-label-audit.json). The cache key is SHA-256 of recording
checksum + variant + `zipformer-small-int8/2024-04-15` + `32000` + `16000` + `v2-bell`, with arrays
under `.cache/benchmark/`; columns 2–4 are Bark/Bow-wow/Yip and column 5 is Dog.

## What this would do for the user's reported windows

| Dog | Bark-family maximum | Guarded candidate outcome |
| --- | --- | --- |
| 0.822 | 0.0128 | No bark cue: parent-only evidence. |
| 0.828 | 0.089 | Bark cue through guarded fallback. |
| 0.623 | 0.123 | No bark cue: neither threshold reached. |
| 0.712 | 0.17296 | Bark cue through guarded fallback. |

These values were supplied from the live log inspection, not independently captured by this audit.
If the user wants a general **Dog nearby** notification, that is a different product label and can
be an explicitly selected experimental catalog rule. `Domestic animals, pets` should remain a
separate broad concept; it includes animals other than dogs.

## Recommendation and limits

Implement the guarded fallback as an explicit optional rule clause, preserving the existing
bark-family threshold and logging whether the primary or parent-plus-child clause matched.
Do not emit parent-only evidence with a label asserting barking. Keep the actual scores in
diagnostics; a weighted/floored effective score is not a calibrated correctness probability.

The evaluation split has already been inspected, and this comparison examined several gates.
Therefore 64/64 is development evidence, not a new blind accuracy claim. Transformed cases share
source recordings. The guarded candidate still needs actual replay of the user's clip and the
demo microphone's background speech, coughs, sneezes and animal sounds before final acceptance.
It will deliberately continue rejecting strong Dog scores without any bark-family support.

Do not change all animal thresholds or suppress names to compensate for this mapping issue.

## Implementation and temporary demo override

Guarded Dog parent support is implemented in Zipformer via gated_labels with weight0.25 and
same-window Bark/Bow-wow/Yip >=0.08. Emma then explicitly requested mapping all Domestic animals,
pets to Dog barking for now. That broader alias is active in both model policies, marked TEMPORARY.
It can report cats/pets as barking, and is NOT covered by the guarded candidate's zero-FP result.
Remove that alias after the demo/testing phase before claiming dog-specific accuracy.

## Override removed — October 25

The temporary Domestic animals, pets → Dog barking alias fired repeatedly in live Pi use with no dog
present: the logged windows were a cat, a pig, a horse, chewing and room noise. Emma asked for it to be
fixed, so the alias is removed from both policies. The guarded rule above stays: bark-family labels
≥ 0.175, or Dog ≥ 0.7 with bark evidence ≥ 0.08 in the same window. samples/dog.wav still alerts.
