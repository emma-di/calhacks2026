# Project TODO

Single project checklist. Update IDs and evidence in every relevant PR. Checked means implemented
or verified as stated; unchecked means pending. This list covers the whole product, not just the UI.
See the [UI → backend plan](docs/ui-ux-backend-plan.md) for sequencing and proposed contracts.

## Verified foundation

- [x] BASE-01 — Pretrained environmental model, normalized events, file/microphone capture paths.
- [x] BASE-02 — Recorded sound → inference → JSON → existing laptop monitor exercised.
- [x] BASE-03 — Python-only fake-event generator, receiver, basic priority and dismiss.
- [x] BASE-04 — Offline evaluation: 418 recordings / 1,672 transformed cases; [results](reports/summary.md).
- [x] BASE-05 — Recognition and display decision logs, including bell/alarm context reasons.
- [x] TEAM-01 — GitHub repo, branch guidance, Python CI and [handoffs](docs/team-workstreams.md).

These checks do not establish final-room accuracy, physical display integration, fine-tuned weights,
name recognition, or a polished UI. None of those should be presented as completed.

## First: browser mirror and cue design — Emma

Before selecting the frontend builder, complete SPONSOR-02 below. The mirror work remains the first product milestone.

- [ ] UI-01 — Scaffold frontend; lock dependencies; establish visual tokens and accessible controls.
- [ ] UI-02 — Build shared browser HUD with all five tiers (0 hidden), short labels and icon mapping.
- [ ] UI-03 — Build fullscreen audience mirror and companion preview of the same session.
- [ ] UI-04 — Add deterministic mock scenarios: all tiers, interruption, repeated/long labels, idle,
  paused, unknown direction, disconnection and reconnect. Label simulated inputs.
- [ ] UI-05 — Connect existing receiver and dismiss API; show a real recorded event in the polished UI.
- [ ] UI-06 — Review contrast, keyboard access, reduced motion, responsive layout and audience-distance readability.
- [ ] UI-07 — Add recent alerts and separate diagnostics; keep raw scores/JSON out of the mirror.
- [ ] UI-08 — Capture screenshots and short demo evidence for teammate review.

## Then: setup and preferences — Emma

- [ ] SET-01 — Confirm profile fields, mode defaults versus explicit overrides, and sound enable/disable semantics.
- [ ] SET-02 — Design/build optional typed name + aliases, sound preferences and cue previews.
- [ ] SET-03 — Support editable settings and clear draft/saved/applied/error states.
- [ ] SET-04 — Connect saved profile to backend; show name worker availability accurately.

## Backend/integration — Emma after initial UI

- [ ] API-01 — Agree versioned output state and backward-compatible event/profile contracts with teammates.
- [ ] API-02 — Implement profile validation, revision handling and atomic local persistence.
- [ ] API-03 — Compute effective priority from defaults, mode and user overrides in one backend location.
- [ ] API-04 — Add event deduplication, bounded fresh queue, interruption/resume and repeated-sound behavior.
- [ ] API-05 — Add sequence/freshness/expiry state and event-specific dismiss; prevent stale cue replay.
- [ ] API-06 — Add capture/inference/display health and capabilities; silence must not imply disconnection.
- [ ] API-07 — Implement real pause/resume and visible acknowledgement; do not fake worker controls.
- [ ] API-08 — Verify mirror/hardware state alignment, timeout clearing and reconnect snapshots.
- [ ] API-09 — Test full settings → detected event → effective tier → mirrored cue flow.

## Environmental audio / ML — owner to confirm

- [ ] ML-01 — Confirm workstream owner and preserve benchmark/tuning versus evaluation separation.
- [ ] ML-02 — Evaluate final microphone in final room: knocks, barking, generic bells, alarms and negatives.
- [ ] ML-03 — Investigate bell versus alarm confusions using scores, context and decision logs.
- [ ] ML-04 — Measure misses, false alerts and complete sound-to-screen latency; tune rules from evidence.
- [ ] ML-05 — Keep bicycle-specific labeling disabled until supported by independent evidence.
- [ ] ML-06 — Consider training only if measured remaining errors justify it; no per-user model training for settings.

## Name recognition — owner to confirm

- [ ] NAME-01 — Implement shared capture fanout and bounded worker queues; avoid opening the mic twice.
- [ ] NAME-02 — Benchmark the speech model and VAD on target compute before choosing the final configuration.
- [ ] NAME-03 — Implement typed-name/alias matching, utterance deduplication and stale-profile protection.
- [ ] NAME-04 — Coordinate nullable-confidence event support with receiver and frontend.
- [ ] NAME-05 — Test uncommon names, similar-sounding negatives, background conversation and repeated mentions.
- [ ] NAME-06 — Demonstrate configured name → “Your name” cue; log evidence without storing raw speech by default.

## Hardware and display — Yameen; stack pending

- [ ] HW-01 — Supply compute/OS, controller, display/driver/resolution, transports and controls.
- [ ] HW-02 — Supply audio interface, sample rate, channel count/order and synchronization capability.
- [ ] HW-03 — Display a fake cue on actual hardware independently of recognition.
- [ ] HW-04 — Implement device renderer for agreed icon IDs, labels, tiers, clear and expiry.
- [ ] HW-05 — Connect authoritative backend state; compare event IDs with audience mirror.
- [ ] HW-06 — Validate optical readability, refresh, mounting, power and reconnect/clear behavior.
- [ ] HW-07 — Feed final audio device into capture adapter and complete the physical end-to-end demo.

## Spatial audio — owner to confirm; synchronized capture gate

- [ ] SPACE-01 — Prove synchronized multichannel capture and document microphone geometry.
- [ ] SPACE-02 — Prototype GCC-PHAT with known-angle recordings and measure error/confidence.
- [ ] SPACE-03 — Agree direction coordinate frame, freshness and unknown/low-confidence behavior.
- [ ] SPACE-04 — Integrate measured direction into matching events; test glasses orientation alignment.

## Integration and demo — whole team

- [ ] DEMO-01 — Confirm remaining owners and shared interfaces; prevent overlapping shared-file edits.
- [ ] DEMO-02 — Exercise a live sound → model → event → browser → physical display.
- [ ] DEMO-03 — Rehearse urgent interruption, dismiss, preference changes, silence, failure and reconnect.
- [ ] DEMO-04 — Prepare labeled recorded/mock fallback and one-command startup instructions.
- [ ] DEMO-05 — Rehearse judge wearing glasses while audience follows the mirror; capture measured latency.
- [ ] DEMO-06 — Verify presentation claims match measured capabilities; prepare final demo/pitch.

## Stretch after the integrated demo

- [ ] EXTRA-01 — Distance estimation, only after sensor feasibility and accuracy are demonstrated.
- [ ] EXTRA-02 — Gestures or extra input controls supported by the final hardware.
- [ ] EXTRA-03 — Additional AI/personalization beyond names and saved notification preferences.

## Sponsor and track decisions

See [sponsor build instructions](docs/sponsor-build-guide.md). These are evaluation tasks, not adopted integrations.

- [ ] SPONSOR-01 — Verify official briefs, eligibility, required technology, submission links, deadlines and multi-track rules.
- [ ] SPONSOR-02 — Emma: timebox Mana frontend trial before committing to the builder; record adopt/defer and evidence.
- [ ] SPONSOR-03 — Emma + hardware owner: evaluate SpacetimeDB before choosing new synchronization infrastructure;
  prove event delivery, expiry and reconnect, or explicitly defer while retaining the local receiver.
- [ ] SPONSOR-04 — Preserve sponsor usage artifacts and judge-accessible links for integrations actually adopted.
- [ ] SPONSOR-05 — Select final tracks from verified eligibility and implemented demo capabilities; tailor submission narratives.

## Current dependencies

Browser design, mock scenarios and receiver integration can proceed now. Physical rendering depends
on HW-01; spatial localization depends on HW-02 and SPACE-01. Name setup can be designed now,
but recognition depends on NAME-01–05. No live microphone session is required for the first UI pass.
