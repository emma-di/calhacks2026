# DETECT 0.14 — measured fit and verification limits

## Reported dimensions

Arm: 12.70 mm high × 7.112 mm thick (0.50 × 0.28 in).
Mic: Ø17.78 mm (0.70 in), with 12.70 mm total axial depth including soldered
pins (0.50 in, interpreted as depth normal to the PCB).
USB plug housing: 10.16 × 5.08 mm (0.40 × 0.20 in). Its 20 mm modeled axial
length is an assumption. Both mic mounting positions use the same arm size;
physical taper at the ears is not measured.

## Integral hanging hook — no extra printed jaw

The body has an open-side C-section. The lower shelf surrounds the underside,
the outer wall locates the arm, and the upper shelf bears hanging weight.
Clear vertical opening: 13.40 mm. Internal shelf engagement depth: 9.106 mm.
The mouth opens toward the head. Align from below/outboard and slide sideways;
no PLA flex or forced snap-fit is required. A local arm insertion gauge checks
this mouth, not an exact swept assembly against a scanned frame or face.

Two optional top-entry M3 screws at X=40 and 72 mm engage captive nuts in local
5.2 mm-high upper bosses. The nuts slide in from the open inboard side before
the hook is installed. The modeled screws are M3 × 8 mm; verify actual lengths
and engagement. Add soft removable padding at contact and tighten only enough
to stop movement. Screws press down against the arm; never drill or tap the
glasses. There are no screw heads, through-holes or nut pockets on the lower
shelf, leaving the wearer-facing underside smooth.
Without screw retention the hook can slide sideways or rock, so hanging alone
is a positioning feature rather than a validated secure wearable fastening.

## Top clearance and rear microphone wiring

The hood roof underside is Z=48.5 mm. PCB top is Z=22.8 mm. Modeled upright
connector tops are Z=37.8 mm: there is 10.70 mm headroom above them, compared
with 2.70 mm in v0.11. A separate interference probe uses plugs 3 mm taller.
This height remains assumed until actual plugged-in hardware is measured.

Both six-lead microphone cables use the rear window toward the ear: nominal
16 × 12 mm, plus local relief around the modeled cables. Two Ø6.2 mm bundle
lanes are kept separate through the hood. The OLED uses its own nominal
10 × 10 mm front opening. Mic routes include sampled 5 mm radius bends into
the rearward run; the remaining routes are assembly envelopes, not a certified
minimum bend-radius analysis for the user's actual wire or every individual
lead. Roof tie holes and mic carrier tie holes allow optional strain relief.

The left cable returns forward above/outside the right housing, crosses in
front of the frame, then follows the outside of the left arm. It never bridges
ear-to-ear through the head. A coarse central head-space box is checked for
intersections; it does not establish actual forehead/ear comfort or fit.

Mic carriers retain Ø17.78 mm PCBs with 0.4 mm peripheral fit clearance, the
reported 12.7 mm stack depth, and a 2 mm gap to the saddle. Rear/top remain
open for wiring. Remove the M2 guard screw/washer to lower a board into its
guides. Acoustic faces stay open. Solder joints must clear the outer 1.5 mm
handling band; actual pad positions and pin orientations need physical checking.

## OLED pocket reserve

The assumed OLED PCB remains 27.3 × 27.3 × 1.8 mm. Its holder is checked with
a 28.3 × 28.3 × 2.8 mm solid gauge, giving exactly 1.0 mm extra in width,
height and board-thickness allowance. Width reserve is split around the board;
height and thickness reserve grow away from the screen datum so the active
display stays on the same optical axis. This reserve helps with PLA tolerance,
but the physical OLED and its rear components still require a dry fit.

## Optics — display distance is not mirror distance alone

Upright OLED → flat corner mirror → focusing lens → combiner → eye.
OLED-to-mirror centre-ray leg is now 18 mm (previously 16); mirror-to-lens leg
is 18 mm (previously 20). The nominal folded distance remains 36 mm, with
±3 mm OLED travel giving 33–39 mm calibration. This is an initial mechanical
setting for the nominal f36 lens, not a measured principal-plane distance.
Focus the assembly on the bench. The combiner redirects a virtual image and
is not a projection screen.

The geometric optical check samples 135 rays from a central 12 × 6 mm label
zone toward a central 4 mm lens region, at nominal and both focus extremes.
It tests finite mirror aperture, not full optical image quality or an eye box.
Full-screen edge rays can clip; use short centered labels/arrows for the demo.
Do not treat this as verification of all 128 × 64 pixels being visible.
The solid checks test optics/housing collisions and the central light path.

OLED PCB remains assumed 27.3 × 27.3 × 1.8 mm with unmeasured connector stack.
Mirror remains nominal 25 × 25 × 1.5 mm; coating side and thickness are not
confirmed. Lens remains nominal Ø25 / f36 mm, 6.5 mm overall thickness; its
actual profile, rim thickness and principal planes are unconfirmed. Combiner
is nominal Ø25.4 × 2 mm. Keep the optics adjustable until focus is established.

## Scope of the checks

Four print meshes are audited for watertightness, single connected shell,
degenerate triangles and consistent orientation. Solid probes cover frame,
Pi, connector envelopes (including +3 mm), optics at focus extremes, both mic
carriers, pin-depth envelopes, mic insertion, local hook loading, USB plug,
wire routes, lid mating, central light path and actual front/rear slot gauges.
The body/lid probe uses a 0.02 mm lift to exclude intended seating surfaces.
These verify nominal models, not print tolerances, strength, face comfort,
thermal performance, physical focus, microphone compatibility or wiring pinout.

The modeled frame is simplified. Eye position, hinge geometry, prescription
lens curvature, actual PCB dimensions and exact connector heights remain
physical-fit dependencies. Install the SD before the optics; moving the OLED
may be necessary for straight card extraction. Retain reversible shims during
bench focus and keep glue off optical faces.

Optics principle reference:
https://www.edmundoptics.com/knowledge-center/frequently-asked-questions/microscopy/magnifiers/how-do-i-calculate-the-power-of-a-magnifier/
