"""Prediction 1 (test H1): threshold behaviour of the giant component against concentration.

Thresholding a network whose coupling declines smoothly already produces a sharp fall of the giant component, so
sharpness alone is not evidence. The test compares the observed steepness with the steepness the same pipeline
produces from surrogate data whose coupling declines linearly with concentration (null A) or follows the observed
mean coupling exactly (null B).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import curve_fit

from . import network
from .settings import SHAPE
from .specs import EdgeTest

TEN_TO_NINETY = 2 * np.log(9.0)
EXPONENT_CLIP = 50.0
START_QUANTILES = (0.25, 0.5, 0.75)
START_WIDTHS = 5
SIGMOID_PARAMETERS = 4
LINE_PARAMETERS = 2
MIN_WINDOWS = 6
MIN_SPAN = 1e-9
MAX_FUNCTION_EVALUATIONS = 20000
LINE_DEGREE = 1


@dataclass(frozen=True)
class Logistic:
    """Decreasing logistic: ``high`` at low concentration, ``low`` at high concentration."""

    low: float
    high: float
    c50: float
    steepness: float

    def __call__(self, c: np.ndarray) -> np.ndarray:
        exponent = np.clip(self.steepness * (c - self.c50), -EXPONENT_CLIP, EXPONENT_CLIP)
        return self.low + (self.high - self.low) / (1.0 + np.exp(exponent))


def _logistic_curve(c: np.ndarray, *parameters: float) -> np.ndarray:
    return Logistic(*parameters)(c)


def width_to_steepness(width: float) -> float:
    return TEN_TO_NINETY / width


def steepness_to_width(k: float) -> float:
    return TEN_TO_NINETY / k


def bic(rss: float, n: int, n_params: int) -> float:
    return n * np.log(max(rss, np.finfo(float).tiny) / n) + n_params * np.log(n)


@dataclass(frozen=True)
class ShapeFit:
    c50: float
    steepness: float
    width: float
    low: float
    high: float
    delta_bic: float

    @property
    def sigmoid_preferred(self) -> bool:
        return self.delta_bic <= -SHAPE.bic_margin


def _sigmoid_starts(c: np.ndarray, s: np.ndarray) -> list[tuple[float, float, float, float]]:
    widths = np.geomspace(SHAPE.min_width_ug_per_ml * 2, np.ptp(c) if np.ptp(c) > 0 else 1.0, START_WIDTHS)
    centres = np.quantile(c, START_QUANTILES)
    return [(s.min(), s.max(), c50, width_to_steepness(w)) for c50 in centres for w in widths]


def _bounds(c: np.ndarray, s: np.ndarray) -> tuple[list[float], list[float]]:
    k_low, k_high = width_to_steepness(SHAPE.max_width_ug_per_ml), width_to_steepness(SHAPE.min_width_ug_per_ml)
    span = max(np.ptp(s), MIN_SPAN)
    return [s.min() - span, s.min() - span, c.min(), k_low], [s.max() + span, s.max() + span, c.max(), k_high]


def _best_sigmoid(c: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, float]:
    bounds = _bounds(c, s)
    best, best_rss = None, np.inf
    for start in _sigmoid_starts(c, s):
        start = np.clip(start, bounds[0], bounds[1])
        try:
            params, _ = curve_fit(_logistic_curve, c, s, p0=start, bounds=bounds, maxfev=MAX_FUNCTION_EVALUATIONS)
        except RuntimeError:
            continue
        rss = float(np.sum((s - _logistic_curve(c, *params)) ** 2))
        if rss < best_rss:
            best, best_rss = params, rss
    if best is None:
        raise RuntimeError("no sigmoid fit converged")
    return best, best_rss


def fit_shape(c: np.ndarray, s: np.ndarray) -> ShapeFit:
    """Fit a decreasing sigmoid and a straight line; ``delta_bic`` is sigmoid minus line (negative favours the sigmoid)."""
    c, s = np.asarray(c, float), np.asarray(s, float)
    if c.size < MIN_WINDOWS:
        raise ValueError(f"at least {MIN_WINDOWS} windows are needed to compare a four-parameter sigmoid with a line")
    best, best_rss = _best_sigmoid(c, s)
    line = np.polyfit(c, s, LINE_DEGREE)
    line_rss = float(np.sum((s - np.polyval(line, c)) ** 2))
    low, high, c50, k = (float(v) for v in best)
    delta = bic(best_rss, c.size, SIGMOID_PARAMETERS) - bic(line_rss, c.size, LINE_PARAMETERS)
    return ShapeFit(c50, k, steepness_to_width(k), low, high, delta)


def linear_decline(c: np.ndarray, awake_level: float, deep_level: float) -> np.ndarray:
    """Null A: mean coupling falls on a straight line between its awake and deep levels."""
    c = np.asarray(c, float)
    span = c.max() - c.min()
    fraction = (c - c.min()) / span if span > 0 else np.zeros_like(c)
    return awake_level + (deep_level - awake_level) * fraction


def mixing_fractions(target_coupling: np.ndarray, awake_coupling: float) -> np.ndarray:
    if awake_coupling <= 0:
        raise ValueError("awake mean coupling must be positive to scale it")
    return np.clip(np.asarray(target_coupling, float) / awake_coupling, 0.0, 1.0)


def declining_surrogate(reference: np.ndarray, fraction: float, rng: np.random.Generator) -> np.ndarray:
    """Surrogate window whose correlations are ``fraction`` times those of the awake reference window.

    A common-phase surrogate keeps the reference correlations; an independent surrogate removes them; mixing their
    standardised rows with weights sqrt(f) and sqrt(1 - f) scales every correlation by f.
    """
    shared = network.zscore_rows(network.phase_randomise(reference, rng, common=True))
    independent = network.zscore_rows(network.phase_randomise(reference, rng, common=False))
    return np.sqrt(fraction) * shared + np.sqrt(1.0 - fraction) * independent


def null_giant_components(awake_windows: list[np.ndarray], fractions: np.ndarray, test: EdgeTest) -> np.ndarray:
    values = np.empty(len(fractions))
    for i, fraction in enumerate(fractions):
        reference = awake_windows[test.rng.integers(len(awake_windows))]
        window = declining_surrogate(reference, float(fraction), test.rng)
        values[i] = network.correlation_network(window, test)["giant_component"]
    return values


def steepness_against_null(observed: float, null: np.ndarray) -> dict:
    null = np.asarray(null, float)
    return {
        "ratio_to_null_median": float(observed / np.median(null)),
        "p_value": float((1 + np.sum(null >= observed)) / (1 + null.size)),
        "null_median": float(np.median(null)),
        "null_size": int(null.size),
    }
