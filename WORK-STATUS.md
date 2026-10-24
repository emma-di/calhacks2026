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
| Notification policy | Acknowledgement, repeats, duration, Work/DND | Design review complete; implementation queued, no new runtime behavior yet | Next backend slice after stable UI review |
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
