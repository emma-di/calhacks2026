# Project TODO

Latest October24 software supersedes older unchecked snapshots: catalog selection and name integration
are wired, Mana receiver adapter is live, stale profile overwrite fixed, centered16-arrow renderer ready.
See WORK-STATUS.md and docs/audio-software-readiness.md; remaining room/device acceptance is not
completed by unit tests. Approved 50 symbols and curated picker are implemented; see docs/cue-catalog-verification.md for
wiring evidence and remaining recognition gaps. Physical optics, independent per-class accuracy
and final room testing remain acceptance gates.


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
- [x] UI-04 — Deterministic scenarios: all tiers, interruption, skip, queue/resume, repeats, idle, paused,
  Work/DND, unknown direction, disconnect and reconnect. Shared fixtures in audio/alert-scenarios.json;
  Play a busy minute in the UI. Sources labeled (Test sound / Recording / Microphone).
- [x] UI-05 — Connect existing receiver and dismiss API; show a real recorded event in the polished UI.
- [ ] UI-06 — Redesigned Live screen; taste lint and inspector pass (0 FAIL) at 1440/768/390; keyboard focus,
  reduced motion and phone order checked. Remaining: wearer readability through the optics and an
  unfamiliar tester. See docs/display-ux.md.
- [x] UI-07 — Add recent alerts and separate diagnostics; keep raw scores/JSON out of the mirror.
- [x] UI-08 — Capture screenshots and short demo evidence for teammate review.

## Then: setup and preferences — Emma

- [x] SET-01 — Defaults → searchable exception rules; numeric 0–4 overrides separate from presets; Ignore (0) is
  the disable. Receiver validates and applies the same semantics.
- [x] SET-02 — Mana onboarding integrated: defaults, searchable exceptions, optional name/aliases, display preview and Start preview. Automatic browser-local saving; no user-facing JSON. Eight frontend tests plus browser Ignore/reset flow verified. Name recognition itself remains pending.
- [x] SET-03 — Browser-local settings plus receiver saved/applied/error states (version shown) and glasses
  connection from /health.
- [x] SET-04 — Profile pushed via PUT /profile on connect/change, persisted atomically, reloaded on restart.
  /health reports name_worker unavailable; the UI says names are not running yet.

## Backend/integration — Emma after initial UI

- [ ] API-01 — Implemented backward-compatible /state, /display, /profile, /controls (docs/alert-engine.md);
  awaiting teammate review before calling the contract agreed.
- [x] API-02 — Profile validation, server revision, atomic .cache/profile.json persistence (tests/test_alerts.py).
- [x] API-03 — audio/alerts.py effective_tier: per-sound → category → preset → producer default; focus modes applied after.
- [x] API-04 — Dedup, 5-item queue with 10 s freshness, interruption/resume, repeat merging, urgent ongoing cap.
- [x] API-05 — state_sequence, remaining_ms, session_id, event-specific dismiss; restart does not replay.
- [ ] API-06 — /health reports per-source event recency and display clients; silence ≠ disconnect. Inference
  heartbeat from the capture worker still pending (needs audio/cli change).
- [ ] API-07 — Pause/resume and acknowledgement implemented in the receiver and labeled honestly (pause hides
  alerts; it does not stop capture). Stopping capture itself still needs a worker control.
- [ ] API-08 — Verified in software: browser and hardware/oled_client follow one envelope, clear on timeout and
  disconnect, ignore re-polled sequences. Repeat on the physical OLED.
- [x] API-09 — Browser Ignore rule → receiver → dog ignored, knock drawn by the glasses client in 71 ms.

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

## Hardware and display — Yameen; stack supplied, device validation pending

- [ ] HW-01 — Inventory supplied in [hardware stack](docs/hardware-stack.md): original Pi Zero W, 2× INMP441, SSD1306 128×64. Confirm OS, driver, actual transport and controls.
- [ ] HW-02 — Supply audio interface, sample rate, channel count/order and synchronization capability.
- [x] HW-03 — Fake cues on the real SSD1306 via glasses-pi (Oct 24): `scripts/glasses_up.sh selftest`, OLED at 0x3C.
- [ ] HW-04 — Renderer + browser preview byte-identical (render fixtures); SSD1306 I²C driver and
  hardware/oled_client.py with self-test written and tested against a fake bus. Mark complete after it
  drives the real module. See docs/alert-engine.md.
- [x] HW-05 — Live receiver state on the real OLED (Oct 24): `scripts/glasses_up.sh live` over an SSH tunnel; demo scene drove knock/dog/alarm-clock/smoke cues, 40–118 ms receiver→display.
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
- [ ] EXTRA-04 — Proposed optional attention-keyword triggers and short, on-demand companion captions, only after name detection and the physical loop. Nearby speech does not establish that someone is addressing the wearer. Revoicing/ASL translation are outside current scope.

## Sponsor and track decisions

See [sponsor build instructions](docs/sponsor-build-guide.md). These are evaluation tasks, not adopted integrations.

- [ ] SPONSOR-01 — Verify official briefs, eligibility, required technology, submission links, deadlines and multi-track rules.
- [ ] SPONSOR-02 — Mana-built onboarding exported and integrated locally with provenance. Bridge pairing/authenticated device integration and verified public submission links remain pending. React mirror remains locally authored.
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
