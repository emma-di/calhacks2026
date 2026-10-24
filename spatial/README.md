# Spatial: where is the sound coming from?

Estimates the direction of a sound from synchronized microphones on the glasses frame.
Hardware capture is not connected yet; the sound map below simulates the microphones.

## Sound map simulator

Needs Python 3 and NumPy only. From the project root:

```sh
python3 -m spatial.server
```

Open **http://127.0.0.1:8766**. The wearer is at the center of a top-down map, to scale out to 6 m.
Click the map to play a sound there. Red dots are the true positions; amber lines are the directions
the microphones estimate. Dashed lines with a question mark mean front or back is still unknown.

To feed it from the audio program, also run `python3 -m audio.server` (port 8765). New events, mock or
recognized, appear on the map at a random simulated position, because the audio pipeline has no direction
yet. Events can also be sent straight to the map:

```sh
python3 -m audio.cli fake knock --endpoint http://127.0.0.1:8766/events
```

Controls:

- **Microphones**: two (arm tips, from `frame_geometry.json`) or three (adds the planned bridge mic at 0, 0).
- **Head**: turn 15° with the buttons or arrow keys. With two mics, turning while a sound is still playing
  decides front or back: a sound in front shifts the opposite way to the turn, a sound behind shifts the same way.
- **Room noise**: signal-to-noise ratio of the simulated mics (quiet 30 dB, normal 15 dB, loud 5 dB).

## How it works

| File | Purpose |
| --- | --- |
| `frame_geometry.json` | Mic positions in mm. Origin at the bridge of the nose, +x right, +y forward |
| `geometry.py` | Loads the geometry, angle helpers, head-frame rotation |
| `simulate.py` | Synthesizes each mic's signal from a source position (free-field delay and 1/r, plus noise) |
| `gcc_phat.py` | Time difference of arrival between two channels, with partial PHAT weighting |
| `localize.py` | Scores every bearing against all mic pairs (SRP-PHAT); reports the mirror pair for two mics |
| `front_back.py` | The head-turn rule for two mics |
| `scene.py`, `server.py`, `radar.html` | Simulator state, local HTTP server and the map page |

Bearings: 0° straight ahead, positive clockwise toward the right, so ±180° is behind. Simulation uses
48 kHz audio. Tests: `python3 -m unittest discover -s tests -v`.

## Limits of the simulation

- No head shadow, room echoes, mic mismatch or clock drift. Real recordings will be harder.
- Waveforms are synthetic stand-ins for each event type, not recordings.
- Tonal alarms (around 3 kHz) have wavelengths shorter than the mic spacing, so their estimates can alias;
  the confidence value drops for them.
- Positions are measured from the bridge; the two-mic array center sits 122 mm behind it, which adds up to
  about 2° of parallax for sounds 3 m away.
- Distance is not estimated.
