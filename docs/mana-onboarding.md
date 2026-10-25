# Mana onboarding integration

Status: Mana-built onboarding is integrated into the local Aware website under **Set up Aware**.
Its presets, explicit sound exceptions and display choices control the browser simulator. Both preview
renderers use the same Cue/Oled components as the companion. It now saves explicit edits through the Mana-generated receiver adapter to the local Python profile API;
that profile controls real alerts. No cloud profile service or Bridge pairing is required. The mirror itself remains locally authored React.

## Workspace artifacts

- App: `Apps → Aware` in Emma's signed-in Mana workspace.
- [App link](https://www.mana.space/home/aQEUv8A1Q3QQmwezqlUHKlrMXR42/apps/Aware)
- [Build conversation](https://www.mana.space/home/aQEUv8A1Q3QQmwezqlUHKlrMXR42/apps/Aware?chatId=00179281825133699224190a85845a09d30)

These are workspace links, not verified public judge links. Do not assume teammates or judges have
access. No sharing settings were changed. The first generated draft used string priorities; it must
not be imported. The revision requires numeric tiers 0–4 and generic Bell/chime labeling.

## Implemented behavior

- Preset defaults first; optional name/aliases; search and add only explicit sound overrides.
- Numeric tier 0 remains a real Ignore override, not a falsey “use default.”
- Switching preset preserves overrides; removing a rule restores default and removes it from export.
- Unknown niche queries explain model support; they do not create recognition capability.
- Automatic browser-local saving and Start preview; no JSON download or technical profile UI.
- Display settings stay outside the proposed profile JSON until a display schema is agreed.
- Icon-first ordinary cues, urgent labels, optional labels/colors/motion, clear mock-direction labeling.

## Source handoff

The revised export is checked into `frontend/mana/AwareOnboarding.jsx`; `provenance.json` records
its original hash and local adaptations. The adapter removes Mana-only globals and forwards draft
changes to the simulator. Numeric preset defaults have one source shared with the simulator.
The component stays mounted while hidden so saved preferences apply on page load. Draft storage is
browser-local; display preferences are separate from the proposed profile export. Typed names now drive the integrated streaming name spotter on the Mac. Gentle/Active presets are provisional product defaults.

A brief benefit sentence lives in onboarding; the detailed motivation belongs in the pitch/submission.

The saved-profile API is now integrated, without a public tunnel to the diagnostic receiver.
Mana Bridge has not been installed/paired. Sponsor eligibility and public submission requirements
still need official verification.

## October 24: Mana-generated backend adapter (integrated)

In the same Mana build conversation, requested a narrow receiver adapter without replacing the app.
Mana generated frontend/mana/awareReceiverAdapter.js and its 10 contract tests. Original generated
JavaScript is preserved; its hash and source path are in frontend/mana/provenance.json. The companion
uses it for profile reads and serialized read-before-write saves. It preserves Ignore0 and unknown
name fields, validates numeric tiers, propagates failures, and requires a saved revision increment.
The local ProfileEdits helper supplies only genuine user patches; cold localStorage restores do not
write to the receiver. Backend PUT still lacks compare-and-swap across truly simultaneous writers.

Verified adapter → real isolated Python receiver → selected Rain rule → tier3/drop icon →1024-byte
OLED frame via scripts/verify_mana_receiver.py; evidence reports/mana-backend-integration.json.
Recorded Whistling → classifier → selected catalog rule → receiver/person icon also passed separately.
This is substantive Mana onboarding/backend integration; it is not a claim that Mana runs audio,
controls I2C, or that the private workspace links are publicly judge-accessible. Public submission
links and official eligibility remain to be confirmed; no sharing/publishing settings changed.

## October 25: Mana revamped onboarding into a first-run flow (integrated)

Prompt: [mana-onboarding-revamp-prompt.md](mana-onboarding-revamp-prompt.md), sent in the same Aware build
conversation with the integrated file attached. Mana returned a four-step page a new person completes
top to bottom: 1 required name (nicknames and question capture appear after it), 2 read-only everyday
alerts with a quiet Adjust, 3 optional sounds (search, common choices, Ask Claude, Your sounds), 4 one
Start button that says what is blocking it, then a collapsed More settings (Claude shortening and key,
suggestions, category defaults, display, reset). Mana kept every line above the component byte for byte
and found a real bug: the questions checkbox showed off for new drafts although the profile treats a
missing value as on. The generated file is checked in unchanged (sha256 in provenance.json); only three
local render tests were updated to the new order. For the Mana track the workspace app and chat must be
made public by Emma; no sharing settings were changed here.
