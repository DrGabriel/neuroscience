"""Prediction 2 (tests H2a, H2b): critical slowing down of the order parameter before loss of responsiveness.

Indicators follow Dakos et al. (2012): Gaussian detrending, rolling variance and lag-1 autocorrelation over a window
of half the series, Kendall's tau of each indicator against time, and significance against phase-randomised surrogates
of the same series, which keep its spectrum but have no trend in either indicator by construction.
"""

from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.ndimage import gaussian_filter1d
from scipy.stats import kendalltau

from .network import phase_randomise
from .settings import WARNING

MIN_ROLLING_WINDOW = 3


def gaussian_detrend(series: np.ndarray, bandwidth: float) -> np.ndarray:
    return series - gaussian_filter1d(series, sigma=bandwidth, mode="nearest")


def _lag1(windows: np.ndarray) -> np.ndarray:
    centred = windows - windows.mean(axis=1, keepdims=True)
    numerator = np.sum(centred[:, 1:] * centred[:, :-1], axis=1)
    denominator = np.sum(centred**2, axis=1)
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)


def rolling_indicators(residuals: np.ndarray, window: int) -> dict[str, np.ndarray]:
    windows = sliding_window_view(residuals, window)
    return {"variance": windows.var(axis=1), "autocorrelation": _lag1(windows)}


def trend(indicator: np.ndarray) -> float:
    tau, _ = kendalltau(np.arange(indicator.size), indicator)
    return float(tau)


def indicator_trends(series: np.ndarray) -> dict[str, float]:
    series = np.asarray(series, float)
    if series.size < WARNING.min_points:
        raise ValueError(f"{series.size} points before loss of responsiveness; at least {WARNING.min_points} are needed")
    window = max(int(round(WARNING.rolling_share * series.size)), MIN_ROLLING_WINDOW)
    bandwidth = WARNING.detrend_bandwidth_share * series.size
    indicators = rolling_indicators(gaussian_detrend(series, bandwidth), window)
    return {name: trend(values) for name, values in indicators.items()}


def critical_slowing_test(series: np.ndarray, rng: np.random.Generator, n_surrogates: int | None = None) -> dict:
    """Kendall's tau of variance and autocorrelation, each with a one-sided surrogate p-value."""
    n_surrogates = WARNING.surrogates if n_surrogates is None else n_surrogates
    observed = indicator_trends(series)
    null = {name: np.empty(n_surrogates) for name in observed}
    for i in range(n_surrogates):
        surrogate = phase_randomise(np.asarray(series, float), rng)[0]
        for name, tau in indicator_trends(surrogate).items():
            null[name][i] = tau
    return {
        name: {"tau": tau, "p_value": float((1 + np.sum(null[name] >= tau)) / (1 + n_surrogates))}
        for name, tau in observed.items()
    }
