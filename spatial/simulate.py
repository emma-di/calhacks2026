"""Synthesize what each microphone would record from a sound at a known position.

The model is free-field: each mic hears the source delayed by distance / c and
attenuated by 1 / distance, plus independent sensor noise. It ignores head shadow,
room echoes and mic mismatch, so real recordings will be harder than this.
"""
import numpy as np

from spatial.geometry import SPEED_OF_SOUND

SAMPLE_RATE = 48000

# How long each kind of sound keeps going after it starts, in seconds.
# Head-turn front/back checks only work while a sound is still going.
SOUNDING_SECONDS = dict(knock=0.6, bell=1.5, dog_bark=4, siren=15, smoke_alarm=20, alarm_clock=12, bicycle_bell=1.5)


def _decay(t, start, tau):
    return np.where(t >= start, np.exp(-(t - start) / tau), 0.0)


def source_signal(kind, fs=SAMPLE_RATE, duration=0.25, rng=None):
    """A short, plausible waveform for each event type (not a recording)."""
    rng = np.random.default_rng() if rng is None else rng
    t = np.arange(int(fs * duration)) / fs
    noise = rng.standard_normal(t.size)
    if kind == 'knock':
        sig = sum(noise * _decay(t, start, 0.006) for start in (0.02, 0.11, 0.20))
    elif kind in ('bell', 'bicycle_bell'):
        f0 = 2200 if kind == 'bicycle_bell' else 880
        sig = sum(a * np.sin(2 * np.pi * f0 * r * t) for a, r in ((1, 1), (0.6, 2.76), (0.4, 5.4)))
        sig = sig * _decay(t, 0.01, 0.4) + 0.5 * noise * _decay(t, 0.01, 0.003)
    elif kind == 'smoke_alarm':
        # About 3.1 kHz, the usual piezo alarm pitch. Its 11 cm wavelength is shorter than the
        # mic spacing, so direction estimates can alias; the simulator keeps that realistic.
        sig = np.sign(np.sin(2 * np.pi * 3100 * t)) * (t % 0.5 < 0.25)
    elif kind == 'alarm_clock':
        sig = np.sin(2 * np.pi * 2600 * t) * ((t * 8) % 1 < 0.5) + 0.2 * noise
    elif kind == 'siren':
        freq = 1100 + 400 * np.sin(2 * np.pi * 2 * t)
        phase = 2 * np.pi * np.cumsum(freq) / fs
        sig = np.sin(phase) + 0.4 * np.sin(2 * phase) + 0.2 * np.sin(3 * phase)
    elif kind == 'dog_bark':
        spectrum = np.fft.rfft(noise)
        freqs = np.fft.rfftfreq(t.size, 1 / fs)
        spectrum *= np.exp(-((freqs - 900) / 600) ** 2)
        sig = np.fft.irfft(spectrum, t.size) * (_decay(t, 0.02, 0.05) + _decay(t, 0.14, 0.05))
    else:
        sig = noise
    sig = np.asarray(sig, dtype=np.float64)
    return sig / (np.max(np.abs(sig)) + 1e-12)


def render(source_xy, mic_xy, signal, fs=SAMPLE_RATE, snr_db=20.0, rng=None):
    """Return an (n_mics, n_samples) array of what each mic records.

    `source_xy` and `mic_xy` are in meters in the same (head) frame.
    """
    rng = np.random.default_rng() if rng is None else rng
    source_xy = np.asarray(source_xy, dtype=np.float64)
    distances = np.linalg.norm(mic_xy - source_xy, axis=1)
    delays = distances / SPEED_OF_SOUND
    delays -= delays.min()  # keep the common travel time out of the buffer
    pad = int(np.ceil(delays.max() * fs)) + 64
    n = signal.size + pad
    spectrum = np.fft.rfft(signal, n)
    freqs = np.fft.rfftfreq(n, 1 / fs)
    channels = []
    for delay, distance in zip(delays, distances):
        shifted = np.fft.irfft(spectrum * np.exp(-2j * np.pi * freqs * delay), n)
        channels.append(shifted / max(distance, 0.3))
    channels = np.array(channels)
    power = np.mean(channels ** 2)
    noise_std = np.sqrt(power / (10 ** (snr_db / 10)))
    return channels + noise_std * rng.standard_normal(channels.shape)
