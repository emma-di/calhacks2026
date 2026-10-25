# Team build instructions — distilled handoff

Source: Emma's additional team handoff and workstream screenshot, October 23, 2026.
This is a reconciled builder summary. Recommendations in the source are proposals, not evidence
that integrations exist. Use the [master TODO](../TODO.md) for completion status and the
[sponsor guide](sponsor-build-guide.md) for candidate evaluations.

## TLDR: preserve the working vertical slice

Build independently with fake events, then connect real recognition to the same alert path.
Emma builds the browser mirror/companion first, then backend integration. Yameen builds the
physical output. John and Leo are proposed for environmental/name recognition and spatial audio.
Spatial experiments must not delay basic sound classification and name recognition.

One canonical active alert drives the audience mirror and glasses. User preferences affect the
deterministic notification engine, not model training. Do not add sponsor dependencies to urgent
alert handling unless their necessity and failure behavior are proven.

## Workstreams from the supplied assignment

| Owner | Responsibility | First evidence |
| --- | --- | --- |
| Yameen | Display, optics, mounting, microphone capture interface, device connection | Fake cue physically displayed; capture/transport specifications documented |
| John and Leo — proposed | Environmental recognition, name detection, thresholds and false-positive testing | Real input emits validated events, with misses and negatives recorded |
| Emma | UI/UX, then backend/schema, preferences, alert state and hardware bridge coordination | Polished mirror handles mock then recorded events; settings change actual behavior |
| John and Leo — proposed | Synchronized capture/geometry, direction estimation and confidence | Known-angle test with measured error, or explicit unknown direction |

The screenshot labels assignments proposed. John and Leo should agree how they divide audio/name
and spatial work; do not infer a person-to-GitHub-username mapping from these names alone.

## Reconcile the handoff with code already in this repo

- **Model:** Zipformer Small INT8 is the current default. YAMNet is a comparison baseline.
  Do not restart model selection merely because the source handoff suggests starting with YAMNet.
- **Schemas:** keep `schema_version` and `event_id` from the [integration contract](integration.md).
  The source handoff's `id` example is illustrative; it is not a replacement schema.
- **Confidence:** current classifier scores are uncalibrated, not probabilities of correctness.
  Keep recognition confidence separate from notification priority and direction confidence.
- **Events:** prioritize knock, dog bark, generic bell, alarms and planned `name_called`.
  Bicycle-specific labeling remains disabled pending evidence; a fake “Bicycle bell” hardware cue
  does not establish that the classifier recognizes that subtype.
- **Folders:** keep the existing Python package runnable. The source's `core/`, `web/`, `glasses/`
  and `convex/` tree is a proposal; add directories only when implementing those modules.
- **Cloud state:** Convex is the new preferred candidate from the handoff, not an installed backend.
  Evaluate it versus SpacetimeDB and choose at most one equivalent cloud synchronization system.
- **Speech:** Cartesia is a candidate provider; the local speech plan remains a fallback. Both
  consume shared capture and emit the same planned name event. No second independent mic owner.
- **Cue lifetimes:** tier 4 currently expires after at most 30 seconds. “Persistent” in a design
  note does not silently change that behavior. Review lifetime and acknowledgement together.

## Implementation instructions worth keeping

1. Freeze the event/profile contracts before wiring independent modules. Classifiers provide
   detections; backend defaults and preferences determine effective tier. Coordinate schema changes.
2. Feed synchronized channels to spatial processing; feed normalized mono to classification.
   Independent unsynchronized streams do not satisfy the localization input requirement.
3. Hardware accepts replacement, clear and expiry, not just draw commands. Verify near-eye optics,
   not merely whether text looks readable on a screen sitting on a desk.
4. Profile saves must change the running engine without restarting audio. If a cloud profile layer
   is adopted, use revisions and keep the last applied local profile during outages. Show sync status.
5. Store event summaries only as needed; never send raw audio to the state database. Cartesia speech
   transport is a separate, explicit provider decision. Keep credentials out of source and browser code.
6. Names mean a configured token/alias was heard, not speaker identity or proof someone addressed
   the wearer. Hide unreliable direction; do not invent precise distance.
7. Build ordinary editable settings first. Optional Claude interpretation proposes settings for user
   confirmation; validate mappings to real event keys (`knock`, not an unimplemented `door_knock`).
8. Keep mock/replay/live visibly distinct. A hosted demo needs an explicit supported connection to
   the live laptop session; publishing a page alone does not connect the microphone or glasses.

## Demo and submission runbook

The source handoff states **Sunday, October 25, 2026, 9:00 AM PDT** as the deadline.
Treat this as a supplied planning target until confirmed against the official submission page.
Proposed internal cutoff: **8:00 AM PDT**, leaving one hour for upload/access problems.

- First integration: mock alerts on browser and hardware independently, then one actual sound
  through the existing pipeline. Do not wait for every feature before integrating.
- Saturday vertical slice: configure name → speak it → name event → tier-3 cue → clear. Keep the
  environmental demo operational if speech is still unavailable; no new sponsor APIs during integration.
- Robustness: test changed priorities, competing alerts, repetition, negatives, restart and reconnect.
- Spatial: integrate only after synchronized capture and known-angle testing; otherwise omit arrows.
- Before submission: freeze features, measure end-to-end latency, film a backup, capture project
  images, finish setup/sponsor notes, check public demo links signed out, and rehearse the pitch.

Suggested three-minute story: accessibility need → optional typed setup → live name cue → knock/bell
cue → change a preference and repeat → explain only the technologies that actually run.
Use reliable measured direction if available; never make it a prerequisite for telling the story.

## Acceptance evidence

Record hits, misses, false alerts and sound-to-display delay. Include a matching name, nonmatching
name, environmental sound, higher-tier interruption, repeated sound, settings change, real physical
output, restart and network interruption. Test local fallback rather than merely describing it.
Final materials: README, repository, image, live/recorded demo, short pitch and verified track links.
If the core demo is broken, stop optional sponsor, distance, gesture and elaborate animation work.
