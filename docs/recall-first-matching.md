# Recall-first selected sound matching — October 24

Emma prefers occasional related-sound alerts over missed selected sounds. Catalog selections use
pretrained recognition immediately; teaching recordings are optional for unsupported/personal sounds.
This changes event rules and thresholds, not model weights.

## Train-horn miss

During the reported test, the decision log contained `Air horn, truck horn` at 0.353019 while the
selected train-horn group's own score was 0.000075. Earlier windows reported generic vehicle horn
at 0.545182. The old exact-only train rule used threshold 0.25 and dropped both labels.
The regression test replays those scores; it does not claim a fresh acoustic trial or save raw audio.

Train horn now accepts train horn/whistle as primary labels at 0.15, or truck/air/generic vehicle
horn as related evidence at 0.25. A related match displays **Horn — possibly train**, retains the
selected cue's priority/icon, and records the actual matched label. It does not establish a train's
identity, proximity or direction. An explicitly selected exact truck/car category takes precedence
over a related train fallback on the same evidence, avoiding duplicate subtype cues.

## Current defaults

- All 43 curated custom cue groups use primary score threshold 0.15, formerly0.25.
- The raw 527-label picker also defaults to 0.15; thresholds remain provisional and uncalibrated.
- Eleven curated groups have explicit related-label fallbacks at 0.25: the three horn groups,
  baby crying/crying, screaming/children shouting, clapping/applause, cat, bird and rain.
- Fallback labels and uncertain display wording are explicit in `audio/cue-catalog.json`.
- Existing five selected sounds were updated through the live profile API. Priorities, names,
  focus/repeat controls and unrelated profile settings were retained. Mic worker was reloaded.
- Builtin environmental detector thresholds, name matching and the bicycle gate are unchanged.
- Hearing now says **Your selected sounds**; related matches show the actual model label.

## Verification and limits

112 Python tests, 45 frontend tests and production build pass. Tests include observed horn scores
through rule → priority engine → matching display pixels, exact-category precedence, every fallback,
quiet unrelated scores and explanation transport. All 16 existing public recording spotchecks now
qualify: breaking/footsteps cross 0.15; clapping uses Applause 0.973764. These same inspected examples
were used during development, so the improved count is not independent validation or a measured
false-positive rate. Thirty-four cues still have no mapped fixture. Final room/mic trials remain.
