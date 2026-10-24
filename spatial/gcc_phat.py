"""GCC-PHAT time-difference-of-arrival estimation (NumPy only)."""
import numpy as np


def gcc_phat(sig, ref, fs, max_tau=None, interp=16, beta=0.6):
    """Cross-correlate two channels with (partial) PHAT weighting.

    Returns (tau, lags, cc): tau is how many seconds `sig` arrives after `ref`
    (positive when `sig` hears the sound later), lags are the candidate delays in seconds
    and cc the normalized correlation at each lag (a clean single delay peaks near 1).

    beta=1 is classic PHAT, which whitens every frequency equally. Tonal sounds such as
    alarms then get swamped by noise-only bins; beta around 0.6 keeps some weight on the
    frequencies that carry energy. `interp` upsamples for sub-sample resolution.
    """
    sig = np.asarray(sig, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)
    n = sig.shape[0] + ref.shape[0]
    cross = np.fft.rfft(sig, n) * np.conj(np.fft.rfft(ref, n))
    weighted = cross / (np.abs(cross) ** beta + 1e-12)
    cc = np.fft.irfft(weighted, n * interp) * (n * interp) / (2 * np.sum(np.abs(weighted)) + 1e-12)
    max_shift = n * interp // 2
    if max_tau is not None:
        max_shift = min(int(np.ceil(interp * fs * max_tau)), max_shift)
    cc = np.concatenate((cc[-max_shift:], cc[:max_shift + 1]))
    lags = np.arange(-max_shift, max_shift + 1) / float(interp * fs)
    tau = lags[int(np.argmax(cc))]
    return tau, lags, cc
