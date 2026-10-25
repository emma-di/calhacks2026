# Mac recognizer controls

Run these from the repository root. These commands start actual microphone recognition only when
explicitly requested; they do not start the receiver or website, change the saved profile, deploy
inference to the Pi, or automatically fall back to the Mac microphone.

```sh
# Use the current demo receiver on 8766; keep its existing process/session API key.
.venv/bin/python scripts/recognizer.py pi
.venv/bin/python scripts/recognizer.py status
.venv/bin/python scripts/recognizer.py stop

# Explicit laptop fallback; first find its CURRENT device index.
.venv/bin/python scripts/recognizer.py devices
.venv/bin/python scripts/recognizer.py mac --device 1

# Last 40 console lines (may contain private recognized text; never commit/share casually).
.venv/bin/python scripts/recognizer.py logs
```

Pi and Mac commands run in the background and keep running after the terminal closes. Repeating
the same start command does not create another worker. Choosing a different source stops the
managed previous worker before starting its replacement. Status reports process ownership, not
proof that the input is actually capturing: check site **Log → Diagnostics** for fresh windows and
Pi channel levels. Pi disconnection/retry is handled by the existing capture adapter.

An older manually started recognizer is deliberately not killed or adopted. The command reports
its PID and refuses duplicate capture. Stop that worker in its original terminal, then use this
controller. It also refuses to signal a stale PID or unexpected process group. If a worker fails to
stop within ten seconds, the replacement is not started. No machine-wide login/startup service is
installed; start Pi once at the beginning of a demo session.

Optional overrides:

```sh
.venv/bin/python scripts/recognizer.py pi --pi pi@192.168.1.20
.venv/bin/python scripts/recognizer.py pi --endpoint http://127.0.0.1:8765/events
.venv/bin/python scripts/recognizer.py pi --dry-run
```

The default is this demo Mac's receiver **8766**, whereas a fresh `audio.server` defaults to8765.
The receiver must be reachable before a source switch is performed. Models may load slowly; a
successful launch is not a recognition accuracy check. Runtime metadata and logs stay in ignored
`.cache/`; raw microphone audio is not recorded by this controller.

## OLED reflection session

Keep the receiver and one Pi recognizer running. Deploy the current **display-only** code:

```sh
scripts/glasses_up.sh selftest
# If text is reversed through the combiner:
FLIP=--flip-x scripts/glasses_up.sh selftest
# If upside down too, include --flip-y. Use the confirmed transform for live:
FLIP=--flip-x scripts/glasses_up.sh live
```

Read text through the actual mounted optics before selecting the transform; a reflection is not
proof that the physical left/right input channels should be swapped. The browser remains in normal
wearer coordinates; only the physical display scan orientation changes. Confirm a real source on
left and right gives the corresponding arrow **as seen by the wearer**, then test urgent text and
question text. If the default orientation is already correct, omit FLIP. Ctrl+C the previous OLED
client before starting another; do not run the bear demo and this client together.
