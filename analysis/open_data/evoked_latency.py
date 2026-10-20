"""Prediction 8 (test H5, partial): trial-to-trial latency variability of responses between areas.

Single-trial latency is the shift that best aligns each trial with the mean evoked response of its connection; its
spread across trials is measured robustly (scaled median absolute deviation) and on equal trial counts in both states,
because the spread of a small sample depends on its size.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import MS_PER_SECOND, NUMERICAL_FLOOR

MAD_TO_SD = 1.4826
PARABOLA_HALF = 0.5


@dataclass(frozen=True)
class LatencyWindow:
    """Samples [start, end) in which the response is sought, the largest shift tried and the sampling rate."""

    sampling_hz: float
    start: int
    end: int
    max_shift: int


@dataclass(frozen=True)
class ResponseTest:
    """A connection responds if its mean response in [start, end) deviates by ``z_limit`` baseline SDs."""

    start: int
    end: int
    z_limit: float


def robust_sd(values: np.ndarray) -> float:
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return float(MAD_TO_SD * np.median(np.abs(values - np.median(values))))


def _parabolic_offset(left: float, centre: float, right: float) -> float:
    curvature = left - 2 * centre + right
    return 0.0 if curvature >= 0 else PARABOLA_HALF * (left - right) / curvature


def _alignment_scores(trial: np.ndarray, inner: np.ndarray, max_shift: int) -> np.ndarray:
    n = trial.size
    scores = np.empty(2 * max_shift + 1)
    for k, s in enumerate(range(-max_shift, max_shift + 1)):
        segment = trial[max_shift + s : n - max_shift + s]
        segment = segment - segment.mean()
        scores[k] = np.dot(segment, inner) / (np.linalg.norm(segment) * np.linalg.norm(inner) + NUMERICAL_FLOOR)
    return scores


def single_trial_shifts(trials: np.ndarray, template: np.ndarray, max_shift: int) -> np.ndarray:
    """Shift (samples, sub-sample by parabolic interpolation) best aligning each trial with the template; positive is later."""
    inner = template[max_shift : template.size - max_shift]
    inner = inner - inner.mean()
    out = np.empty(trials.shape[0])
    for t, trial in enumerate(trials):
        scores = _alignment_scores(trial, inner, max_shift)
        best = int(np.argmax(scores))
        offset = _parabolic_offset(*scores[best - 1 : best + 2]) if 0 < best < scores.size - 1 else 0.0
        out[t] = best - max_shift + offset
    return out


def peak_latency(template: np.ndarray, start: int, end: int) -> int:
    """Sample of the largest negative deflection (the N1 of a cortico-cortical evoked potential) in [start, end)."""
    return start + int(np.argmin(template[start:end]))


def is_response(template: np.ndarray, baseline: np.ndarray, test: ResponseTest) -> bool:
    scale = baseline.std()
    if scale == 0:
        return False
    return bool(np.abs((template[test.start : test.end] - baseline.mean()) / scale).max() >= test.z_limit)


def connection_latency(trials: np.ndarray, window: LatencyWindow) -> dict[str, float]:
    """Mean latency (ms) of the N1 and robust SD (ms) of single-trial latencies for one connection."""
    template = trials.mean(axis=0)
    peak = peak_latency(template, window.start, window.end)
    span = slice(window.start - window.max_shift, window.end + window.max_shift)
    shifts = single_trial_shifts(trials[:, span], template[span], window.max_shift)
    to_ms = MS_PER_SECOND / window.sampling_hz
    return {"mean_latency_ms": to_ms * peak, "latency_sd_ms": to_ms * robust_sd(shifts)}


def equalise_trials(trials: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    if trials.shape[0] < count:
        raise ValueError("fewer trials than the common count")
    return trials[np.sort(rng.choice(trials.shape[0], size=count, replace=False))]


def first_spike_latencies(spike_times: np.ndarray, stimulus_times: np.ndarray, window_s: tuple[float, float]) -> np.ndarray:
    """Latency (s) of the first spike in the window after each stimulus; NaN when there is none."""
    spike_times = np.sort(np.asarray(spike_times, float))
    out = np.full(len(stimulus_times), np.nan)
    for k, onset in enumerate(stimulus_times):
        i = np.searchsorted(spike_times, onset + window_s[0])
        if i < spike_times.size and spike_times[i] < onset + window_s[1]:
            out[k] = spike_times[i] - onset
    return out


def relative_change(awake: dict[str, float], anaesthetised: dict[str, float]) -> float:
    """log(SD ratio) minus log(mean latency ratio): positive when variability rises more than mean latency."""
    if min(awake["latency_sd_ms"], anaesthetised["latency_sd_ms"]) <= 0:
        raise ValueError("a latency spread of zero cannot be compared on a log scale")
    return float(
        np.log(anaesthetised["latency_sd_ms"] / awake["latency_sd_ms"])
        - np.log(anaesthetised["mean_latency_ms"] / awake["mean_latency_ms"])
    )
