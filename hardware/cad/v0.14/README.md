# DETECT CAD v0.14

This is the current four-piece print candidate for the clip-on glasses assembly.

## Printable files

- `stl/body.stl` — flat Pi tray, integral glasses-arm hook, and optical guides.
- `stl/cover.stl` — electronics cover and raised GPIO wire-bend clearance.
- `stl/mic_left.stl` — left microphone carrier.
- `stl/mic_right.stl` — right microphone carrier.

The body carries the Pi flat and uses an integral hanging hook rather than a
separate clamp jaw. Optional pressure screws enter from the top so no screw head
sits against the wearer. Both microphone carriers leave the acoustic opening
clear and route their six conductors out the rear/top.

## Before printing

Read `MEASURED_FIT.md`. Print with existing PLA at approximately 0.16–0.20 mm
layers, 3–4 walls, and 20–35% infill. Print or slice-inspect the fit-critical
body first, then dry-fit all electronics and optics before using adhesive.

## Editable files and checks

- `source/DETECT.scad` — main OpenSCAD model.
- `source/parameters.scad` — fit dimensions and clearances.
- `source/checks.scad` — geometric check geometry.
- `CHECKS.json` — automated geometric validation results.
- `OPTICAL_CHECK.json` — nominal optical-path validation results.
- `stl/SHA256SUMS` — verified file-integrity checksums for all four STLs.

The checks verify modeled geometry, not the unmeasured tolerances of the exact
physical parts. Re-export after changing parameters and repeat the physical fit.
