# Design decisions and discussed features

Record of the product and interface decisions from Emma's October 23–24 sessions, with the reasoning
and the alternatives that were rejected. Status words: **built** (in `codex/browser-mirror`),
**proposed** (agreed direction, not built), **open** (needs a team decision). Implementation detail
lives in [alert engine](alert-engine.md), [display renderer](display-renderer.md) and the
[frontend guide](../frontend/README.md).

## Who the screen is for

- **Judges first.** The Live screen answers one question: *when a sound happens, what does the wearer
  see, and why?* Everything a judge needs fits one 1440×900 screen: the lens, the reason line, the
  sounds to try, the mode controls. **Built.**
- **Explain every decision in plain words.** Each engine outcome has a one-sentence reason ("Dog barking
  skipped: Door knock matters more right now"), shown under the lens and in the log. This is how the
  alert logic becomes visible in a demo. **Built.**
- **No JSON or technical setup for testers.** Preferences save automatically; the receiver gets them
  without any export step. **Built.**

## Visual direction: "Night lens"

- **Decision (Emma):** the page is the view through the glasses. Near-black ground, the OLED's own
  white, the Silkscreen pixel font for anything the display would say, Instrument Sans for the
  interface, and one warm signal colour (amber) for urgent cues and "connected" lights. **Built.**
- **Rejected:** the sage-green first build ("messy / AI generated") and the repo's dealt "achromatic
  ledger" admin-dashboard style (read as bland, no personality). Rainbow tier colours were dropped for
  white tiers plus amber Urgent.
- **The lens shows the real panel frame.** The browser draws the exact 128×64 frame the glasses get,
  scaled up, with black rendered as see-through, which is how a 50:50 combiner looks. So the live view
  and the panel cannot disagree (a byte-for-byte test enforces it). A small black-backed "panel" inset
  shows the raw frame. **Built.**
- **Camera backdrop:** "Show my room" puts the camera feed behind the cue so judges see cues over a real
  scene. Click-to-start only, never recorded or sent. **Built.**

## The glasses panel

- **The direction is the position.** Cues sit at the edge the sound came from (left, right, front =
  top, behind = bottom), with a one-pixel line along that edge. Arrows beside a centred icon were tried
  and rejected: the wearer should feel where the sound is, not decode an arrow. **Built.**
- **Unknown direction stays centred** so the display never claims a side it does not know. Today's
  hardware always reports unknown, so centred is the common case until localization works. **Open:**
  Emma may prefer a fixed corner for unknown.
- **The icon never moves with tier or labels.** Early layouts put the icon in different places per
  tier, which looked inconsistent. Now the label row is always reserved and tier only changes the box
  around the icon: none (Ambient), thin (Notify), double (Attention), double plus inverted label
  (Urgent). Urgent always shows its label. **Built and tested.**
- **Cute, readable icons.** 32×32 pixel art with 2px strokes and friendly details: puppy face, door
  with knock marks, bell with sparkles, smiley with a speech bubble (your name), flame (smoke alarm),
  siren dome, alarm clock, speech bubbles, a check mark. The site's sound buttons use the same art.
  **Built;** readability through the real optics still untested.
- **Icon-first by default; labels optional** (Preferences → Display). Labels setting also reaches the
  glasses. **Built.**

## Urgency and attention

- **No rapid flashing.** More than three flashes a second is a seizure risk and harsh through a
  see-through combiner. **Decided.**
- **Slow urgent pulse.** Urgent blinks its box and label once a second for the first ~5 s, then holds
  steady; urgent-only; off with reduced motion; lens and panel blink together. **Proposed, not built.**
- **Modes:** Everyday passes everything not ignored; Work passes Attention and Urgent; Do not disturb
  passes Urgent only; Pause hides everything including Urgent and says so. **Built.**

## How a cue ends

- A cue resolves by **expiring**, **Dismiss**, a **thumbs-up**, or the wearer **looking toward it**.
  The user-driven ways show a 0.6 s ✓ at the cue's position; expiry shows nothing. Resolving
  acknowledges that sound, so it stays quiet while it keeps going (15 s after its last repeat). **Built.**
- **Look-to-resolve:** if the wearer turns toward a directed cue, it is resolved. There is no head
  sensor yet; `POST /look` is ready for one and the Look button simulates it. **Built (simulated input).**

## Dismiss gesture: visual, not audio

- **Decision (Emma):** dismiss must be visual. Not everyone can snap loudly, and a real alarm would
  drown out a snap exactly when dismissing matters. Emma confirmed the glasses have a camera. **Built.**
- **Thumbs-up held ⅓ s** was chosen over an open palm (happens by accident) and a visual finger snap
  (too small and fast for a camera). MediaPipe's free hand-gesture model runs in the browser on the lens
  camera. **Open:** the gesture itself is easy to change if the team prefers another.
- **Audio snap (history):** built first using the models' "Finger snapping" class, then disabled. Note
  for anyone reviving it: 1 s analysis hops make quick double snaps merge into one detection.
- Gestures only act while a cue is showing, to avoid accidental dismissals. **Built.**

## Direction and hardware limits

- Direction arrives as degrees plus confidence from a future spatial worker; shown only at confidence
  ≥ 0.6. **Built (contract ready).**
- **Two microphones cannot tell front from behind.** The engine supports four sides, but a two-mic
  worker should send no direction rather than guess. A third mic or head sensor would make front/behind
  real. **Decided.**

## Browser vs Receiver

- **Browser:** everything runs in the page with test sounds; for design and showing behaviour without
  Python, mic or glasses. **Receiver:** the page follows the real Python receiver that hears audio,
  applies preferences and drives the glasses. For the demo, use Receiver so the site, the glasses and
  the real audio follow one set of decisions. **Built.**
- The site never asks for the microphone; the Python recognizer listens. "Waiting for audio" means
  connected but nothing recognized yet; "Lens offline" means no glasses client. **Open:** rename "Lens
  offline" to "Glasses not connected" if it keeps reading as an error.

## Discussed, not committed

- **Name detection first,** short companion captions as a stretch; nearby speech alone never means
  "someone is talking to you". Revoicing and continuous ASL translation are out of scope this weekend.
- **A "mic is listening" heartbeat** so silence is distinguishable from a stalled worker (audio side).
- **Demo stage gesture via webcam** was considered before the glasses camera was confirmed; now the
  same gesture code serves both.

## Codex review — October 24

Retain the Night lens and edge-position approach. A Fortnite-style cue is a useful interaction reference;
the 128×64 optical patch is not established as a full-field-of-view circumference. Keep unknown direction
neutral and real directional output gated on measured localization. Queue/ack/urgent-extension timing
remains provisional until wearer testing. Leave the proposed urgent pulse unbuilt pending that validation.

A held thumbs-up now requires release before rearming, preventing one sustained gesture from resolving
several queued sounds. “Display client connected” establishes polling, not verified OLED output. “Recent
audio events” establishes recent detections, not microphone heartbeat. These distinctions are intentional.

## Camera assumption corrected — October 24 (supersedes camera/gesture claims above)

Emma clarified there is no camera on the glasses. The optional camera background is a demo POV,
using a laptop webcam or a phone exposed as a webcam. It does not establish wearable capture,
spatial tracking, head tracking or gesture control. Automatic hand recognition and the thumbs-up
button have been removed from the user flow. Gesture code remains unused experimental code.
Manual Dismiss and timed expiry work; Look is explicitly a simulated input. No new camera is needed.

A phone can act as a camera when the OS/browser exposes it as a webcam. Direct phone-browser access
would require a reachable secure site and an agreed event connection; localhost on the laptop is
not accessible from the phone. That remote-phone setup has not been implemented or tested here.

## Current display and demo decisions — October 24 (supersedes edge-placement history)

The real panel is only on the right side of the field of vision. Center the icon within it and use
compass arrows around that icon; unknown has no arrow. One alert at a time remains intentional.
Optional thumbs-up is restored for the demo POV camera only, with a deliberate hold/release and exact
event dismissal. User reports finicky live behavior; tuning is deferred. The glasses still have no
camera. Phone POV/mirroring is not implemented yet. See simulator-freeze.md and integration-revisit.md.
