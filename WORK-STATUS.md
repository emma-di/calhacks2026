# Work status

Checkpoint: October 23, 2026, Pacific time. This is a maintained milestone snapshot, **not a live
agent telemetry feed**. Root updates it when work changes state. For detailed tasks use [TODO](TODO.md);
for decisions and caveats use [TEAM-NOTES](TEAM-NOTES.md).

| Worker / lane | Work | Checkpoint status | Evidence / handoff |
| --- | --- | --- | --- |
| Main Codex agent | Preview consistency and reliable individual sound tests | Fixed and locally verified; PR branch | Same semantic icons/text/placement for mirror/OLED; bell replaces previous urgent sample; dog test override removed |
| Preferences subagent | Defaults first, sound search, explicit exceptions, appearance controls | Design complete; consolidated into Mana onboarding | frontend/mana/AwareOnboarding.jsx; simulator-only, no live profile API |
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
