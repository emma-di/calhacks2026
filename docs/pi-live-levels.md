# Live Pi microphone levels

**Primary mode now:** run `.venv/bin/python -m audio.cli mic --pi pi@glasses-pi.local
--endpoint http://127.0.0.1:8766/events`. This serves the same meters on 8768 while feeding recognition
from the Pi; `inference_input=pi_stereo` distinguishes it from `levels_only` below. Do not start the
standalone bridge alongside this command. See [spatial handoff](pi-spatial-handoff.md).

The Mac bridge `audio/pi_levels.py` streams the Pi's two digital microphone slots over SSH and
publishes **numerical levels only** on loopback port 8768. It does not run recognition, save audio,
change the existing receiver, or estimate direction. The Pi runs only its stock `arecord` utility.
This avoids restarting receiver 8766 while live model settings are held in that process.

Start only after the wearer/team has explicitly approved microphone capture:

```sh
.venv/bin/python -m audio.pi_levels --pi pi@glasses-pi.local --port 8768
```

Default capture device: `hw:CARD=AwareINMP441,DEV=0`. The Pi must already expose that ALSA device;
see [capture setup](../hardware/pi-capture/README.md). SSH must already trust the Pi's key and allow
key-based login. The bridge does not accept new host keys or request passwords. Stop with Ctrl+C.

The website can poll `/pi-audio/levels`, proxied to `http://127.0.0.1:8768/levels`, every 200 ms.
The bridge has no microphone-start HTTP endpoint and provides no audio-download endpoint.
Only start one capture bridge for this ALSA device; a second capture client may find it busy.

## Schema

```json
{
  "schema_version": 1,
  "sample_rate": 48000,
  "channels": 2,
  "sequence": 42,
  "age_ms": 83,
  "connected": true,
  "levels": [
    {"channel": 0, "rms_dbfs": -42.1, "peak_dbfs": -20.7, "clip_fraction": 0},
    {"channel": 1, "rms_dbfs": -43.2, "peak_dbfs": -22.5, "clip_fraction": 0}
  ],
  "error": null
}
```

Values above are schema examples, not measurements. Each observation covers 100 ms of signed 32-bit
little-endian stereo PCM at 48 kHz. Levels are calculated relative to full-scale signed 32-bit values;
RMS and peak are floored at −120 dBFS. `clip_fraction` is the fraction at or above 99.9% full scale.
These are digital levels, not calibrated sound-pressure levels or distance measurements.

Before audio arrives, `age_ms` is null. When disconnected or stale for more than 1.2 seconds,
`connected` becomes false and `levels` becomes an empty array: **clear both meters**. Never hold the
last loud reading as if it were live. A zero-level channel while connected remains a valid −120 dBFS
measurement, not a missing value. `sequence` increments once per complete window and resets when the
bridge restarts; clients must not assume it is globally increasing.

Channel 0 and channel 1 denote digital stereo slots. Physical left/right mapping must be verified
by sounding near each microphone. This screen is not spatial localization.

## Failure handling and verification

SSH uses batch mode, verified host keys, bounded connection/keepalive settings and an 8-second audio
stall watchdog. The old child is terminated/reaped before retrying, with a 2-second backoff. SSH and
ALSA stderr is discarded rather than left in an unread pipe or exposed to HTTP clients. Numeric
telemetry is served only on `127.0.0.1`, with caching disabled.

Tests use synthetic local processes and sample arrays, never hardware or microphones:

```sh
.venv/bin/python -m unittest tests.test_pi_levels -v
```

They cover independent channel levels, silence/clipping, fragmented stereo byte reads, stale clearing,
SSH argument validation, child cleanup/reconnect, high stderr output and loopback numeric-only HTTP.
