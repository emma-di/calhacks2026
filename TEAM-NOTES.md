# Team notepad — read this first

Running decisions and caveats from Emma's project chat. **Last updated: October 23, 2026.**
Anyone may append a dated note on their task branch and open a PR. Keep it concise: decision,
owner, consequence, and link to detail. Do not overwrite contradictory notes silently; mark what supersedes them.
Never put API keys, private ambient audio or transcripts here.

## Where everyone and their agents should start

- [AGENTS.md](AGENTS.md): agent entry point and project invariants.
- [README](README.md): runnable setup and actual readiness.
- [TODO](TODO.md): entire-project tasks, dependencies and evidence.
- [Workstreams](docs/team-workstreams.md): owners and interface coordination.
- [Build instructions](docs/team-build-instructions.md): distilled team handoff and demo goals.
- [UI/backend plan](docs/ui-ux-backend-plan.md): frontend-first sequence and proposed backend contracts.
- [Event contract](docs/integration.md), [audio guide](docs/audio-guide.md), [name plan](docs/name-detection-plan.md).
- [Hardware stack](docs/hardware-stack.md): supplied parts, verified specifications and unproven capture/transport gates.
- [Sponsor guide](docs/sponsor-build-guide.md): candidate integrations, eligibility verification and adoption decisions.
- [Frontend guide](frontend/README.md): current UI implementation, setup and verification evidence.

**Branch context:** these latest notes, frontend and hardware/agent guides are on
`codex/browser-mirror`, built on the planning branch `codex/ui-ux-backend-plan`.
Until the PRs merge, cloning `main` alone will not include all this context. Fetch and inspect the
branch before creating your own task branch from the appropriate agreed base. Never reset existing local work.

```sh
git fetch origin
git switch --track origin/codex/browser-mirror
```

If you already have that local branch, use `git switch codex/browser-mirror` instead. Read
[CONTRIBUTING](CONTRIBUTING.md) before editing. Agents need these repo files; they do not inherit this chat.

## Decisions and caveats — October 23

### Product and team

- Judge wears glasses; audience watches the same active cue in the browser mirror.
- Emma: UI/UX first, then backend/integration. Yameen: hardware. John and Leo are proposed for
  audio/ML, name detection and spatial work; agree their internal split instead of duplicating work.
- First integrated sound-to-alert demo outranks elaborate onboarding and sponsor extras. Keep the
  full TODO maintained. Parallel agent sessions are authorized where work can be split cleanly;
  assign separate files/tasks and coordinate shared schemas.
- “Aware” is a provisional frontend title, not a finalized product-name decision.

### Hardware

- **Original Pi Zero W, not Zero 2 W.** Two owned INMP441s; SSD1306 white 128×64 I²C OLED;
  32 GB microSD; existing power bank/cable/header. No new header purchase needed.
- Plan laptop inference, Pi capture/display. Confirm OS, ALSA driver, channel synchronization and
  local transport before claiming hardware integration. Shared-clock stereo is electrically supported;
  that does not establish a working Linux capture path.
- The UI's exact one-bit raster is a design preview. Optics, firmware rendering and physical output
  are still untested. Direction remains unknown; two mics do not establish unambiguous 360° localization.

### Audio and backend

- Zipformer Small INT8 is the current pretrained model. Rules were tuned; weights were not fine-tuned.
  YAMNet is a comparison option. Do not restart model selection based on older planning notes.
- The existing local Python receiver works. New UI uses its `/state`, `/events`, `/dismiss` through a
  development proxy. The receiver is loopback-only; Pi audio ingress/display transport are not built.
- Keep `schema_version` and `event_id`; older handoff examples with `id` are not new schema decisions.
  Backend owns effective priorities/timing. Detection confidence is an uncalibrated score.
- Classifier and name transcription are separate workers sharing capture; name recognition is still
  planned. Configuration of a name is not evidence that ASR is running. No per-user model training.
- Bells can be confused with alarms: inspect current/recent alarm context and decision logs. Existing
  bell suppression holds for four seconds after qualifying alarm context. Bicycle subtype stays disabled.
- Current queue behavior drops lower-priority display requests; proper queuing is planned. Current
  tier-4 lifetime is at most 30 seconds, not an implemented indefinite warning.

### Frontend readiness

- Implemented: companion, fullscreen audience view, mock sounds, priorities 0–4, interruption timeline,
  event history/diagnostics, simulator-only tier controls, exact 128×64 one-bit preview and receiver adapter.
- Verified: build, four behavior tests, urgent priority, receiver delivery/dismissal, and labeled recording
  → model → receiver → new browser cue. No live microphone session was started for this UI work.
- No physical glasses, saved profile API, worker health, actual pause, name worker or cloud state is
  connected yet. The UI labels these limitations. Simulator tabs are independent; mirror expands one session.

### Sponsors and Mana

- Sponsor integrations are candidates, not mandatory tools for every teammate. Hardware/audio owners
  keep working against repo contracts; do not migrate their work to Mana to become “eligible.”
- Mana is now signed in. Its assistant described Bridge as remote terminal/file access, with **no
  documented automatic localhost HTTP/event tunnel**. This is assistant guidance, not an independently
  completed source audit. No Bridge was installed or paired, and no terminal permissions were granted.
- A Mana-hosted UI still needs an explicit authenticated application relay or supported integration.
  Preserve local display delivery. The assistant says generated React can be adapted/exported, but
  a working export/live-event proof has not yet been completed.
- Mana onboarding/prototyping remains an opportunity; do not duplicate two entire frontend apps.
- Evaluate Cartesia streaming STT for names; verify the actual current endpoint/model and test negatives.
  A local ASR fallback remains planned. Cloud speech requires clear disclosure and server-side keys.
- Evaluate **Convex or SpacetimeDB**, at most one equivalent cloud state layer; neither adopted yet.
- Claude could translate free-text preferences to proposed settings for user review. Optional, after
  ordinary settings work; never put it in urgent-alert handling. Track eligibility still needs official rules.
- The handoff's Sunday Oct 25, 9 AM PDT deadline is a supplied target, not officially verified here;
  proposed internal cutoff is 8 AM PDT. Verify the submission page.

## Open handoffs

- Yameen: OS/driver, stereo capture proof, display communication and readable fake cue through optics.
- John/Leo: internal ownership split, live/recorded recognition evidence and speech-provider trial.
- Emma: saved preferences and authoritative backend extensions after reviewing the first UI; Mana
  onboarding/export/event-relay proof before making sponsor usage claims.
- Team: official sponsor rules, deadline, cloud-state decision and final submission categories.

## Add a note

```text
Date / author:
Decision or caveat:
Owner / affected interface:
Evidence or doc link:
Status: proposed | decided | implemented | verified | superseded
```
