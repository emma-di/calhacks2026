# Mana onboarding integration

Status: Mana-built app exists; numeric-tier/defaults-first revision is under review. It is not connected
to the running Python engine, physical glasses or a cloud profile API. This is actual Mana UI work;
the existing browser mirror remains locally authored React.

## Workspace artifacts

- App: `Apps → Aware` in Emma's signed-in Mana workspace.
- [App link](https://www.mana.space/home/aQEUv8A1Q3QQmwezqlUHKlrMXR42/apps/Aware)
- [Build conversation](https://www.mana.space/home/aQEUv8A1Q3QQmwezqlUHKlrMXR42/apps/Aware?chatId=00179281825133699224190a85845a09d30)

These are workspace links, not verified public judge links. Do not assume teammates or judges have
access. No sharing settings were changed. The first generated draft used string priorities; it must
not be imported. The revision requires numeric tiers 0–4 and generic Bell/chime labeling.

## Required behavior before integration

- Preset defaults first; optional name/aliases; search and add only explicit sound overrides.
- Numeric tier 0 remains a real Ignore override, not a falsey “use default.”
- Switching preset preserves overrides; removing a rule restores default and removes it from export.
- Unknown niche queries explain model support; they do not create recognition capability.
- Local draft status and profile JSON export; no implication that saving controls a live device.
- Display settings stay outside the proposed profile JSON until a display schema is agreed.
- Icon-first ordinary cues, urgent labels, optional labels/colors/motion, clear mock-direction labeling.

## Source handoff

Mana reports a standalone React export at `/cloudspace/exports/aware/AwareOnboarding.jsx` in **its**
workspace, not this local checkout. A downloadable export has been requested. Review it for numeric
contract compatibility, undefined Mana globals, keyboard behavior and unsupported capability claims
before adding it to the runtime. Keep provenance if adapting the exported component into this repo.

Next integration is a deliberate saved-profile API, not a public tunnel to the diagnostic receiver.
Mana Bridge has not been installed/paired. Sponsor eligibility and public submission requirements
still need official verification.
