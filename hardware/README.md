# DETECT hardware package

This directory contains the current wearable CAD deliverable and its interactive
review environment. **v0.14 is the print candidate.** Older experimental
revisions are intentionally excluded so the team does not print the wrong files.

## Download from GitHub Actions

Every push or pull request that changes `hardware/` creates two downloadable
workflow artifacts:

- `DETECT-print-files-v0.14` — the four STL files, print ZIP, and fit notes.
- `DETECT-CAD-viewer-v0.14` — editable OpenSCAD sources, validation reports,
  downloads, and the complete browser viewer.

Open the workflow run named **Hardware CAD artifacts** in GitHub's **Actions**
tab, then download the artifact you need from the run summary.

## Four parts to print

1. [`body.stl`](cad/v0.14/stl/body.stl)
2. [`cover.stl`](cad/v0.14/stl/cover.stl)
3. [`mic_left.stl`](cad/v0.14/stl/mic_left.stl)
4. [`mic_right.stl`](cad/v0.14/stl/mic_right.stl)

The same four files are bundled in
[`DETECT_4_PRINT_PARTS_v0.14.zip`](cad/v0.14/DETECT_4_PRINT_PARTS_v0.14.zip).
Read [`MEASURED_FIT.md`](cad/v0.14/MEASURED_FIT.md) before printing or gluing
optics. Physical dry fitting is still required.

## View the assembly and wiring

The viewer is buildless and works without Node or package installation:

```sh
python3 -m http.server 4174 --bind 127.0.0.1 --directory hardware/viewer
```

Open <http://127.0.0.1:4174/> for the CAD assembly or
<http://127.0.0.1:4174/wiring.html> for the GPIO guide. The wiring page includes
the complete system, isolated left/right microphones, OLED wiring, clearance,
and mirrored underside-soldering views.

The downloaded viewer artifact can also be unzipped and `index.html` opened
directly in a modern browser because the meshes are bundled locally.

## Current measured assumptions

- Raspberry Pi Zero W board envelope: 65 × 30 mm.
- Glasses arm at clamp: 12.7 mm high × 7.1 mm thick.
- Microphone carrier allowance: 17.8 mm diameter × 12.7 mm total depth.
- OLED pocket: 28.3 × 28.3 × 2.8 mm.
- Lens and round combiner: nominal 25 mm diameter.
- Pocket battery: intentionally excluded from the glasses CAD.

These values document the current CAD inputs; they do not replace a dry fit of
the exact boards, solder joints, connectors, lens, combiner, and frame.
