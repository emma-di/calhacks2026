# Sponsor and track build instructions

Read this before choosing frontend tools, backend infrastructure, or demo scope.
This guide distills the sponsor/track discussion supplied by Emma on October 23, 2026.
It records **candidate opportunities, not verified eligibility or a commitment to use a sponsor**.
The supplied discussion references a separate prize list that is not included here. Confirm the
official challenge briefs before relying on required technologies, judging criteria, deadlines,
multi-track entry rules, or submission formats. Prize amounts and scoring percentages are omitted
until verified. Nobody is assigned a sponsor integration by this document alone.

## TLDR for builders

- Prioritize a working sound → recognition → visual alert demo. The judge wears the glasses;
  the browser mirror lets everyone follow the same cue.
- Design around accessibility and everyday human connection. A person calling the wearer's name
  is a strong demo moment once name recognition works. Add direction only when it is measured reliably.
- **Evaluate Mana before committing to the frontend builder.** It may fit onboarding, preferences
  and the simulator. Meaningful use and a judge-accessible demonstration matter; document what it built.
- **Evaluate SpacetimeDB before committing to a new synchronization backend.** It could coordinate
  preferences and active alerts across displays, but must pass an actual Python-to-browser/hardware-bridge test.
  The existing local receiver remains the working integration path while that decision is pending.
- Keep sponsor choices behind clear interfaces. Do not block the basic demo or replace working
  infrastructure solely to collect another track. Record an explicit adopt/defer decision below.
- Only claim features and sponsor usage that the final demo and repository can substantiate.
- The additional team handoff proposes **Cartesia for live name transcription** and **Convex for
  persistent/reactive application state**. Evaluate these as real product integrations; neither is
  installed or adopted just because it appears in the handoff. Choose Convex **or** SpacetimeDB
  for cloud synchronization, not both. See [team build instructions](team-build-instructions.md).

## Candidate tracks and what to build/show

Rankings are project-fit judgments from the supplied discussion, not official rankings or winning odds.

| Priority | Candidate | What builders should preserve | Evidence for submission |
| --- | --- | --- | --- |
| Primary | Best People-First Hack | Readable, discreet cues; control over notification overload; editable preferences | Explain the accessibility need, show wearer experience, document user feedback if actually collected |
| Primary | Meta — Bringing People Closer Together with AI | Name/attention cues that support everyday interaction; AI central to recognition | Someone calls a configured name and the wearer receives a cue; explain actual models and limitations |
| Primary if physical demo works | Best Hardware Hack | Working wearable output, optics, mounting and real audio/display integration | Physical demonstration, hardware stack, wiring/integration notes and measured delay |
| Evaluate early | Mana | Useful contribution to companion, setup, preferences or simulator | Build history/artifacts, accessible project links and a clear explanation of Mana's contribution |
| Secondary if implemented | Most Technically Complex Hack | Reliable integration, shared capture, names, measured localization and wearable output | Architecture, full-pipeline latency and direction-error measurements; separate working from planned features |
| Conditional architecture choice | SpacetimeDB | Real shared alert/preferences state and subscriptions, if selected | Running synchronization across actual clients and the hardware bridge; explicit reconnect behavior |
| Optional | Most Creative Hack | Intuitive translation of sound into visual cues | A clear, original interaction demonstrated in use |

These are candidate track titles from the notes; verify their current official names and requirements.
Do not assume Meta's challenge requires a Quest, or that a Quest automatically establishes eligibility.

## Sponsor decisions before implementation

### Mana — frontend decision

Owner: Emma. Status: **evaluate; not adopted**.

1. Obtain the official challenge brief and platform access. Confirm what qualifies as meaningful use
   and whether a runnable app/agent link is required or merely encouraged.
2. Timebox a small trial (target: 30 minutes): build a cue preview or preferences screen, then prove
   it can consume our agreed state/API. Check source access/export and how the local Python backend
   will be reached; a hosted page cannot be assumed to reach a laptop's loopback receiver.
3. Adopt only if the result supports the mirror's visual quality, required integration and demo access.
   Otherwise record why we deferred and continue the proposed React/Vite implementation.
4. If adopted, retain project links, screenshots and a description of actual platform use for submission.

The [UI/backend plan](ui-ux-backend-plan.md) proposes React/Vite, but that choice remains subject
to this early trial. Do not build two full frontends in parallel for the same screen.

### Convex versus SpacetimeDB — synchronization decision

Owner: Emma for backend coordination, with the hardware owner. Status: **evaluate; not adopted**.

1. Evaluate the new handoff's preferred candidate, Convex, alongside SpacetimeDB. Verify official
   challenge eligibility, runtime/client support and deployment requirements for the selected option.
2. Timebox a small proof (target: 30–45 minutes): a Python detection updates canonical active state;
   a browser and a second subscriber or hardware bridge receive it; verify clear/expiry and reconnect.
3. Check target compute compatibility, connection/authentication setup and demo network reliability.
   Preserve backend priority authority, explicit event IDs, freshness, source labels and local fallback.
4. Adopt only if this meaningfully helps synchronization and fits the hackathon budget. Otherwise
   retain the local receiver and document the decision; no backend rewrite is required by this guide.

Hardware transport is still unknown, so actual display compatibility cannot yet be claimed.
The proof can use a second subscriber, with physical bridge validation remaining a separate gate.
If Convex is selected, use it for saved profiles, event metadata/history and reactive preference
updates. Keep the local alert engine authoritative and the local detection-to-display path functional
without a cloud round trip. Do not let a cloud subscriber independently recompute competing cues.

### Cartesia — name recognition decision

Proposed owners: John and Leo. Status: **evaluate; not adopted**.

The additional handoff identifies a useful fit: streaming speech-to-text feeding configured-name
matching. This is a stronger use case than adding speech output to a visual product.
Verify the current model/endpoint (the handoff names Ink-2), streaming format, keyterm support,
credentials, cost and challenge rules against official documentation before implementation.
Demonstrate microphone → transcript → name match → real `name_called` event, including nonmatching
names and background-conversation negatives. Streaming sends speech to a provider: make that clear
in setup and do not store raw speech/transcripts by default. Keep keys server-side.
Timebox connection debugging to 60–90 minutes, then establish the independent local ASR fallback
described in the [name plan](name-detection-plan.md). Provider choice must not change the event contract.

## Other sponsor opportunities

- **MLH Best Use of Gen AI:** verify the actual rules and whether the product's use qualifies.
  Using a coding assistant or a pretrained sound classifier does not by itself establish eligibility.
- **Cartesia:** evaluate the live transcription use case above; visual output does not rule out a
  meaningful speech-input integration. No working integration is claimed yet.
- **Anthropic/Claude:** optional natural-language preferences → proposed structured settings → user
  review → save. Keep it outside urgent-alert handling and defer until ordinary settings work.
- **Moss, Apify, Bright Data:** defer unless a real retrieval or web-data requirement emerges. A
  deterministic event-to-tier lookup needs neither semantic retrieval nor scraping.
- **Microsoft — Built for the Real World:** the supplied notes describe an AI-agent focus.
  Verify this before investing; do not relabel the existing classifier pipeline as an agent.
- **Other AI-first tracks:** check required sponsor technology against what actually runs in the product.

## Submission checklist

- Confirm official rules, deadline/timezone, required links and whether multiple-track entry is allowed.
- Record adopted sponsor decisions and real dependencies in this guide and the README.
- Keep accessible demo/project links and evidence of sponsor usage; check access as a judge would.
- Describe pretrained models honestly: recognition rules were tuned; model weights were not fine-tuned.
- Separate name recognition, speaker identity and direction. None establishes the others automatically.
- Use a human-centered demo story; show measured capabilities rather than a long planned feature list.
- Update [SPONSOR TODO items](../TODO.md#sponsor-and-track-decisions) as decisions and evidence arrive.

## Decision log

| Decision | Status | Evidence / outcome |
| --- | --- | --- |
| Official track rules and eligibility | Unverified | Need official briefs; supplied summary alone is insufficient |
| Mana for frontend workflow | Evaluation | Signed in; assistant queried about Bridge. No pairing, export or live event proof completed; React mirror runs locally |
| Convex versus SpacetimeDB for cloud state | Evaluate | Handoff prefers Convex; select one or defer both; local receiver works |
| Cartesia for streaming name transcription | Evaluate | Handoff proposes Ink-2; endpoint and live performance still need verification |
| Claude for preference interpretation | Optional | After basic settings; user reviews proposed values before saving |
| Final submission tracks | Pending | Choose after eligibility and working capabilities are confirmed |

## Mana Bridge follow-up

A sponsor contact supplied by Emma suggested Mana Bridge for connecting the hardware and frontend.
Treat this as a lead, not verified transport capability. After sign-in, inspect official Bridge setup,
source/API access, deployment model and permission scope. Prove local event → Mana view with mock
data first; do not expose the current unauthenticated loopback receiver publicly or grant broad
filesystem/network access without understanding the bridge. Final track demo should show actual
nearby sound → physical display, with a clearly labeled recorded fallback.

Mana assistant follow-up: Bridge was described as remote terminal/file access, not a generic HTTP
tunnel. Generated React was described as adaptable outside Mana, with platform-specific dependencies
to replace. These are assistant-reported capabilities, not independently validated export/runtime
integrations. No Bridge installation or pairing was performed. See [team notepad](../TEAM-NOTES.md).
