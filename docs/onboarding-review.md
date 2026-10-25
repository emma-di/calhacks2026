# Onboarding and Claude suggestions checkpoint

October 24, 2026. This records implemented software and observed checks; it does not certify
physical microphone capture, sound accuracy, or glasses connectivity.

## Current user flow

A fresh browser opens **Preferences → Set up Aware**. Name and nicknames are optional typed fields
at the top; no recordings or per-user training are required. Common alert defaults are already set.
Users can search the curated sound catalog, choose a priority, and add only their exceptions.
Advanced model labels remain available; unsupported free-text requests stay pending rather than
pretending to recognize a newly named sound. Bicycle subtype recognition remains gated.

**Start Aware** records `aware-setup-complete-v1` in this browser and opens Live. Later visits open
Live unless the URL explicitly requests `?view=preferences`, `?view=live`, or `?view=log`.
Entry routing is in `frontend/src/lib/setupEntry.ts`; this flag is navigation state, not a profile
or microphone permission. Preferences remain editable afterward. Receiver-authoritative hydration
and explicit-edit synchronization preserve live name settings on refresh.

Optional personal recordings are behind a separate disclosure in Preferences and are not required
by onboarding. They no longer occupy the main Live screen. Live inference still requires a running
recognition worker; completing setup does not silently start microphone capture.

Display vocabulary is unchanged: Ambient is a quiet icon with no frame, clearing after two seconds.
The centered icon and existing 16-position direction triangles remain shared between browser and
Pi renderer; unknown direction remains unknown. Pi deployment contains display code; inference
stays on the Mac.

## Claude is optional, real, and reviewable

The setup disclosure can suggest a few relevant sound exceptions from a description of the user's
routine. The local receiver calls Anthropic; Claude is not in the continuous recognition or alert
path. The selected, actually exercised model is **Claude Haiku 4.5**
(`claude-haiku-4-5-20251001`). Manual sound selection works without provider configuration.

| Route | Purpose |
| --- | --- |
| `GET /setup/suggestions` | Availability/model configuration; not proof of a completed provider request |
| `POST /setup/suggestions` | Submit a description and return bounded, validated suggestions for review |
| `POST /setup/suggestions/key` | Set a session API key from a loopback client with a localhost Origin |
| `DELETE /setup/suggestions/key` | Clear the in-memory override; a configured environment key may remain |

The companion reaches these through `/api`. A user-entered key stays only in receiver-process
memory, is not persisted to disk/browser storage/Git, and clears on receiver restart. The password
field is not part of exported settings. An optional `ANTHROPIC_API_KEY` server environment value is
also supported. Never put a key, private routine description, or provider response body in a commit.
The request sends the submitted description and public cue catalog; it sends no raw audio,
learned name data, or current private profile.

Suggestions are validated against supported catalog IDs and tiers 0–4, capped at eight entries,
and displayed for explicit review. Existing sound choices, including Ignore, are preserved when
selected suggestions are applied. Asking for suggestions itself never updates the profile.
A whole-response JSON markdown fence is safely unwrapped before strict parsing; arbitrary prose,
partial JSON, unknown fields, unsupported IDs and invalid tiers are rejected. Provider refusal,
incomplete response, authentication, rate limiting, timeout, model/configuration, malformed JSON
and invalid content return distinct error codes. No failure silently changes settings.

## Observed verification

- Full suite rerun: **132 Python tests**, **51 frontend tests**, and the production build pass.
  Local HTTP tests were permitted; this verification did not start microphone capture.
- Root agent completed an actual external, sound-only provider request: Doorbell/Notify (2),
  Rain/Ambient (1), and Baby crying/Attention (3) returned. The profile remained unchanged.
- Root agent completed an actual browser request and saw **Review suggested sounds**. No Apply
  action was performed against the live profile during that check. Availability alone is not
  counted as provider success.
- Existing first-use tests cover fresh setup routing, completed routing, explicit links, name-first
  order and the finish action. Suggestion tests cover strict validation and applying reviewed
  selections while preserving existing choices.
- Taste inspection of `http://127.0.0.1:5174/?view=preferences` passed at **1440×900**, **768×1024**
  and **390×844**: **0 failures, 0 warnings, 0 horizontal overflow** at all three sizes.
  Existing brand cream and exact OLED preview borders were allowed deliberately. Instrument Sans
  loaded, and “Set up Aware” stayed on one line at all sizes.

Reproduce the automated checks:

```sh
.venv/bin/python -m unittest discover -s tests -q
npm test --prefix frontend
npm run build --prefix frontend
```

Local visual artifacts from this review are in `/tmp/aware-onboarding-review/` (`report.json`,
`desktop-fold.jpg`, `tablet-fold.jpg`, `mobile-fold.jpg`, and full-page contact sheets). They are
verification artifacts, not required deployment files or exported user profiles.

## Visual review

ROUND 1

Seen in one second: the setup title and optional typed name; the product identity remains in the
shared shell. Idea: personalize an already-working alert vocabulary instead of building a classifier.
Live thing: search a supported sound, choose its priority, and review optional Claude suggestions.
Layout: shell=compact navigation / name=two-column form that stacks on phone / defaults=disclosure /
suggestions=disclosure / sounds=search and selected list / finish=single primary action.

Opened and reviewed desktop, tablet and phone fold screenshots plus the phone full-page sheet.
Desktop and tablet keep the compact name grid and search within the initial viewport. Phone fields
stack cleanly, labels remain readable, and no text or control crosses the viewport edge. The actual
selected cue symbols make the choices specific to Aware; the page does not need decorative dither
or animation over settings or OLED data.

Scores, using app-screen criteria: design 7.5 · usability 7 · creativity 7 · content 8 → overall 7.3.
This is a functional settings screen, not a marketing-page imagery exercise. No inspector cap applies;
Start Aware being below the initial fold limits the usability score to 7.

Remaining polish, not blockers for the current hardware lane:

1. On phone, shared navigation/status occupies roughly the first 230 pixels before the setup title.
   A later shell pass could consolidate the status row; this review did not alter shared source code.
2. A long selected-sound list pushes Start Aware well down the phone page. A future compact finish
   affordance could reduce that scroll without making users configure every catalog sound.
3. Disabled quick-pick labels wrap on narrow phones. They fit without overflow, but their “added”
   state could be presented more compactly in a later visual pass.

## Handoff boundary

Onboarding, optional provider suggestions, and the software checks above are implemented and
verified. They do not prove a physical two-microphone path. The current next lane is connecting and
validating the **two Pi microphones first**; spatial estimation comes afterward. The root agent owns
that hardware work. Verify device enumeration, actual captured channels and synchronization before
claiming direction support. Do not deploy inference models or website code onto the Pi.


## October 25: defaults-first setup and save confirmation

Supersedes the earlier layout/next-lane snapshot above. Hardware is disconnected for assembly;
this review used an isolated receiver and temporary profile, without microphone capture.

- Everyday defaults and Start Aware now appear before optional name, search and Claude suggestions.
- Both curated and raw model-catalog choices open an explicit priority chooser before saving.
- The chooser previews the actual cue at the OLED aspect ratio; Ignore renders blank. This local
  preview never publishes a fake recognition event.
- Start is disabled while a sound choice is unfinished or the latest receiver save is unconfirmed.
  Revision/session-aware sync prevents an older successful save from confirming a newer edit.
- Browser verification: name saved; Baby crying set to Ignore; Accordion set to Notify; both
  persisted after the Saved confirmation and reload; Start opened Live. Reloading before a pending
  save finishes can still abandon that save. Wait for confirmation.

Final combined checks: 176 Python tests, 64 frontend tests and the production build pass.
Python HTTP tests required local socket access outside the restricted sandbox. Visual inspection at desktop1440, tablet768 and
phone390 pixels showed no horizontal overflow or console errors. The inspector reported zero
failures and one below-fold warning: optional customization intentionally continues below the
first viewport while defaults and the primary action remain visible. Existing brand cream text
and hairline borders were allowed. Local artifacts:
/tmp/aware-onboarding-streamlined-review-final/ (report.json and viewport screenshots).

The concurrent question-after-name feature is checkpointed separately in commit3a593dc. Its
physical speech-to-OLED acceptance remains a live hardware test, not a result of this UI review.
