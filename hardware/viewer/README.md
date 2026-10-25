# DETECT interactive viewer

This static site presents the v0.14 CAD assembly, individual printable parts,
component and wire clearances, optical path, glasses hook, and the two-I²S-mic
plus SSD1306 OLED GPIO plan.

Run it from the repository root:

```sh
python3 -m http.server 4174 --bind 127.0.0.1 --directory hardware/viewer
```

Then open:

- CAD: <http://127.0.0.1:4174/>
- Wiring: <http://127.0.0.1:4174/wiring.html>

On the wiring page, select **07 — Underside soldering** for the mirrored bottom
view of the Pi header pads.
