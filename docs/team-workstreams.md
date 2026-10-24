# Team workstreams

Current milestone: **sound → recognition → event JSON → laptop cue → hardware display**.
The laptop path works. The physical display, spatial module, onboarding frontend and name worker
are still separate work items. See [current measured results](../reports/summary.md).

| Workstream | Responsibility | First handoff |
| --- | --- | --- |
| Hardware / Yameen | Display, optics, mounting, microphone access, controller transport | A mock event appears on the physical display; document the audio interface |
| Audio / ML — John and Leo (proposed) | Environmental classification, false-alert evaluation, future name detection | Recorded/live audio emits normalized events; keep a reproducible test set |
| Backend / integration — Emma after initial UI | Schema, preferences → tier, alert state, hardware output | Same alert state reaches laptop and physical display |
| UI/UX — Emma | Audience mirror, companion, cue design, then onboarding/settings | Polished mock cues, then recorded events in the same UI |
| Spatial audio — John and Leo (proposed) | Mic geometry/synchronization, direction and confidence | A known-angle recording produces a measured direction or unknown |

Emma's UI/backend work and Yameen's hardware work are confirmed. The supplied assignment proposes John and Leo for audio/ML and spatial work; confirm their split as a team;
GitHub access does not assign anyone to a workstream.

Use the [master TODO](../TODO.md) for status and the [UI → backend plan](ui-ux-backend-plan.md)
for the judge-wears-glasses/audience-watches-mirror demo, implementation order and proposed APIs.

## Interfaces to keep stable

- [Event + hardware handoff](integration.md): receiver routes, event fields, missing-direction behavior.
- [Name detection plan](name-detection-plan.md): shared capture, ASR worker and matching strategy.
- [Proposed onboarding profile](onboarding-profile.example.json): typed name, aliases, language and preferences.
- `GET /state`: the active cue, recent received events and priority decisions.
- `POST /events`: validated environmental event input. `POST /dismiss` with JSON `{}` clears the cue.

The environmental recognizer and future speech worker should share capture; avoid opening the same
mic independently. Direction stays unknown until synchronized channels are available. UI can use
mock events now, and onboarding should not block the recognition work.

## Shared files that need coordination

`audio/events.py`, `audio/server.py`, profile schemas, and dependency files affect several workstreams.
Call out changes to them in the PR. New hardware, spatial and frontend modules can be developed on
separate task branches without reorganizing the current Python package first.

## Before the next hardware checkpoint

Provide the controller, compute device/OS, microphone model/interface, channel count/sample rate,
synchronization capability, display model/resolution/driver, audio and alert transports, and any
dismiss/mute controls. Then implement the selected adapters against the existing event contract.

Read the [distilled team build instructions](team-build-instructions.md) for the latest supplied handoff, sponsor candidates, contract reconciliations and demo acceptance evidence.
