# Mana prompt: onboarding revamp (October 25)

Paste the prompt below into the existing **Aware** build conversation in Mana and attach the current
`frontend/mana/AwareOnboarding.jsx` (the integrated version, not Mana's older export). Save Mana's
output unchanged as `exports/aware/AwareOnboarding.jsx` in the workspace and send the file back; we
record its hash in `frontend/mana/provenance.json` before any local fix.

---

Revise the attached AwareOnboarding.jsx (the integrated version we run today) into a first-run flow a
brand-new person completes top to bottom. Keep it one React component file with the same default
export and props: `{ onChange, onComplete, theme, receiverProfile, firstUse, canFinish }`.

**Who it is for.** Someone hard of hearing setting up Aware glasses for the first time. They should
finish in under a minute and only see choices that matter. Everything else keeps its default and
stays out of the way.

**Order (chronological, numbered steps on one page, no wizard pages):**

1. **Your name — required, at the top.** One "Your name" field (required; Start stays disabled until
   it has letters). After a name is entered, show an optional "Nicknames" field (comma separated).
   Under it, one checkbox already on: "Also show what they ask right after your name" with the help
   text "The next few seconds are transcribed on this laptop. Audio is never saved." (draft.questions).
2. **Everyday alerts are ready.** A compact read-only list of what already alerts and how strongly:
   Fire/smoke alarm (Urgent), Siren (Attention), Your name (Attention), Door knock (Notify),
   Bell/chime (Notify), Dog barking (Ambient) — read the tiers from the selected preset and rules, do
   not hardcode them. One quiet "Adjust" disclosure holds the Gentle / Balanced / Active preset choice
   and the per-tier summary. No other controls in this step.
3. **Sounds that matter to you — optional.** Keep the existing behavior exactly: the six common
   choice buttons, the search box with curated matches, "More model labels", the priority picker with
   the OLED preview when adding a sound, "Ask Claude to find …" when nothing matches (with its
   matches list and the person's own words kept as the label), and "Save as pending". Show the
   person's added sounds ("Your sounds") directly under the search, with priority select and Remove.
4. **Start Aware** — one primary button at the bottom (label "Start Aware" when firstUse, otherwise
   "Done"). Disabled until a name exists, nothing is mid-add, and canFinish is true; the help text
   under it says which of those is missing. Remove the earlier Start button near the top.

**Below Start, one collapsed "More settings" disclosure** (open automatically when the URL has
`?connect=claude`) containing, in this order: "Shorten questions with Claude"
(draft.question_paraphrase, disabled unless draft.questions), the existing SetupSuggestions block
(Claude key connection and "describe your day" suggestions), Category defaults, Display preferences
(labels, colors, motion, preview), and Reset preferences with its confirm step. Change the Ask Claude
error for a missing key to say the key is connected under More settings.

**Must not change:** every exported helper and constant (buildAwareProfile, sanitizeAwareDraft,
AWARE_PRESET_DEFAULTS, AWARE_EVENTS, applySuggestedCues, resolveAwareTier, etc.) and their behavior;
the profile shape sent through onChange; numeric tiers 0–4 including Ignore 0; the receiver
hydration effect; the existing Oled/SoundIcon/SetupSuggestions imports; localStorage keys; the inline
style system and palette. No new dependencies. No eyebrow headings or decorative HUD chrome; calm,
plain copy; accessible labels, aria-live status, keyboard-reachable controls, and reduced-motion
support stay.
