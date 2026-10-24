# Hardware stack and software handoff

**Updated 2026-10-23. Owner: Yameen (hardware); Emma (backend/display contract); John and Leo (audio/spatial).**

## TLDR for builders

Use the **original Raspberry Pi Zero W** for microphone capture and OLED output, with the
laptop running recognition, future speech recognition, priority decisions, and the browser mirror.
The display target is **128×64 monochrome**, so design a real pixel-sized cue alongside the larger
audience view. Two INMP441 microphones can share an I²S clock and data bus using opposite channel
selection; synchronized Linux capture still needs to be demonstrated on this board.
No physical hardware, driver, power supply, or transport has been tested by this repository yet.

## User-supplied inventory

These are the supplied parts, not a shopping list. Listing descriptions do not verify the delivered units.

| Part | Quantity / status | Build implication |
| --- | --- | --- |
| [Raspberry Pi Zero W](https://www.amazon.com/dp/B0FN4CN7TM) | 1; first generation, **not Zero 2 W** | Wi-Fi/Bluetooth endpoint; keep ML on the laptop. |
| [INMP441 I²S microphones](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf) | 2; already owned, six-pin modules | Capture left/right together; inspect module labels and components before wiring. |
| [ELEGOO SSD1306 OLED](https://www.amazon.com/dp/B0FSRQG23K) | Listing is a three-pack; use one | 0.96-inch, white, 128×64, four-pin I²C; listing advertises address `0x3C` and 3.3–5 V power. Verify actual module/address. |
| [SanDisk Ultra microSDHC](https://www.amazon.com/dp/B08GY9NYRM) | 32 GB, Class 10 / U1 / A1, adapter | OS and small device software; no model weights required on the Pi. |
| Vida IT USB power bank | Existing; exact model/label unverified | Confirm **5 V output**, available current, and reliable operation under capture + Wi-Fi load. |
| [USB-A → Micro-USB cable](https://www.amazon.com/dp/B0BLL6M29N) | User reports 5 ft, rated up to 2.4 A | Power cable rating alone does not prove stable voltage at the Pi. Listing could not be independently fetched. |
| [2×20, 0.1-inch GPIO header](https://www.amazon.com/dp/B0756KM7CY) | Already owned/pre-soldered | **Do not purchase another header.** |

The [official Zero W specification](https://www.raspberrypi.com/products/raspberry-pi-zero-w/)
lists a 1 GHz single-core CPU, 512 MB RAM, wireless LAN, Bluetooth, and Micro-USB power.
That makes a lightweight endpoint the practical MVP choice; this is an architecture decision,
not an inference-speed benchmark on the Pi. Select a Raspberry Pi OS image compatible with
this original board; do not assume a Zero 2 W tutorial or an ML package wheel supports it.

## System split

```text
Two INMP441s → Pi: one stereo capture stream → local Wi-Fi → laptop audio adapter
                                                        ├─ mono → classifier / future ASR
                                                        └─ original stereo → future localization
Laptop: events → preferences/priority → canonical active alert
                                         ├─ browser mirror + 128×64 preview
                                         └─ local Wi-Fi → Pi → SSD1306
```

The current receiver is loopback-only and has no Pi audio ingress or physical display adapter.
These are planned additions, not existing capabilities. Keep the recorded-audio path available
while hardware is brought up. Use a laptop microphone only for an explicitly selected fallback.

## Candidate pins — review before wiring

This table is a **candidate allocation**, not a finalized wiring instruction. Yameen must confirm
board orientation, physical pin numbers, module silkscreen, supply/pull-ups, and the capture driver.
BCM GPIO numbers and physical header numbers are different.

| Signal | Candidate BCM GPIO | Physical pin | Purpose |
| --- | --- | --- | --- |
| INMP441 SCK, both modules | GPIO18 / PCM clock | 12 | Pi-generated I²S bit clock |
| INMP441 WS, both modules | GPIO19 / PCM frame sync | 35 | Shared left/right frame clock |
| INMP441 SD, shared | GPIO20 / PCM data input | 38 | One stereo input stream |
| OLED SDA | GPIO2 / SDA1 | 3 | I²C data |
| OLED SCL | GPIO3 / SCL1 | 5 | I²C clock |
| 3.3 V peripheral supply | 3V3 | 1 or 17 | Candidate module supply, subject to module checks |
| Common ground | GND | e.g. 6 | Shared signal reference |

These alternate functions and the 3.3 V GPIO limitation are documented in the
[official Raspberry Pi header reference](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#gpio).
Pi GPIO is not 5 V tolerant. The OLED listing's power range does not establish the voltage of
its I²C pull-ups; inspect the module and prefer a verified 3.3 V-compatible configuration.
Power the Pi through its Micro-USB power input; keep the 5 V power source separate from signal levels.

## Stereo capture feasibility and acceptance

The [TDK INMP441 datasheet, I²S interface section and Figures 7–10](https://product.tdk.cn/system/files/dam/doc/product/sw_piezo/mic/mems-mic/data_sheet/inmp441.pdf)
describes 24-bit samples in 32-bit slots: 64 bit-clock cycles per stereo frame.
It supports a shared SD line because the inactive microphone output is high impedance.
Select left on one microphone (`L/R = 0`) and right on the other (`L/R = 1`), with common SCK/WS.
The datasheet also specifies supply decoupling and a shared-data pull-down; verify what the
breakout boards already provide. Do not leave channel selection floating.

This supports the proposed electrical topology. It does **not** prove the installed OS exposes
a working stereo ALSA input. Do not copy an output-only DAC overlay and call capture complete.

Yameen's capture checkpoint:

- [ ] Record the actual board revision, OS/kernel, capture overlay/driver and ALSA device name.
- [ ] Capture one stereo WAV and verify **both distinct channels** contain sound, with the expected channel order.
- [ ] Record native sample rate, container format, 24-bit alignment/sign extension, and scaling.
- [ ] Check clipping, noise, silent channels, dropped frames and capture overruns during Wi-Fi streaming.
- [ ] Demonstrate continuous shared-clock capture; measure left/right skew with a repeatable source.
- [ ] Measure mic spacing/orientation and label wearer-left/right; share the recording with John and Leo.

Prefer testing native **48 kHz stereo** if the driver supports it, preserving the original channels
for spatial work. Derive the classifier's **16 kHz mono** input on the laptop with proper resampling;
retain metadata and avoid phase cancellation when choosing a mono mix. If 48 kHz is unreliable,
record the supported rate and re-evaluate direction precision rather than pretending synchronization.
Two microphones alone do not establish full 360° direction or distance; confidence and ambiguity
handling must be evaluated before adding arrows to the wearer view.

## Proposed local transport

Start with the same local Wi-Fi network/hotspot. Keep device transport independent of UI components.
Use separate, bounded paths for audio and display commands so audio backlog cannot delay an urgent cue.
Choose and document the concrete protocol with the backend owner; no transport is implemented here.

- **Audio uplink:** stereo PCM chunks with stream/session ID, sample rate, channel order, encoding,
  sequence number and sample counter. A sample counter preserves timing within one stream; a wall clock
  alone does not synchronize microphones. Drop stale backlog and report gaps/overruns explicitly.
- **Display downlink:** a snapshot of the backend's resolved active alert, including event ID,
  state sequence, icon ID, short label, effective tier, and remaining lifetime.
  Include an explicit clear state; dismissal, expiry and pause must reach both displays.
- **Connection health:** heartbeat and reconnect with a fresh state snapshot. Do not replay a backlog
  of expired alerts. Pi acknowledgement should report the rendered state sequence, not imply recognition.
- **Device expiry:** use monotonic local timers with a backend-provided remaining duration and a heartbeat
  timeout. Clear stale cues on disconnect rather than leaving an obsolete emergency visible indefinitely.
- **LAN scope:** use an explicit device credential and network binding when adding remote access;
  do not simply expose the current unauthenticated diagnostic receiver on every interface.

These are proposed contract fields, not additions to the current event schema. Keep recognition events
separate from the display snapshot. The backend owns tier/expiry; the Pi should render the result.

## 128×64 OLED and browser mirror

The browser cannot be copied directly onto an SSD1306. Share alert state, icon IDs and cue layout
rules, then render with separate browser and device adapters. Include an actual **128×64, one-bit**
preview in the browser; enlarge it with crisp pixels for audience readability.

- Use one strong icon and a short label, with limited text and a tested bitmap font.
- Use size, icon, border and persistence to distinguish tiers; this white OLED cannot encode tier colors.
- Tier 0 stays invisible; avoid fast flashing. Show a direction cue only when a validated estimate exists.
- Verify display rotation and any optical mirror/inversion on the assembled glasses. Optical focus,
  eye relief and readability remain hardware tests; an OLED alone is not a finished heads-up display.
- Confirm actual I²C address and driver support, then display a fake generic bell or knock.
  A mock “Bicycle bell” label is fine for display testing, but does not prove bicycle classification.
- Verify replacement, dismissal, expiry, disconnect and reconnect against the browser's same event ID.

## First physical integration gates

1. **Fake alert → OLED:** one visible cue, then clear/replace it; photograph or record the result.
2. **Stereo capture → recording:** publish capture metadata and a short agreed test recording through
   the team's chosen sharing path; do not commit private ambient audio or large recordings by default.
3. **Pi audio → laptop recognizer → both displays:** measure capture-to-visible latency, including
   the classifier's two-second windows; model inference time alone is not end-to-end latency.
4. **Spatial prototype:** only after capture is proven, compare known left/right source positions
   and unknown/ambiguous cases. Keep direction optional while recognition/display integration proceeds.
5. **Wearable rehearsal:** verify optics, cable strain, supply stability, connection recovery and the
   audience mirror. Keep a clearly labelled replay fallback available for the demo.

Record checkpoint evidence in the [master TODO](../TODO.md). See the
[integration handoff](integration.md) and [UI/backend plan](ui-ux-backend-plan.md) for software boundaries.

See [display UX / optical questions](display-ux.md) before promising full-field peripheral placement, and the [offline pixel renderer](display-renderer.md) for software frames ready for driver integration.

## OLED photo and CAD follow-up — October 23

Emma supplied a close-up showing a white monochrome OLED breakout labeled `GND VCC SCL SDA`,
and a CAD screenshot of the glasses/optical assembly. The images are consistent with the supplied
four-pin I²C module; a photo alone does not establish controller identity, exact resolution or voltage
requirements. Those still come from the actual module specification and verification on the board.

The [controller manufacturer's SSD1306 page](https://www.solomon-systech.com/product/ssd1306)
confirms 128×64 display RAM, I²C support and contrast control. One one-bit frame is 1,024 bytes,
matching the offline renderer. Contrast adjustment does not make this white panel a color display.
The controller chip's supply specifications must not be confused with a breakout board's VCC pin.

At the supplied nominal 0.96-inch active diagonal and a 2:1 active aspect ratio, the lit area would
be approximately 22×11 mm; this is a geometric estimate, not a measurement of the PCB or optics.
A 24×24 pixel pictogram leaves useful room for a short urgent label. The photographed examples
support the simple-icon design direction, but magnified photographs do not prove near-eye focus,
contrast in the venue, eye box or angular coverage.

The CAD suggests optical elements are planned, but no readable focal lengths, spacing or angular
coverage are supplied. Keep browser edge placement marked as simulated. Yameen should provide
a through-the-optics view from the intended eye position and confirm whether the virtual image is
a small fixed patch or a wide overlay. See [display UX questions](display-ux.md).

## Combiner supplied — October 23

Yameen's screenshot identifies the final plate as an Azure Spy listing: BK-7 glass, 25.4 mm diameter,
2 mm thick, 50:50 transmission/reflection. These are supplied listing claims, not measured optical
performance. The plate combines light paths; its aperture does not specify magnification, focal
distance or angular field of view. Confirm the actual focusing lens and display/lens/plate/eye
geometry before claiming a full-field directional overlay.
