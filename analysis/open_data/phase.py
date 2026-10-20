"""Phase-based coupling between recording sites: filtering, re-referencing, lag statistics and coupling measures.

DPC is about agreement in timing, which includes coupling at or near zero lag. The weighted phase lag index (wPLI) is
blind to zero-lag coupling, so it is always reported beside two lag-sensitive measures, the phase-locking value (PLV)
and the lag statistics. Volume conduction, which also produces zero-lag coupling, is limited instead by bipolar
re-referencing and by keeping only long-range pairs that share no electrode.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, filtfilt, hilbert, iirnotch, sosfiltfilt

from .constants import MS_PER_SECOND, NUMERICAL_FLOOR, RESULTANT_FLOOR
from .settings import Band
from .specs import FilterSpec, LineNoise, Resampling

Pairs = list[tuple[int, int]]


@dataclass(frozen=True)
class PairedSignals:
    """Analytic signals (sites x samples) and the pairs of sites to compare."""

    analytic: np.ndarray
    pairs: Pairs

    def unit_cross(self, partner: np.ndarray | None = None) -> np.ndarray:
        """Unit-magnitude cross products z_i conj(z_j) per pair; ``partner`` replaces the second member's signals."""
        i, j = np.array(self.pairs).T
        second = self.analytic if partner is None else partner
        cross = self.analytic[i] * np.conj(second[j])
        return cross / np.maximum(np.abs(cross), NUMERICAL_FLOOR)


@dataclass(frozen=True)
class ShiftSurrogates:
    """PLV edge test: (1 - alpha) quantile after circular shifts of at least ``min_shift`` samples."""

    alpha: float
    min_shift: int
    resampling: Resampling


def remove_line_noise(x: np.ndarray, fs: float, noise: LineNoise) -> np.ndarray:
    for f0 in noise.frequencies_hz:
        if f0 < fs / 2:
            b, a = iirnotch(f0, noise.quality, fs)
            x = filtfilt(b, a, x, axis=-1)
    return x


def bandpass(x: np.ndarray, band: Band, spec: FilterSpec) -> np.ndarray:
    sos = butter(spec.order, [band.low_hz, band.high_hz], btype="bandpass", fs=spec.sampling_hz, output="sos")
    return sosfiltfilt(sos, x, axis=-1)


def analytic(x: np.ndarray) -> np.ndarray:
    return hilbert(x, axis=-1)


def nearest_neighbour_pairs(xy: np.ndarray) -> Pairs:
    """Each electrode with its nearest neighbour, as unique unordered pairs, for bipolar derivations."""
    distances = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=-1)
    np.fill_diagonal(distances, np.inf)
    pairs = {tuple(sorted((i, int(np.argmin(distances[i]))))) for i in range(len(xy))}
    return sorted(pairs)


def bipolar(x: np.ndarray, xy: np.ndarray, pairs: Pairs) -> tuple[np.ndarray, np.ndarray]:
    signals = np.stack([x[a] - x[b] for a, b in pairs])
    midpoints = np.stack([(xy[a] + xy[b]) / 2 for a, b in pairs])
    return signals, midpoints


def long_range_pairs(midpoints: np.ndarray, members: Pairs, quantile: float) -> Pairs:
    """Pairs of derivations sharing no electrode and further apart than the given quantile of all distances."""
    n = len(midpoints)
    candidates = [(i, j) for i in range(n) for j in range(i + 1, n) if not set(members[i]) & set(members[j])]
    distances = np.array([np.linalg.norm(midpoints[i] - midpoints[j]) for i, j in candidates])
    cut = np.quantile(distances, quantile)
    return [pair for pair, d in zip(candidates, distances, strict=True) if d > cut]


def circular_mean(angles: np.ndarray, axis: int = -1) -> np.ndarray:
    return np.angle(np.mean(np.exp(1j * angles), axis=axis))


def circular_sd(angles: np.ndarray, axis: int = -1) -> np.ndarray:
    resultant = np.abs(np.mean(np.exp(1j * angles), axis=axis))
    return np.sqrt(-2.0 * np.log(np.clip(resultant, RESULTANT_FLOOR, 1.0)))


def phase_to_ms(angle: np.ndarray, centre_hz: float) -> np.ndarray:
    return MS_PER_SECOND * angle / (2 * np.pi * centre_hz)


def windowed_phase_differences(signals: PairedSignals, window: int) -> np.ndarray:
    """Circular mean phase difference of each pair in each non-overlapping window: shape (pairs, windows)."""
    z = signals.analytic
    n_windows = z.shape[-1] // window
    if n_windows == 0:
        raise ValueError("segment shorter than one window")
    trimmed = PairedSignals(z[:, : n_windows * window].reshape(z.shape[0], n_windows, window), signals.pairs)
    return np.angle(np.mean(trimmed.unit_cross(), axis=-1))


def lag_statistics(window_angles: np.ndarray, centre_hz: float) -> dict[str, np.ndarray]:
    """Mean lag and lag variability (circular SD across windows), both in ms, per pair."""
    return {
        "mean_lag_ms": np.abs(phase_to_ms(circular_mean(window_angles), centre_hz)),
        "lag_variability_ms": phase_to_ms(circular_sd(window_angles), centre_hz),
    }


def plv(signals: PairedSignals) -> np.ndarray:
    return np.abs(np.mean(signals.unit_cross(), axis=-1))


def wpli(signals: PairedSignals) -> np.ndarray:
    """Weighted phase lag index over samples (Vinck et al., 2011)."""
    i, j = np.array(signals.pairs).T
    imaginary = np.imag(signals.analytic[i] * np.conj(signals.analytic[j]))
    denominator = np.mean(np.abs(imaginary), axis=-1)
    return np.divide(np.abs(np.mean(imaginary, axis=-1)), denominator, out=np.zeros_like(denominator), where=denominator > 0)


def log_power(z: np.ndarray) -> np.ndarray:
    return np.log(np.mean(np.abs(z) ** 2, axis=-1))


def plv_surrogate_threshold(signals: PairedSignals, spec: ShiftSurrogates) -> float:
    """Upper (1 - alpha) quantile of PLV after circularly shifting one member of each pair, pooled over pairs."""
    z, rng = signals.analytic, spec.resampling.rng
    n = z.shape[-1]
    if n <= 2 * spec.min_shift:
        raise ValueError("window too short for the minimum surrogate shift")
    pooled = []
    for _ in range(spec.resampling.count):
        shifted = np.stack([np.roll(row, int(rng.integers(spec.min_shift, n - spec.min_shift))) for row in z])
        pooled.append(np.abs(np.mean(signals.unit_cross(shifted), axis=-1)))
    return float(np.quantile(np.concatenate(pooled), 1.0 - spec.alpha))
