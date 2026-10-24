# Mana onboarding integration

Status: Mana-built onboarding is integrated into the local Aware website under **Set up Aware**.
Its presets, explicit sound exceptions and display choices control the browser simulator. Both preview
renderers use the same Cue/Oled components as the companion. It does not save to the Python engine,
physical glasses or a cloud profile API. The mirror itself remains locally authored React.

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
- Local draft status and profile JSON export; no implication that saving controls a live device.
- Display settings stay outside the proposed profile JSON until a display schema is agreed.
- Icon-first ordinary cues, urgent labels, optional labels/colors/motion, clear mock-direction labeling.

## Source handoff

The revised export is checked into `frontend/mana/AwareOnboarding.jsx`; `provenance.json` records
its original hash and local adaptations. The adapter removes Mana-only globals and forwards draft
changes to the simulator. Numeric preset defaults have one source shared with the simulator.
The component stays mounted while hidden so saved preferences apply on page load. Draft storage is
browser-local; display preferences are separate from the proposed profile export. Names are settings,
not a working speech detector. Gentle/Active presets are provisional product defaults.

A brief benefit sentence lives in onboarding; the detailed motivation belongs in the pitch/submission.

Next integration is a deliberate saved-profile API, not a public tunnel to the diagnostic receiver.
Mana Bridge has not been installed/paired. Sponsor eligibility and public submission requirements
still need official verification.
