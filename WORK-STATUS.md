# Work status

Checkpoint: October 24, 2026, Pacific time. This is a maintained milestone snapshot, **not a live
agent telemetry feed**. Root updates it when work changes state. For detailed tasks use [TODO](TODO.md);
for decisions and caveats use [TEAM-NOTES](TEAM-NOTES.md).

## Latest software checkpoint

527-label catalog choices now flow through settings, hot-reloaded rules, per-ID priority and OLED
icons. Recorded Whistling + Mana adapter→Python→Rain/drop integration checks pass. Profile refresh
preserves names; only explicit edits save. All previews centered; directional alignment retired.
Site readability/mobile cleanup complete; Pi deployment parked. Domestic-pets→Dog barking is an
explicit temporary demo override. Proposed50 custom symbols are awaiting approval, not implemented.
Current evidence: docs/audio-software-readiness.md, docs/mana-onboarding.md, docs/proposed-50-cues.md.

## Latest: finer display directions and snap parked

16-position triangle renderer is ready in shared Pi/browser assets; original four directions are
unchanged. Explicit simulated-bearing selector verified with a 22.5° mock cue. 93 Python tests,
21 frontend tests and build pass. Pi display-only deployment audited; Pi unreachable, not deployed.
Snap is off per Emma. See [direction/deployment guide](docs/display-16-directions.md).

## Alarm lifecycle and glasses-only input checkpoint

Claude's centered icon + solid direction triangles remain in both pixel renderers. Triangles require
supported direction; no connected spatial feed currently. Fire/smoke clears after four seconds of
continuous same-source negative model evidence; gaps/dropouts do not count as quiet. Session-only
Snap to dismiss is available without camera; camera thumbs-up stays optional. Snap accuracy awaits
real trials. Verified: 89 Python tests, 21 frontend tests, build and 10,000 engine parity steps.
Live snap toggle was clicked off/on and checked against receiver health. Fixed stale hot-reload
state and mic worker queue-timeout exit found during the user's live trial.

## Live-testing checkpoint

Session-only Show every detection bypasses recognizer cooldowns and alert repeat suppression.
Fire alarm joins smoke alarm as an urgent alias; recorded-score tradeoffs are in
reports/fire-alarm-alias-review.json. Verified: 85 Python / 21 frontend tests, production build,
10,000 cross-language engine comparisons. User-authorized MacBook microphone remains active.
Name-recognizer decisions are shown separately from display decisions. Physical glasses are offline.

## Latest integration checkpoint (supersedes older snapshots below)

John's integration branch `12dddc0` is incorporated into `codex/browser-mirror`: live hearing panel,
custom-sound teaching and improved name spelling are connected to the current receiver.
Verified this session: 79 Python tests, 21 frontend tests, production build, 10,000 Python/browser
alert-state comparisons. No microphone capture or new physical hardware trial performed.
Pretrained sound-catalog selection is still unfinished. See [resume notes](HANDOFF-NEXT.md).

| Worker / lane | Work | Checkpoint status | Evidence / handoff |
| --- | --- | --- | --- |
| Main Codex agent | Preview consistency and reliable individual sound tests | Fixed and locally verified; PR branch | Same semantic icons/text/placement for mirror/OLED; bell replaces previous urgent sample; dog test override removed |
| Preferences subagent | Defaults first, sound search, explicit exceptions, appearance controls | Design complete; consolidated into Mana onboarding | frontend/mana/AwareOnboarding.jsx; local save plus receiver profile sync |
| Hardware subagent | Specs, offline OLED renderer and display guards | Complete | [Renderer](docs/display-renderer.md), 13 tests; no physical driver tested |
| Hardware subagent follow-up | Sponsor substitution matrix | Complete | [Decision matrix](docs/sponsor-decision-matrix.md); no infrastructure provisioned |
| Mana | Onboarding app and standalone React export | Integrated and checked locally | [Mana handoff](docs/mana-onboarding.md), frontend/mana/AwareOnboarding.jsx |
| Notification policy + receiver | Preferences → effective tier, acknowledgement, repeats, queue, Work/DND, pause, profile API | Implemented and tested (software) | [Alert engine](docs/alert-engine.md); shared scenarios run by Python and the browser |
| Companion redesign | Live screen for judges, glasses frame, reasons, camera, phone layout | Implemented; lint/inspector pass | [Frontend guide](frontend/README.md) |
| Glasses client | /display poller, SSD1306 I²C driver, self-test | Written and tested against a fake bus; awaiting the module | `python3 -m hardware.oled_client --self-test` |
| Yameen / physical hardware | Driver, optics, fake OLED alert, synchronized capture | Awaiting physical evidence | [Hardware handoff](docs/hardware-stack.md) |
| Audio / ML teammates | Final input testing, names, spatial | Team-owned; status not inferred from this chat | [Workstreams](docs/team-workstreams.md) |

## Deliberately parked

Further Mana generation, Claude API integration, new cloud infrastructure and extra hardware features
are parked while the stable preview and notification policy are resolved. Mana Bridge is not installed.
The original Pi Zero W remains the planned capture/display endpoint; another Mac will run inference.

## How to follow along

- GitHub [PR #2](https://github.com/emma-di/calhacks2026/pull/2) and branch `codex/browser-mirror` contain current work.
- Subagents are internal workers, not separate user-owned chats. Root can report their actual status
  when asked; repository notes contain their outputs rather than automatically inheriting chat state.
- Do not mark another teammate's task complete without their evidence.

## Handoff snapshot — October 24, ~00:30 (Claude session → Codex)

All work is pushed to `codex/browser-mirror` (PR #2, not merged to main).

**Built and verified (automated tests + browser checks):**
- Receiver alert engine (audio/alerts.py) and identical browser port; 14 shared scenarios run by both.
  Preferences → effective tier, interrupt/queue/resume, repeat merging, acknowledgement, Work/DND,
  pause, duplicate IDs, expiry logging, four-way direction (confidence ≥ 0.6), look-to-resolve,
  thumbs-up gesture dismiss, 0.6 s check-mark confirmation.
- Receiver API: /state, /display, /health, GET/PUT /profile (atomic, survives restart), /events,
  /dismiss {event_id}, /controls, /look. 37 Python + 9 frontend tests incl. HTTP and restart.
- Glasses: edge-placed panel layout (icon hugs the sound's edge, unknown centred, tier = box only),
  32×32 pixel icons; browser renderer byte-identical to Python (render fixtures). oled_client + SSD1306
  driver tested against a fake I²C bus and live against the receiver (pbm sink).
- Companion "Night lens" redesign; lens draws the real panel frame; camera backdrop; MediaPipe
  thumbs-up (model loads locally, verified with a synthetic stream; real-hand dismiss seen in receiver log).
- Live laptop-mic recognition into the receiver was exercised (knock detected).

**Still to test:** physical SSD1306 + optics readability; glasses camera as a webcam; thumbs-up in
demo lighting with a real hand across several people; full taste/inspector pass on the night theme
at 768/390; unfamiliar tester; second Mac; final mic/room accuracy and latency.

**Still to do:** confirm camera model/interface (Yameen); capture/inference heartbeat for /health;
spatial worker emitting direction; name worker; slow 1 Hz urgent pulse (proposed, not built);
merge PR #2 after teammate review.

**Decisions made in this session that need team re-review** (reasoning in [design decisions](docs/design-decisions.md)):
1. Receiver, not producers, decides tier; `/state.active.priority_tier` is now the effective tier.
2. Queue/repeat/ack timings (5 items, 10 s fresh, 15 s acknowledge, urgent up to 2 min) and
   one-gesture dismiss; check mark delays a resumed cue by 0.6 s.
3. `DisplayState` trusts a newer `state_sequence` for the same event (needed for resume/extension).
4. Panel layout changed (edge placement, new icons, tier = box). Unknown direction stays centred.
5. Direction: four sides at 90° each; a two-mic worker must send null rather than guess front/behind.
6. Dismiss is a camera thumbs-up (not snap); audio snap rule disabled. Gesture choice is open.
7. Night lens visual direction replaced the repo's dealt "achromatic ledger" style (Emma chose it);
   onboarding tier colours reset to white + amber (storage key bumped, old colours dropped).
8. `name_called` and `confidence: null` accepted by /events; Gentle/Active presets still provisional.

## Verification limits and next acceptance checks

- Last verified local build (Oct 23, late): TypeScript/Vite success; 9 frontend tests; 34 Python tests.
  Browser checks: preferences → receiver → glasses client, Work/DND/pause, dismiss/resume, receiver kill
  and restart, 1440/768/375, keyboard focus, audience view, camera with a synthetic stream. Not yet:
  physical OLED, an unfamiliar tester, wearer readability.
- Recorded inference → receiver → polished browser was exercised previously. Live final-mic → Pi OLED
  and second-Mac portability have not been demonstrated here. No microphone was started by this UI work.
- Before calling UI finished: keyboard-only setup, narrow screens, reduced motion, all tiers, expiration,
  urgent interruption, disconnect/reconnect, and audience/preview event consistency need a full QA pass.
- Before calling recognition finished: final-mic positives/negatives in the demo room, overlapping/repeated
  sounds, bell/alarm confusion and measured end-to-end latency. See reports/summary.md for offline limits.
- Backend acceptance slice met in software: preferences change receiver priority; repeats do not restart an
  acknowledged alarm; event-specific dismiss, pause and DND behave consistently. Next: run the glasses
  client on the Pi and add a capture/inference heartbeat.
- New communication proposal reviewed: name/attention detection first, optional short companion captions
  as stretch. No new speech, camera, gesture, revoicing or ASL implementation was started by that review.

## Codex return audit — October 24

Reviewed Claude's code and design handoff; retained Night lens, shared pixel frames, four-way placement,
queue/repeat/mode rules and the optional camera gesture. Timing values remain provisional product
choices, not wearer-validated requirements. Real directional inference and look sensing are not running.

Found and fixed:
- Browser simulator accidentally routed test events to HTTP because event provenance shadowed session
  mode. Separate delivery routing now has two boundary tests (sound + camera gesture, both modes).
- A continuously held thumbs-up could fire again after cooldown and dismiss a newly resumed cue.
  Recognition now requires release before another action; two hold/cooldown tests added.
- Camera requests now discard late streams after unmount/switch and stop tracks directly on cleanup;
  enumeration failure no longer discards a working feed. Physical camera recheck remains pending.
- Receiver failure clears confirmation as well as the active cue; profile saves are serialized in edit
  order and stale completions do not mark a newer draft applied.
- Failed profile persistence now returns HTTP 503 without changing live settings, verified over HTTP.
- Status wording distinguishes a polling display client from verified physical pixels, and recent audio
  events from a confirmed listening microphone.

Verified this audit: **38 Python tests**, **13 frontend tests**, production build, browser simulated
left urgent cue in both views and local thumbs-up confirmation. Python socket tests require loopback
binding permission in the Codex sandbox. No new microphone or camera capture was started. The existing
Claude-started services/capture were not stopped. Full responsive/layout inspection was not rerun.

Still required: physical OLED/optics and orientation, camera interface/model, real-hand gesture tests,
second Mac, final mic/spatial/name workers, unfamiliar-tester review and full responsive accessibility QA.

## Hardware correction — October 24

The glasses have no camera. Optional POV camera video is a browser demonstration backdrop only.
Automatic hand tracking and the test thumbs-up button are removed from the app flow; manual Dismiss
and expiry remain. Earlier camera-on-glasses and physical gesture claims are superseded. Phone as
OS-exposed webcam is a possible demo input, not a verified direct phone-to-site streaming feature.

## Overnight software pass — October 24

[Full verification report](docs/overnight-verification.md): 41 Python tests, 15 frontend tests, 17 shared
scenarios, 127 raster fixtures and 150,000 matching stress actions (~52 simulated hours, not wall-clock
hardware runtime). Fixed Pause confirmation leakage, queue bounds/ties, invalid-request rollback,
receiver-instance isolation, malformed-state handling, onboarding/live render mismatch and responsive
controls/audience sizing. Actual UI→receiver settings, pause, connection-loss/restart and keyboard mode
selection exercised on isolated ports without opening a mic/camera. Physical checks and multi-client
profile ownership remain pending; existing backend processes need restart to load Python fixes.

## Simulator freeze checkpoint — October 24

See docs/simulator-freeze.md for D/E role coverage and docs/integration-revisit.md for blocked/deferred
checks. Latest: centered icon + compass arrows inside fixed right-side patch; category inheritance;
pending custom-sound requests; optional demo-camera gesture restored. Emma's live gesture trial was
finicky, so tune later and keep manual Dismiss. Phone connection is not built; it is the next focus
after phone type/flow is confirmed. One OLED alert at a time is the current decision.

Phone mirror implemented and browser-checked at 390px with a real receiver mock event. It is read-only,
access-key protected, and uses the shared OLED renderer. 43 Python / 18 frontend tests pass. Actual
Safari-on-iPhone network trial pending; see docs/phone-mirror.md. No phone camera streaming implemented.

Continuity Camera selected for iPhone POV; device refresh and in-app instructions added. Physical
trial requires Emma to connect/lock/mount the phone and select it on the Mac. John's custom-sound
branch reviewed with 14 passing isolated tests; integration boundaries recorded in docs/john-audio-review.md.

Leo spatial branch reviewed: 17 synthetic tests pass; standalone simulated map on localhost:8878.
No microphone started. Live gates: silence/input guards, synchronized capture, measured yaw,
classification association and receiver adapter. Current iPhone Continuity input is mono; see
docs/leo-spatial-review.md for Apple native stereo alternatives and limitations.

Native spatial phone probe: Xcode 27.1 installed; actual iPhoneOS build passes, plus 80 synthetic math
checks. John’s phone is connected/trusted; signing/deployment in progress. No live direction accuracy
claim yet. See native/PhoneSpatialProbe/README.md and docs/phone-direction-research.md. This probe is
separate from the frozen simulator and does not emit alerts. John’s observations stream reviewed
with six passing isolated tests; not merged into current receiver. Speech remains John’s ongoing work.


Usage-limit handoff: HANDOFF-CLAUDE.md is the current resume point. Xcode is extracting OS library
symbols from John's connected/unlocked iPhone after Developer Mode was enabled. Signed Run was
requested; app launch and actual FOA capture are not yet confirmed. Native diagnostic preservation
change compiled successfully. Real recorded John-observations replay delivered 5 observations +
one dog_bark event (custom heads disabled). All follow-up gates and running services are in the handoff.
