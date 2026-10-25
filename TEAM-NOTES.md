# Team notepad — read this first

Running decisions and caveats from Emma's project chat. **Last updated: October 23, 2026.**
Anyone may append a dated note on their task branch and open a PR. Keep it concise: decision,
owner, consequence, and link to detail. Do not overwrite contradictory notes silently; mark what supersedes them.
Never put API keys, private ambient audio or transcripts here.

## Where everyone and their agents should start

- [AGENTS.md](AGENTS.md): agent entry point and project invariants.
- [Demo and setup guide](docs/demo.md): runnable setup and actual readiness.
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

## Latest design update — October 23

- **No eyebrow headings.** Calm neutral interface; remove decorative crosshairs, repeated captions,
  large sound cards and inline history. Event history remains in its own view.
- **Defaults before customization.** Preset → search → a short queue/list of only custom rules;
  do not make people configure every sound. Explicit Ignore/tier 0 must survive preset changes.
- User wants full customization; supported sound coverage is a separate ML capability. Unsupported
  niche queries must say they require recognition support rather than pretending they already work.
- **Peripheral, icon-first cues** are the desired experience. Text optional for ordinary cues;
  urgent cues keep a label. Browser tier colors, still/gentle motion and mock edge placement are
  preview controls. White SSD1306 needs monochrome equivalents. No rapid flashing.
- OLED pixel dimensions do not establish full-field optical coverage. Confirm virtual-image placement,
  angular field of view and orientation with Yameen before promising a Fortnite-style full-field overlay.
  See [display UX](docs/display-ux.md) for the precise questions and fallback.
- Local mirror remains React-built. Taste guidance is now installed/applied. Mana built onboarding
  and its numeric-tier/search revision is visible; final source export is being reviewed. Do not import
  the first draft's string priorities. See [Mana handoff](docs/mana-onboarding.md). No Bridge pairing
  or live Mana→hardware connection is claimed.
- Offline device renderer is now implemented: original bitmap icons/font, one-bit frames, SSD1306
  page conversion, stale/duplicate/expiry/disconnect guards. Thirteen tests pass; no physical driver
  or display output is connected. [Handoff](docs/display-renderer.md).

## OLED image follow-up — October 23

- Close-up confirms visible GND/VCC/SCL/SDA labels and white-on-black graphics; controller/resolution
  still rely on the actual module specification. Manufacturer confirms SSD1306 128×64, I²C and 1KB
  one-bit display RAM. [Spec check](docs/hardware-stack.md#oled-photo-and-cad-follow-up--october-23).
- CAD includes an optical assembly, but no readable optical dimensions/FOV. It does not yet establish
  that an icon can appear at the edge of the wearer's entire field of vision. Ask for a through-optics
  test at the intended eye position; do not equate a zoomed OLED photo with wearable readability.

## Latest integration checkpoint — October 23

- [Work status](WORK-STATUS.md) lists actual worker/task states. Internal subagents are not separate
  teammate chats; their context is published through repo artifacts and notes.
- **Preview bug fixed:** each manual sound button starts an isolated mock preview; Play sequence
  retains interruption behavior. Receiver mode still follows backend priority. A dog Ignore override
  left by agent testing was removed from the current browser; future QA must restore test settings.
- Browser and OLED now share cue content/placement decisions and the same semantic Lucide icon.
  The canvas thresholds that icon to one bit. Do not claim this means physical firmware is connected.
- Mana's revised JSX is integrated under Set up Aware in the same local website. Presets, exceptions
  and appearance apply to the simulator; a tested Ignore rule was reset after QA. No Bridge pairing
  or live profile API exists. Provenance is saved under frontend/mana.
- Inference will move to **another Mac**. [Fresh setup](docs/mac-setup.md) records runtimes, assets,
  architecture caveat and recorded smoke test. Do not copy virtual environments across machines.
- New standing policy: check meaningful sponsor substitutions for every required API/storage/backend
  choice. Prefer low-cost, high-fit substitutions with worthwhile rewards; no unrelated prize features.
  [Prize-based matrix](docs/sponsor-decision-matrix.md) uses the supplied Oct 23, 9:55 PM snapshot.
- Final combiner supplied: listed BK-7, 25.4 mm diameter, 2 mm thick, 50:50 transmission/reflection.
  This does not determine virtual-image size, angular field, focus or the magnifying lens. Confirm with Yameen.
- Next requested backend slice: tier durations/prominence, dismiss/ack, ongoing-sound repeat suppression,
  Work/DND modes and explicit sound overrides. Design review started; current server behavior unchanged.

## Team update practice — October 23

- Commit and push coherent, verified slices frequently; main stays runnable and branch status stays explicit.
- Keep a short benefit sentence in onboarding. Put the fuller problem, motivation and impact story in
  the submission/pitch; keep the live mirror focused on detections.

## Tester onboarding correction — October 23

User-facing onboarding must not ask testers to download, copy or manage JSON. Settings save locally
automatically, and Start preview returns to the companion. Internal profile helpers remain for future
backend integration; the interface explicitly says glasses syncing is not connected.

## Communication idea review — October 23

The supplied discussion proposes optional name/attention-keyword triggers and short captions. Treat
this as a proposal, not a new committed feature or evidence of sponsor eligibility. Prioritize the
physical sound-to-cue loop, settings/policy integration and names. Captions can be companion-first
because 128×64 is constrained. Do not infer that nearby speech is addressed to the wearer. Revoicing,
voice cloning and continuous ASL translation are outside current weekend scope. No new model added.

## Alert engine, glasses client and companion redesign — October 23 (late)

- Receiver now decides effective tier from saved preferences (producers' tiers are legacy defaults).
  Behavior table, API and Pi steps: [alert engine](docs/alert-engine.md). Owner: Emma. Status: implemented.
- Shared contracts to review: `GET /display` envelope (+`show_labels`), `PUT /profile`, `POST /controls`,
  `name_called` with `confidence: null` accepted by `/events`. Existing `/state` fields kept.
- `DisplayState` now trusts a newer `state_sequence` for the same event (needed for resume and urgent
  extension); re-polled snapshots still cannot extend a cue. Icons `siren` and `clock` added. Glyphs and
  icons moved to `hardware/oled-assets.json`, shared with the browser preview (byte-identical, tested).
- Yameen: `python3 -m hardware.oled_client --sink ssd1306 --self-test` is the first wiring check;
  `--flip-x` if the combiner mirrors the image. Status: awaiting physical evidence.
- Companion redesigned around "What the wearer sees" per `.taste-skill/direction.json`; Scene illustration
  removed; Show my room uses the browser camera behind the cue (click-to-start, never recorded).

## Night lens redesign, direction, resolution and icons — October 23 (latest)

- Companion restyled ("Night lens"): dark lens is the page, Instrument Sans + Silkscreen, amber as the
  only signal colour. The live view now draws the glasses' own 128×64 frame (black = see-through), so
  the lens and the panel cannot disagree. Status: implemented.
- Panel layout: the direction is the position (icon hugs left/right/front/behind edge with an edge line;
  unknown stays centred). Tier changes only the box around the icon; the icon never moves with tier or labels.
  New 32×32 pixel icons from `hardware/icons.py`, also used for the site's sound buttons.
- Direction contract ready for spatial work: `direction_degrees` + `direction_confidence` on events;
  four sides, confidence ≥ 0.6; a two-mic worker should send null rather than guess front vs behind. Cues resolve by expiry, Dismiss, or `POST /look`
  (no head sensor yet; the UI's Look button simulates it). See docs/alert-engine.md.

## Snap to dismiss — October 24

- `finger_snap` added to `TARGETS` (tier 0, never displayed) with a provisional rule in both model policies
  (`Finger snapping`, threshold 0.3, 0.9 s cooldown via new per-rule `cooldown_seconds`). John/Leo:
  please measure it in the room; nothing in the benchmark covers snaps. Status: implemented, untuned.
- One snap dismisses only while a cue is showing (double-snap is a policy setting; 1 s hops make quick
  double snaps merge). Resolving shows a 0.6 s check mark at the cue's position on glasses and lens.

## Visual dismiss gesture replaces audio snap — October 24

- Decision (Emma): dismissing must be visual. Not everyone can snap loudly, and a real alarm would mask
  a snap. Thumbs-up held ⅓ s, seen by the glasses' camera (reported Oct 24) or the demo webcam,
  dismisses the showing cue; MediaPipe runs in the browser. Audio snap rule disabled, code kept.
- Yameen: please confirm the camera model/interface and whether it can appear to the laptop as a webcam.

## Design decisions recorded — October 24

Full reasoning, rejected alternatives and open questions from the redesign sessions:
[docs/design-decisions.md](docs/design-decisions.md).

## Real OLED driven by the receiver — October 24

- `glasses-pi` (Pi Zero W, Python 3.13): OLED answers at 0x3C. `scripts/glasses_up.sh selftest` drew six
  cues; `scripts/glasses_up.sh live` followed the Mac receiver through an SSH tunnel (receiver stays on
  127.0.0.1). Demo scene → recognizer → receiver → OLED, 40–118 ms receiver-to-display.
- Yameen's `detect-oled.service` (bear demo) shares the display. Pause it while testing live cues
  (`kill -STOP <pid>` as pi, resume with `kill -CONT`; stopping the unit needs sudo). Our client no
  longer switches the panel off on exit. Status: verified on hardware; optics/readability still untested.

## Add a note

```text
Date / author:
Decision or caveat:
Owner / affected interface:
Evidence or doc link:
Status: proposed | decided | implemented | verified | superseded
```

## Codex return audit — October 24

Reviewed Claude handoff and retained Night lens and shared renderer. Fixed browser-to-receiver routing,
held-gesture rearming, camera lifecycle, ordered profile saves and failed-save rollback. See WORK-STATUS
for exact evidence and remaining physical checks. Fortnite-inspired placement means direction controls
position around the available display edge; do not imply a full-field-of-view overlay or real spatial
inference from the current simulator.

## Hardware correction — October 24

The glasses have no camera. Optional POV camera video is a browser demonstration backdrop only.
Automatic hand tracking and the test thumbs-up button are removed from the app flow; manual Dismiss
and expiry remain. Earlier camera-on-glasses and physical gesture claims are superseded. Phone as
OS-exposed webcam is a possible demo input, not a verified direct phone-to-site streaming feature.

## Overnight software pass — October 24

See docs/overnight-verification.md for repeatable tests, fixes, screenshots and remaining acceptance gates.
Stress time is simulated, not hardware uptime. Camera/snapping remain inactive. Use one settings-owning
companion for the demo: automatic browser→receiver profile syncing has no cross-client conflict policy.
Shared policy/hardware changes now trigger frontend CI as well as Python checks.

## Simulator freeze checkpoint — October 24

See docs/simulator-freeze.md for D/E role coverage and docs/integration-revisit.md for blocked/deferred
checks. Latest: centered icon + compass arrows inside fixed right-side patch; category inheritance;
pending custom-sound requests; optional demo-camera gesture restored. Emma's live gesture trial was
finicky, so tune later and keep manual Dismiss. Phone connection is not built; it is the next focus
after phone type/flow is confirmed. One OLED alert at a time is the current decision.

### iPhone mirror — October 24

Emma chose iPhone displaying the same live alerts (not camera streaming). Read-only viewer implemented;
see docs/phone-mirror.md. Use Receiver mode on the laptop. Browser-only simulation is not cross-device.
Temporary LAN viewer requires an access key, blocks writes, and exposes only /api/state plus build assets.
Real Safari/network trial pending. Thumbs-up reliability tuning remains explicitly deferred.

### Continuity Camera and John's audio handoff — October 24

Emma confirmed same Apple Account and selected Continuity Camera for iPhone → laptop POV.
Use docs/iphone-camera.md. Camera device list now refreshes on device change and manually; setup
help is in the stage. Actual physical camera trial pending. The phone must stay locked for camera
use, so Safari alert viewing on that same phone is a separate mode.

Fetched John's johnaou/custom-sounds at 87aff0d and ran 14 targeted tests in isolation, all passing.
It is not merged: its older server must not replace the current priority/settings engine. Custom
per-ID identity, TS parser and OLED icon are key integration gaps. See docs/john-audio-review.md.

### iPhone camera working; microphone prepared — October 24

Emma confirmed USB Continuity Camera video works. Audio input is separate: Mac lists “Emma Microphone”
(index 0 this session) plus built-in Mac mic. Input-format check accepts 16 kHz mono float32 without
capture. Bounded microphone command is in docs/iphone-camera.md; live phone-audio trial not run yet.
This is a mono demo path, not validation of glasses stereo/spatial capture. Re-enumerate indices on reconnect.

### Leo spatial review / iPhone channel limit — October 24

Emma requested holding the phone mic test until spatial review. No mic capture started.
Reviewed Leo's lragogna/audio-triangulation at ff840bc: 17 synthetic tests pass; isolated simulator on
8878 with --no-audio (8766 is our alert receiver). Silence and one-channel input crash localize;
live capture adapter and measured head yaw remain absent. Full details: docs/leo-spatial-review.md.
Continuity's “Emma Microphone” advertises one channel, so it cannot supply Leo's two-channel TDOA.
Native iOS stereo/directional capture APIs exist but are a separate unvalidated capture experiment.

### Native phone direction investigation — October 24

Emma's phone: iPhone 15 Pro / iOS 26.6. John offered his iPhone 18 Pro and connected/trusted it.
Native spatial capture is worth trying: Apple provides live four-channel ACN/SN3D FOA buffers on
supported hardware. Continuity's mono feed does not expose them. Native source and test plan are in
native/PhoneSpatialProbe; preparation script uses Apple's licensed project shell in ignored .cache.
80 synthetic direction checks pass; unsigned iPhone build succeeds with installed Xcode 27.1.
Physical support/orientation/accuracy remain pending. Probe does not record, upload or control alerts.
Emma authorized Personal Team signing for device testing; account/provisioning details stay local.
John's observations stream at 8a440e1 passes six isolated tests; speech is in progress separately.

### Resumed integration — October 24

John’s `johnaou/integrate-audio-ui` (12dddc0) includes our latest branch and was fast-forwarded.
79 Python / 21 frontend tests, build and 10,000 engine parity steps pass. Hearing now and opt-in
teaching are integrated; all-model-label selection remains unfinished. Keep the responsive website
for judges and configuration, reuse it on phones; no separate native frontend planned. No mic started.
See HANDOFF-NEXT.md for the updated resume point.

### Live testing controls and inclusive alarm mapping — October 24

Emma requested repeat suppression be toggleable for name testing. Live → Show every detection
bypasses recognizer cooldowns and receiver acknowledgement/merge suppression, while preserving
priority, focus, pause and duplicate-event protection. Session-only; normal defaults return on restart.
Name recognition emitted/cooldown decisions appear under Hearing now; display decisions stay in Log.
The active MacBook mic recognizer is explicitly user-authorized.

Fire alarm and Smoke detector, smoke alarm now share the existing urgent smoke_alarm type and
Fire / smoke alarm label. Context suppresses a competing bell. Thresholds unchanged. Cached scores
show added false positives; details in reports/fire-alarm-alias-review.json. No claim of room accuracy.

Known settings caveat observed during this test: refreshing a companion with stale local onboarding
settings can reapply them to the receiver, including disabling a name configured elsewhere. Restored
Emma's previously active name/aliases after the refresh. Resolve receiver/browser initial ownership
before claiming multi-client settings synchronization is complete; avoid multiple settings owners.

### Alarm stop and glasses-only dismissal — October 24

Emma confirmed the glasses have no camera; keep phone-camera thumbs-up optional, and add opt-in
microphone Snap to dismiss. Its score >=0.8 and current-event target/latch guards are implemented,
but real snap accuracy remains unverified. A stronger clap or alarm may still confuse the model.
Ongoing fire/smoke cues clear after four seconds of continuous fresh below-threshold windows from
the same source, not immediately between beeps or on capture disconnect. No resolved/check mark
for automatic sound stop. Claude's solid triangles already render when supported direction exists.

Live test also exposed a stale parser closure after hot reload: receiver polling now depends on
parseSnapshot so new control fields reach the toggle immediately. Clicked snap off/on through UI and
verified both server states. Mic worker also now waits through queue timeouts instead of exiting on
_queue.Empty; missing audio still reports as not listening and is never treated as alarm quiet.

### Pi-only display deployment and 16-position arrows — October 24

Emma clarified: display code only on Pi, inference stays on Mac. Audited scripts/glasses_up.sh:
copy list contains only hardware/__init__.py, display.py, oled_client.py, oled-assets.json (plus
smbus2 wheel), not models/audio/website. Added 16 triangle positions at 22.5° steps with shared
baked pixels. Original four triangles unchanged. Receiver supplies optional bearing_degrees only
for supported direction; simulator has a separate explicit bearing selector. Spatial accuracy is
not improved by rendering more bins. Tests: 93 Python / 21 frontend / build; live mock 22.5° verified.
Pi hostname did not resolve, so not deployed to hardware. See docs/display-16-directions.md.
Emma chose to park snap recognition: switched snap_to_dismiss off. Keep manual Dismiss, optional
phone-camera thumbs-up and automatic alarm clear after sustained quiet.

### Catalog, Mana backend and centered simulator consolidation — October 24

Catalog selection now preserves recognized model labels, icon and per-ID tier; free text stays
pending. CLI and scenes run CustomRules with hot reload. Rain/Saxophone are selectable; Whistling
recorded integration emitted4 events with person/tier 3. The ONNX embedding path now installed and
matched original scores exactly on a checked recording. No model weights were fine-tuned.
Receiver-authoritative hydration and genuine edit revisions prevent stale browser reloads from
erasing names (live refresh held revision107 and retained the enabled name). Mana generated a
serialized read-before-write adapter, now used by the companion, with10 contract tests and a real
Python receiver/Rain→drop test. Private workspace source/provenance is recorded; no public sharing.

Retired movable edge-left/right/front/behind cue CSS and old cue renderer. All previews now use
centered OLED pixels and direction triangles; onboarding has16 explicit arrow bearings. Added
readability/mobile polish; skipped distracting dither over cues/data.

Emma explicitly requested TEMPORARY Domestic animals,pets → Dog barking, active in both policies.
This overrides dog-specific semantics and can show cats/pets as barking. Guarded Dog+bark-family
fallback is separately supported by cached-window evidence; zero-FP results do NOT cover the broad
demo override. Catalog scores remain provisional; there is no zero-false-negative guarantee.

Proposed50 named cues are in docs/proposed-50-cues.md, awaiting explicit approval before any new
symbols/default bundle are implemented. Pi remains parked until available; only display code deploys.

## Approved cue set and Claude review — October24

Emma approved 50 cue proposals. They now have unique 32px OLED symbols, curated synonym search
(including Baby crying), priority-before-add and up to 100 selections. Existing builtin alarm/name
routes retain their identity; custom groups carry cue_id and canonical icon. All 527 raw classes remain
available where not represented by curated groups; unsupported free text remains pending.
Claude reviewed/pushed this work as 00eac84; root then redrew bicycle bell, cracked glass and skid symbols.
Browser end-to-end acceptance used an isolated receiver: save/reload Baby crying/Attention → actual
recorded Zipformer positive → matching previews; Ignore and removal verified. Live profile preserved.
107 Python/44 frontend tests and 10,000 parity actions pass.13/16 recorded spotchecks qualify, with
breaking/clapping/footsteps misses and 34 cues lacking mapped recordings. No 50-class accuracy claim.
Live MacBook microphone is device 0 now; device 1 is speakers. Pi network remains disconnected.

## Recall preference — October 24

Emma explicitly prefers more related-sound false alerts over missing selected sounds. Catalog
choices require no teaching. Custom primary defaults are 0.15 and related-label fallbacks 0.25;
train horn accepts strong truck/generic horn evidence with uncertain wording, not a definite train.
Exact selected categories win over subtype fallbacks. Existing five selections updated; MacBook
mic currently device 1 (phone device 0). See docs/recall-first-matching.md for tests and limitations.

## First-use setup, Claude review and handoff to Pi microphones — October 24

Setup now starts with optional typed name/nicknames, already-active defaults and sound search; no
training recordings are required. Start Aware marks completion locally and opens Live. Optional
personal recordings are separated into Preferences. Ambient is a quiet unframed 2-second icon;
16-position direction triangles and Mac inference/Pi display split remain unchanged.

Optional Claude suggestions now call the real Haiku 4.5 API through the receiver. Session keys are
kept in receiver memory only and configured from a localhost Origin; no key belongs in Git.
GET/POST /setup/suggestions provides availability/reviewable suggestions; POST/DELETE
/setup/suggestions/key manages the memory override. Complete JSON fences are safely unwrapped;
malformed output, unsupported IDs/tiers and provider failures retain strict typed error codes.

Root verified an actual external sound-only response (Doorbell (2), Rain (1), Baby crying (3)), profile
unchanged, and an actual browser Review suggested sounds result without Apply. Checkpoint rerun:
132 Python/51 frontend tests + build pass; isolated Taste desktop/tablet/phone inspection gives
0 failures / 0 warnings and no overflow. Screenshots reviewed; minor mobile density notes are in
docs/onboarding-review.md. No live API key, user description or provider response body was recorded
in these docs. This docs review did not change live settings or start microphone capture.

User's latest priority is both Pi microphones first, then spatial work. Root owns the physical
capture checks. UI/provider verification is not evidence that physical Pi mics are connected or
synchronized. Only display/capture endpoint code belongs on Pi; inference remains on Mac.

## Pi microphone checkpoint — October 25

Both INMP441 microphones now capture using the stock compatible I²S MEMS driver and a small local
overlay. Config backed up before installation/reboot. User close-up trial confirmed two independently
responding channels at 48 kHz/S32_LE, with 14.82 dB and 21.65 dB channel advantages near the two mics.
Physical left/right labeling and spatial calibration remain undone; do not infer direction from
this capture test. No audio/credentials committed. See hardware/pi-capture/README.md.

## Pi primary input and conservative spatial scope — October 25

Emma clarified Pi stereo is the primary inference input; Mac microphone is explicit fallback.
Current meters alone do not switch recognition. Requested direction is left/right/unknown only,
with no front/back or distance claim. Physical channel mapping and real-room direction tests remain
required. Detailed step-by-step handoff: docs/pi-spatial-handoff.md. On hotspot return SSH resolved
again, but the existing level bridge remained disconnected; inspect capture lifecycle before claiming
it recovered. Do not restart receiver 8766 unnecessarily (Claude key is memory-only).

### Follow-up: Pi recognition is now active

Implemented audio/pi_input.py + audio.cli mic --pi. Single stereo capture feeds both recognition
and meters. Continuous antialias FIR converts 48k stereo to 16k mono on Mac; queue generations reset
on disconnect/gaps/overflow and burst backlog is rejected. Mac mic worker and standalone meter
bridge stopped. Site says Pi is selected; actual model windows/receiver observations verified.
13 Python capture tests, 57 frontend tests and build pass. A confirmed old orphan arecord needed
specific-PID SIGKILL after hotspot switch; failure/reconnect hardware acceptance is still pending.
Spatial estimator/calibration remains TODO; resume at step 2 of docs/pi-spatial-handoff.md.

## Pi spatial left/right implementation — October 25

Emma confirmed physical channel labels (0 left,1 right) and spacing approximately 11–13cm.
Mac spatial estimator uses constrained GCC-PHAT plus sensitive level difference, exact recognition
window association, and pulse-aware alarm handling; emits only -90/+90 or null to existing16 arrows.
Name direction stays unknown. Ordinary SSH batching now preserves model windows; real gaps drain/reset.
Two physical alarm trials are NOT a direction acceptance pass: first mostly unknown; second some
right windows but left unreliable. Latest -75dBFS spatial floor change needs a fresh physical trial.
51 regression tests +58 frontend tests/build pass. Receiver8766 not restarted (session key preserved);
phone spatial disconnected. See docs/pi-spatial-live.md for thresholds, evidence and limits.

## Live OLED, eight rough bearings and centered balance — October25

User confirmed actual live sound alerts on the real OLED. Numeric trial matched149/149 sampled
state/display event IDs; Fire/smoke showed0 and+45 degrees, but direction remained too often front.
User approved eight buckets and assuming front when unresolved. Implementation now uses front-branch
TDOA angle, median/45-degree buckets, explicit assumed-front metadata and level-only±45 fallback.
No rear-angle/distance claim. See docs/rough-front-angles.md for current policy and limits.
Dancing Bear PID1076 was SIGSTOP-paused at user's request; OLED client follows8766 over SSH.
No optics flips yet; --flip-x/--flip-y are ready for the mounted reflection review.
Centered reference measured−0.89dB left-minus-right; local numeric config sets gain_offset_db−0.89
and margin_db0.75. Active worker telemetry confirms those values. Old SIGINT-ignored worker was
actually replaced; explicit SIGINT/SIGTERM handlers now make future reloads graceful. Earlier feed
liveness did not prove changed thresholds loaded. Spatial accuracy remains unvalidated.

## Oct 25: dog override removed, attention calls added
- The TEMPORARY Domestic animals, pets → Dog barking override is gone from both policies: it raised
  "Dog barking" live for cats, pigs, horses and chewing. The guarded bark rule remains (docs/dog-label-audit.md).
- The name spotter also listens for attention calls ("Someone's calling") and "watch out" / "look out"
  (urgent "Watch out!"). See docs/design-decisions.md. Name cues now carry Pi stereo direction.


## October 25: offline setup cleanup and John handoff

- Hardware disconnected for assembly; no fresh capture started for UI verification.
- Defaults and Start precede optional configuration. Catalog sounds require a priority choice,
  with a local OLED preview. Ignore is blank; choices save only after confirmation.
- Finish waits for the latest edit's receiver confirmation, including reconnect/session changes.
- Isolated browser verified Baby crying Ignore + Accordion Notify persistence after Saved/reload.
- John owns SPACE-PHONE-01; see HANDOFF-JOHN.md and phone feasibility doc. Loose pocket orientation
  and independent clocks mean this is an experiment, not a ready third-mic triangulation feature.
- Concurrent Claude question feature is checkpointed in3a593dc; live acceptance still pending.


## October 25: recognizer automation and reflected optics session

- Reviewed Claude commits through7b2466d: Mana first-run steps, typed-sound Claude matching,
  Spidey Sense theme, Browser-only test controls and Live diagnostics moved to Log.
- Added scripts/recognizer.py for explicit Pi/Mac background start, stop, status and logs.
  Repeated starts are idempotent; source changes stop the managed old worker first. Older manually
  started workers are detected and left untouched to avoid duplicate capture. Runtime state/logs
  stay in ignored .cache/. No auto-start on login or silent Mac fallback.
- Reflection checks: docs/recognizer-controls.md. Use existing SSD1306 --flip-x/--flip-y flags
  only after wearer-view confirmation; do not swap microphone labels to fix mirrored text.
- At initial check the existing Pi recognizer PID79402 was alive but Pi hostname unresolved.
  Receiver8766 was responding; no inference/capture liveness claimed from process status alone.
