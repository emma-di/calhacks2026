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

- [x] UI-01 — Scaffold frontend; lock dependencies; establish visual tokens and accessible controls.
- [x] UI-02 — Build shared browser HUD with all five tiers (0 hidden), short labels and icon mapping.
- [x] UI-03 — Build fullscreen audience mirror and companion preview of the same session.
- [ ] UI-04 — Complete deterministic mock scenarios (all tiers and interruption built; remaining states pending): all tiers, interruption, repeated/long labels, idle,
  paused, unknown direction, disconnection and reconnect. Label simulated inputs.
- [x] UI-05 — Connect existing receiver and dismiss API; show a real recorded event in the polished UI.
- [ ] UI-06 — Taste source lint and desktop review complete; finish responsive, keyboard, reduced-motion and wearer/readability checks. See docs/display-ux.md.
- [x] UI-07 — Add recent alerts and separate diagnostics; keep raw scores/JSON out of the mirror.
- [x] UI-08 — Capture screenshots and short demo evidence for teammate review.

## Then: setup and preferences — Emma

- [ ] SET-01 — Core decision: defaults → searchable exception rules; keep numeric 0–4 overrides separate from presets. Confirm remaining profile and enable/disable semantics.
- [ ] SET-02 — Local searchable exception/appearance preview built. Mana onboarding revision in progress; integrate optional name/aliases and verify export before completion.
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

## Environmental audio / ML — John and Leo (proposed)

- [ ] ML-01 — Confirm John/Leo task split and preserve benchmark/tuning versus evaluation separation.
- [ ] ML-02 — Evaluate final microphone in final room: knocks, barking, generic bells, alarms and negatives.
- [ ] ML-03 — Investigate bell versus alarm confusions using scores, context and decision logs.
- [ ] ML-04 — Measure misses, false alerts and complete sound-to-screen latency; tune rules from evidence.
- [ ] ML-05 — Keep bicycle-specific labeling disabled until supported by independent evidence.
- [ ] ML-06 — Consider training only if measured remaining errors justify it; no per-user model training for settings.

## Name recognition — John and Leo (proposed)

- [ ] NAME-01 — Implement shared capture fanout and bounded worker queues; avoid opening the mic twice.
- [ ] NAME-02 — Benchmark the speech model and VAD on target compute before choosing the final configuration.
- [ ] NAME-03 — Implement typed-name/alias matching, utterance deduplication and stale-profile protection.
- [ ] NAME-04 — Coordinate nullable-confidence event support with receiver and frontend.
- [ ] NAME-05 — Test uncommon names, similar-sounding negatives, background conversation and repeated mentions.
- [ ] NAME-06 — Demonstrate configured name → “Your name” cue; log evidence without storing raw speech by default.

## Hardware and display — Yameen; stack pending

- [ ] HW-01 — Inventory supplied in [hardware stack](docs/hardware-stack.md): original Pi Zero W, 2× INMP441, SSD1306 128×64. Confirm OS, driver, actual transport and controls.
- [ ] HW-02 — Supply audio interface, sample rate, channel count/order and synchronization capability.
- [ ] HW-03 — Display a fake cue on actual hardware independently of recognition.
- [ ] HW-04 — Offline renderer implemented with 13 tests; finalize icon parity and connect actual SSD1306 driver before marking complete. See docs/display-renderer.md.
- [ ] HW-05 — Connect authoritative backend state; compare event IDs with audience mirror.
- [ ] HW-06 — Validate optical readability, refresh, mounting, power and reconnect/clear behavior.
- [ ] HW-07 — Feed final audio device into capture adapter and complete the physical end-to-end demo.

## Spatial audio — John and Leo (proposed); synchronized capture gate

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
- [ ] DEMO-07 — Verify supplied Sunday October 25, 9 AM PDT deadline; target internal submission by 8 AM PDT.
- [ ] DEMO-06 — Verify presentation claims match measured capabilities; prepare final demo/pitch.

## Stretch after the integrated demo

- [ ] EXTRA-01 — Distance estimation, only after sensor feasibility and accuracy are demonstrated.
- [ ] EXTRA-02 — Gestures or extra input controls supported by the final hardware.
- [ ] EXTRA-03 — Additional AI/personalization beyond names and saved notification preferences.

## Sponsor and track decisions

See [sponsor build instructions](docs/sponsor-build-guide.md). These are evaluation tasks, not adopted integrations.

- [ ] SPONSOR-01 — Verify official briefs, eligibility, required technology, submission links, deadlines and multi-track rules.
- [ ] SPONSOR-02 — Mana signed in; Bridge assistant queried. Pairing not performed; onboarding/export and authenticated event integration proof still pending. React mirror built meanwhile.
- [ ] SPONSOR-03 — Emma + hardware owner: evaluate Convex versus SpacetimeDB before choosing new synchronization infrastructure;
  prove event delivery, expiry and reconnect, or explicitly defer while retaining the local receiver.
- [ ] SPONSOR-06 — John/Leo: evaluate Cartesia streaming STT for names; verify endpoint, live accuracy and local fallback.
- [ ] SPONSOR-07 — Optional Claude preference interpretation only after editable settings work; require user review.
- [ ] SPONSOR-04 — Preserve sponsor usage artifacts and judge-accessible links for integrations actually adopted.
- [ ] SPONSOR-05 — Select final tracks from verified eligibility and implemented demo capabilities; tailor submission narratives.

## Current dependencies

Browser companion, mock scenarios and recorded-audio receiver integration are implemented; see [frontend evidence](frontend/README.md). Physical rendering depends
on the remaining HW-01 confirmations; spatial localization depends on HW-02 and SPACE-01. Name setup can be designed now,
but recognition depends on NAME-01–05. No live microphone session is required for the first UI pass.
