# DETECT CAD 0.14 — four printed parts

1. body.stl — flat Pi tray, integrated hanging C-hook and optical guides.
2. cover.stl — stepped optical lid and raised GPIO wiring hood.
3. mic_left.stl — one-piece microphone carrier.
4. mic_right.stl — one-piece microphone carrier.

No separate clamp jaw is used. Keep the existing stepped electronics-to-display
layout. Read MEASURED_FIT.md before printing; actual OLED, mirror thickness,
solder-pad positions, frame curvature and connector stack are not all measured.
The OLED holder now reserves 28.3 × 28.3 × 2.8 mm for the assumed
27.3 × 27.3 × 1.8 mm board: exactly 1.0 mm extra in every dimension.

The hook slides onto the arm from the open inboard side. Approach from below
and outboard, align the opening, then slide sideways over the arm. It does not
snap straight upward through its solid upper shelf. Optional M3 pressure screws
enter from the top and tighten downward against soft tips/liner. The underside
has no screw heads or nut pockets against the wearer. Captive nuts slide into
the top bosses from the hook's open side; the screws do not enter the frame.
An unsecured hook can slide out sideways, so fit
and secure the prototype before wearing it in motion.

Install the microSD and verify boot before loading optics. The card slot is
exposed, but the OLED can obstruct straight forward card extraction when fully
assembled; service the card with the OLED moved/removed. Pi mounting and lid
screws remain accessible from above with the lid removed.

Use existing PLA, 0.16–0.20 mm layers, 3–4 walls and 20–35% infill. STLs are in
assembly coordinates: orient them in the slicer and inspect supports under the
raised Pi tray, hook shelves and optical lips. Remove support material from
mating surfaces before fit checks. Trial-fit one mic carrier and the actual
frame/components before committing to permanent optical glue.

Reproduce: python3 cad/v14/build.py --export-only; then
python3 cad/v14/check.py and python3 cad/v14/optical_check.py.
After checks pass, python3 cad/v14/build.py updates the local viewer.
Build/check scripts use the included cad/v09 validation helpers.
See CHECKS.json and OPTICAL_CHECK.json for the measured scope of verification.
