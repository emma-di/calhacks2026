# Agent entry point

This is the CalHacks situational-awareness glasses repo. Read this file before changing shared interfaces.

## Start here

Resume point: [HANDOFF-NEXT.md](HANDOFF-NEXT.md). Audio/signals owner (John): [HANDOFF-JOHN.md](HANDOFF-JOHN.md).

Latest continuity handoff: [HANDOFF-CLAUDE.md](HANDOFF-CLAUDE.md).

Check [WORK-STATUS.md](WORK-STATUS.md) for the latest milestone snapshot and update it when work changes lanes.

0. Read [TEAM-NOTES.md](TEAM-NOTES.md) for the latest chat decisions, caveats and branch context. Append relevant new decisions there.
   Product/UI decisions with their reasoning and rejected options: [design decisions](docs/design-decisions.md).
1. Read the [demo and setup guide](docs/demo.md) for runnable setup and actual readiness.
2. Read [TODO.md](TODO.md) for the whole-project checklist; update relevant IDs with evidence in your PR.
3. Read [team workstreams](docs/team-workstreams.md) and [distilled build instructions](docs/team-build-instructions.md).
4. Read [integration contract](docs/integration.md) and [alert engine](docs/alert-engine.md) before changing
   events, notification rules or transports. Change audio/alert-scenarios.json first; both engines test it.
5. Read [UI/backend plan](docs/ui-ux-backend-plan.md), [hardware stack](docs/hardware-stack.md),
   [display UX](docs/display-ux.md), [offline display renderer](docs/display-renderer.md),
   and [sponsor decisions](docs/sponsor-build-guide.md) for the task you are implementing.
6. Name work uses [the name plan](docs/name-detection-plan.md); environmental ML uses
   [the audio guide](docs/audio-guide.md) and [measured results](reports/summary.md).

Current UI/backend checkpoint: [simulator freeze](docs/simulator-freeze.md),
[integration revisit list](docs/integration-revisit.md), [phone mirror](docs/phone-mirror.md),
[iPhone POV camera](docs/iphone-camera.md), and [John audio review](docs/john-audio-review.md),
and [Leo spatial review](docs/leo-spatial-review.md).
Native phone direction experiment: [probe](native/PhoneSpatialProbe/README.md) /
[research](docs/phone-direction-research.md).

These files contain shared context. Agents do not automatically inherit Emma's chat history.
Some plans remain proposals: inspect code and current PRs before assuming an API exists.

## Ownership and scope

- Emma: browser mirror/companion first, then backend integration.
- Yameen: original Pi Zero W capture endpoint, SSD1306 display, optics, physical integration.
- John and Leo: proposed audio/ML, names and spatial work; coordinate their internal split.
- Use task branches and PRs; do not force-push shared branches. Read [CONTRIBUTING.md](CONTRIBUTING.md).
- Coordinate `audio/events.py`, `audio/server.py`, dependency files and profile contracts before edits.
- Keep the current Python mock/replay path runnable. Do not reorganize shared modules just to match a proposed tree.

## Product invariants

- Laptop runs inference; original Pi Zero W is the planned capture/display endpoint, not Zero 2 W.
- Browser and physical glasses consume one canonical alert state. Backend owns priority and timing.
- Mock, recording and microphone sources are distinct. Do not imply a connected receiver means live audio.
- Unknown direction stays unknown; synchronized capture and measured error gate spatial cues.
- Zipformer is the current pretrained default. Rule tuning is not model-weight fine-tuning.
- Bicycle subtype is disabled pending evidence. Name recognition and hardware links are not implemented by a design preview.
- UI direction: calm, no eyebrow headings or decorative HUD chrome. Defaults first, then search/add explicit exceptions; icon-first nonurgent cues, urgent labels, optional gentle motion with reduced-motion support. See display UX notes.
- No per-user training for settings. Match names only after the speech worker is actually integrated.
- Evaluate sponsor tools against meaningful product use; record adopt/defer, preserve local fallback,
  and choose at most one equivalent cloud state layer. Never claim unverified track eligibility.
- Keep credentials, model weights, private audio and runtime logs out of Git. Never auto-start a microphone to test the UI.

## Verification and communication

- Frontend: `npm ci --prefix frontend`, `npm run build --prefix frontend`, `npm test --prefix frontend`.
- Python: follow CONTRIBUTING checks. Use the appropriate recorded/mock inputs before asking for live input.
- Update docs when contracts change. Clearly separate implemented behavior from planned work.
- End user-facing final replies with a TLDR stating completion or a concrete question/options.
- If suggesting an action, either start it or ask the clarification needed to act; do not leave an idle next-step suggestion.
