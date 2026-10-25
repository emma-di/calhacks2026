# Resume here — October 24 software checkpoint

Branch `codex/browser-mirror` (PR #2), everything pushed. Read AGENTS.md, then this. John owns audio/
signals ([HANDOFF-JOHN.md](HANDOFF-JOHN.md)); Emma + agent own the display/product.

## Latest: two Pi microphones verified — October 25

**Current live spatial settings:** [eight rough buckets / assumed front](docs/rough-front-angles.md).
Next mounted-hardware measurements: [direction calibration acceptance](docs/direction-calibration-acceptance.md).
Real Pi microphone→model→browser→OLED path exercised; user confirmed display works.149/149 sampled
state/display event IDs matched. Spatial accuracy is NOT validated; latest1.25dB sensitivity needs
room acceptance. Dancing Bear paused, OLED client following8766, repeat suppression OFF for testing.

**Next: [Pi recognition + left/right implementation handoff](docs/pi-spatial-handoff.md).**
Pi is now the primary recognition input; Mac mic is explicit fallback only. Current command:
`audio.cli mic --pi pi@glasses-pi.local --endpoint http://127.0.0.1:8766/events`.
One SSH capture feeds model + meters; former Mac mic and standalone meter workers are stopped.
Actual inference windows and receiver observations verified. Spatial left/right is now implemented
and running: [live spatial behavior and test status](docs/pi-spatial-live.md). Emma confirmed channel
mapping and 11–13cm spacing. First alarm trial was mostly unknown; beep-pause handling was adjusted
and needs a repeat physical trial. No front/back or fine-angle claim.
New left/right-only scope replaces speculative front/back; unknown means no arrow.
Meter UI/bridge implementation: [live levels](docs/pi-live-levels.md). 57 frontend tests/build pass;
13 capture/resampling/bridge tests cover levels, stale clearing, antialiasing and process lifecycle.

I²S capture driver installed with original bootconfig backed up on Pi at
/home/pi/aware-mic-backup-20261025-000106/config.txt. Device AwareINMP441 now captures 48 kHz, S32_LE,
stereo. Near-each-mic 20s test shows independent response: channel 0 +14.82 dB at first mic,
channel 1 +21.65 dB at other. No reported overruns. Physical left/right identity not yet mapped;
spatial testing/calibration remains separate. See reports/pi-stereo-mic-check.json and
hardware/pi-capture/README.md. No raw audio/transcripts/credentials committed; inference stays on Mac.

## Latest: first-use setup and real Claude suggestions

First use now opens Preferences with optional typed name/nicknames up front, defaults already set,
and supported-sound search for exceptions. Start Aware saves a local completion flag and opens Live;
later visits open Live, with explicit view links preserved. No training or personal recordings are
required. Optional recordings are in Preferences, outside Live. Ambient remains a frame-free icon
for two seconds; centered icons and existing 16-position triangles remain unchanged.

Claude suggestions are implemented through the local receiver with review before Apply. User-entered
API keys stay in receiver memory only; localhost-origin key routes are required. Haiku 4.5 was verified
with an actual external sound-only request (Doorbell (2), Rain (1), Baby crying (3)), plus a browser review result;
neither test applied suggestions to the live profile. Strict bounded parsing accepts a complete JSON
fence but rejects malformed/unsupported output with specific error codes. Never commit credentials.

Fresh verification: 132 Python tests, 51 frontend tests, production build pass. Taste inspector at
1440/768/390 passes with 0 failures / 0 warnings with no horizontal overflow; screenshots reviewed. Details and minor
phone polish: [onboarding review](docs/onboarding-review.md). UI source is built; physical two-mic
capture is not certified by these checks. Current user priority: connect/test both Pi mics first;
root agent owns hardware, spatial work follows verified capture. Inference stays on Mac.

## Latest: recall-first selected sounds

Emma requests fewer misses even at the cost of related-sound false alerts. Custom catalog threshold
is now 0.15; 11 cue groups have explicit related-label fallbacks 0.25. Train horn catches strong
truck/vehicle horn evidence with label “Horn — possibly train,” retaining the chosen icon/tier.
No teaching is required for catalog sounds. Existing five selections updated through profile API;
MacBook mic device 1 currently (phone is device 0). Enumerate devices before restarting.
112 Python/45 frontend tests and build pass; 16/16 inspected recordings qualify, not independent accuracy.
See docs/recall-first-matching.md. Old 13/16 results below are historical. Pi remains disconnected.

## Latest software consolidation (read before older snapshots)

Catalog picker + backend rules + per-ID priorities + icons are connected, including Rain/Saxophone.
Free text remains pending. Recorded Whistling passes and Mana adapter→Python→Rain/cue_rain/tier 3 passes.
Mac optional custom-head dependencies installed; audio worker now runs embedding path + catalog.
Profiles hydrate from receiver, only genuine edits save; cold reload verified without name loss.
Mana-generated adapter is imported by the companion and preserves Ignore0, learned names and failures.
Legacy directional alignment is retired: centered icon/box +16-position triangle in all previews.
Site contrast/mobile/diagnostics polished without dither over meaningful data.

TEMPORARY user-requested Domestic animals,pets → Dog barking is active in both policies; do not claim
this is dog-specific. Guarded fallback evidence is separate (docs/dog-label-audit.md). Snap OFF.
Current mic is explicitly user-authorized and running; receiver 8766, site 5174. No Pi until later.
Remaining acceptance: real-room names/false positives/misses, selected-sound sensitivities, second
Mac portability, phone-direction calibration and physical optics once hardware returns.
Emma approved the 50 cues; implemented and pushed in 00eac84 (Claude committed the Codex work).
50 distinct symbols and curated search are ready. See docs/cue-catalog-verification.md.
Browser acceptance: isolated Preferences → Baby crying/Attention → save/reload → real recorded
Zipformer positive → cue_baby_cry in both previews; Ignore suppresses, removal stops recognition.
107 Python/44 frontend tests, 759 raster fixtures, 10,000 parity actions pass. 13/16 recorded spotchecks
qualify; breaking/clapping/footsteps miss provisional thresholds. 34 cues lack mapped recordings.
Do not describe this as 50-sound accuracy certification. Bicycle recognition stays disabled.
Current live mic device 0 is MacBook Pro Microphone (device 1 is speakers); enumerate devices on restart.
See docs/audio-software-readiness.md and docs/mana-onboarding.md for current evidence.

## Latest: 16 display positions, Pi scope, snap parked

Snap is OFF by Emma's decision; keep manual Dismiss, optional phone-camera thumbs-up and alarm
quiet clearing. Fine display directions now use 16 baked positions around the centered icon,
preserving the original four cardinal arrows. No confidence/direction means no arrow. See
docs/display-16-directions.md for the protocol, gallery and exact Pi-only copy list. Inference stays
on Mac. Pi unreachable by hostname, so no physical deployment yet. 93 Python / 21 frontend tests
and build pass; 22.5-degree mock cue checked in the live site with source=mock.

## Latest: ongoing alarms, solid triangles, and snap input

Fire/smoke cues now clear after four seconds of continuous fresh same-source below-threshold
observations (not on a single missed window or disconnect). Snap to dismiss is a session opt-in,
gated by a strong model score and a current-cue target; camera thumbs-up remains independent.
Real snap recognition still needs the wearer/room trial. Unknown direction still has no triangle;
Claude's solid arrows are already in both renderers. See docs/alert-engine.md for precise semantics.

## Latest: name testing and fire alarm aliases

Live has a session-only **Show every detection** toggle. It bypasses recognition cooldowns (including
names) and receiver repeat merging/acknowledgement; all other priority/mode rules stay active.
Current user-authorized MacBook microphone recognition is running; use receiver 8766 and site 5174.
Hearing now includes name emitted/cooldown diagnostics. Controls reset on receiver restart.
Both models now map Fire alarm + Smoke detector, smoke alarm to the existing urgent type;
label is Fire / smoke alarm. Cached-score false-positive tradeoff is recorded in
reports/fire-alarm-alias-review.json; user’s actual fire-alarm recording still needs a repeat trial.

## Codex integration checkpoint — October 24, resumed session

John's `johnaou/integrate-audio-ui` at `12dddc0` already merged our `2a443a6`; fast-forwarded
it into `codex/browser-mirror`, preserving the latest receiver, spatial routes and solid OLED triangles.
It integrates custom-sound teaching, per-custom-ID acknowledgement/queue identity, improved name
spellings, Live → Hearing now, and an opt-in browser microphone meter/teaching controls.

Fresh checks: 79 Python tests, 21 frontend tests, production build, and 10,000 cross-language engine
steps passed. Initial sandbox socket errors disappeared when HTTP tests ran with localhost permission.
No microphone was started. Physical connections/room accuracy remain separate acceptance checks.
Corrected Hearing now's command to receiver port 8766 (old command pointed at 8765).

Any-sound catalog plumbing below is STILL incomplete: taught custom sounds are now integrated, but
selecting the pretrained catalog's 527 labels from Preferences is not. John's identity/parser/OLED
changes satisfy parts of the older six-step list; inspect current code before reimplementing them.
Live Hearing/Teach sections now exist; further live-view refinement should build on those.
Do not apply a blanket two-window gate to short knocks/bells without recorded positive/negative tests.

Product decision: keep the responsive web companion for judge visibility, setup and diagnostics;
phone viewing can reuse the same web UI. A separate native UI is not needed for this purpose.
Native phone audio capture remains a separate hardware capability experiment.

## Done today (verified)

- **Real glasses work end to end.** `glasses-pi` (Pi Zero W, SSD1306 at 0x3C). `scripts/glasses_up.sh selftest`
  draws fake cues; `scripts/glasses_up.sh live` follows the Mac receiver over an SSH tunnel (receiver stays
  on 127.0.0.1). Scene/mic → recognizer → receiver → OLED in ~30–130 ms. SSH key login set up.
- **Panel design:** centered icon, **solid triangle** on the sound's side (none when unknown), tier = box.
- **John's name detection integrated** (his `audio/names.py`, v2 `name_called`, 0.2 s mic blocks). Verified:
  synthetic "Hey Emma" → "Your name" on the real OLED. Needs `sentencepiece` and
  `python -m audio.download_model --names` (done on Emma's Mac). Name comes from Preferences.
- **Signal panel** ("What it's hearing", Log page) on John's observations format; `/health.capture.listening`.
- **Simulated scenes:** `python -m audio.scene audio/scenes/demo.json --receiver http://127.0.0.1:8766`.
- Phone spatial handed to John ([docs/phone-spatial-handoff.md](docs/phone-spatial-handoff.md)).

## First thing on resume: check John's live audio → signal work

John has been getting live audio → signal translation working. On resume: `git fetch` and look at his
newest `johnaou/*` branch before building more. Port it onto the current receiver (as with observations
and names — don't merge his older server.py), then **post-process** the signals as needed, e.g.:
- smoothing / requiring 2 consecutive windows above threshold before alerting (fewer one-off false alarms);
- per-sound thresholds tuned with the signal panel on the real mic (alarm_clock 0.05 and knock/bell 0.075
  are very low);
- hysteresis so an ongoing sound stays one cue (the engine already merges repeats; check timing);
- confidence floor or ignore lists for background classes (speech, music) unless the person picked them.
Verify with `audio/scene.py` plus the live mic, watching the signal panel and the real glasses.

## In progress: pick ANY sound the model knows (feature 1+2)

Built and committed, **not wired in yet**:
- `audio/sound-catalog.json` (generated by `audio/build_sound_catalog.py`): all 527 model sounds with a
  friendly name, category and glasses icon.
- 10 new 32×32 category icons in `hardware/icons.py` (person, paw, music, cloud, drop, car, house, gear,
  bang, wave), baked into `hardware/oled-assets.json`; render fixtures regenerated (byte-identical in browser).
- `audio/custom_rules.py`: reads `custom_sound_requests` entries with `status: "recognized"` +
  `model_labels` from the shared profile, hot-reloads within 2 s, emits John's custom event
  (`type: "custom"`, `custom_sound_id`, person's label) plus `icon_id`. Default threshold 0.25 (untuned).

Remaining steps, in order:
1. `audio/alerts.py` `validate_profile`: accept `status: "recognized"` with `model_labels` (1–4, must be in
   the catalog) and `icon`; keep `pending` for free text. Mirror in `frontend/mana/AwareOnboarding.jsx`
   `sanitizeCustomSounds` (it currently forces `status: "pending"`).
2. `audio/events.py` `validate_event`: accept `type: "custom"` (schema 1, `custom_sound_id` ≤120 chars,
   label ≤120, optional `icon_id` in the icon set).
3. Engine identity, both `audio/alerts.py` and `frontend/src/lib/alerts.ts`: use a key
   `custom:<custom_sound_id>` (else `type`) everywhere `event['type']` keys acks / merge / queue
   (alerts.py lines ~188, 233–267); effective tier = the profile entry's tier; presentation
   `icon_id = event.icon_id or policy icons[type]`. Add a shared scenario: two different custom sounds
   neither merge nor acknowledge each other.
4. `audio/cli.py` and `audio/scene.py`: `CustomRules().detect(scores, source, now, ts)` after the Detector;
   add its `decisions` to the observation's rule decisions so the signal panel shows them.
5. Site: `frontend/src/components/Oled.tsx` + `Cue.tsx SoundIcon` use `event.icon_id` for custom events;
   `events.ts` parse `custom` + `icon_id`. In onboarding's sound search, list catalog matches ("Saxophone ·
   Music") above "Request as custom sound"; picking one saves `status: "recognized"`, `model_labels`, icon.
6. Test: add "Whistling" in Preferences, play `samples/speech_whistling2.wav` with
   `python -m audio.cli file samples/speech_whistling2.wav --realtime --endpoint http://127.0.0.1:8766/events`
   → person icon on the glasses.

## Next after that: live-first Receiver view (feature 3, Emma's priority)

Simulator keeps manual test sounds + simulated direction. **Receiver view = the real product:** compact live
"what it's hearing" strip, Listening / glasses status, direction source (phone / none), signal settings; move
manual test buttons into a collapsed "demo tools" section.

## Running on Emma's Mac / Pi right now

- Receiver `127.0.0.1:8766`, site `127.0.0.1:5174`, phone USB bridge, glasses live client (Terminal tab
  "Glasses live"). Old Codex receiver :8765 / site :5173 are stale — ignore.
- **Yameen's bear demo is FROZEN (SIGSTOP), not stopped.** To restore: Ctrl-C the glasses live client, then
  `ssh pi@glasses-pi.local 'kill -CONT $(pgrep -f oled_hello_bear.py)'`. Stopping the unit needs sudo.
- Mac is on the Pi's hotspot network (172.20.10.x).
