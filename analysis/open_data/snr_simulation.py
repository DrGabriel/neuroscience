"""How much latency spread an SNR change alone produces (round 3, H5a signal-to-noise control; Appendix E.15).

Synthetic cortico-cortical evoked potentials with a known latency, a known trial-to-trial jitter and added noise of
known size go through the committed H5a measure (pipeline_prios.measure: baseline correction, response test, N1
latency and single-trial alignment) at the PRIOS sampling rate and trial layout. For each noise colour, true jitter,
trial count and nominal SNR, the median measured latency spread over many synthetic connections is recorded with the
median SNR measured as the data's is measured. The spread at a low SNR over that at a high one, at equal true jitter,
equal latency and equal trial count, is the relative change r that the SNR change alone produces. A null check runs
the SNR control itself (snr_matching.matched_connection) on pairs of states that differ only in SNR, where the matched
r should be near zero. No recording is read.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import combinations, product

import numpy as np

from . import pipeline_prios, snr_matching
from .constants import MS_PER_SECOND
from .pipeline_prios import Comparison, samples
from .round3_settings import SnrControl
from .settings import EVOKED

WHITE, PINK = "white", "pink"
SD_FIELD = snr_matching.SD_FIELD
CONDITION_KEYS = ("colour", "jitter_ms", "trials")
NO_POSITIONS: dict = {}


@dataclass(frozen=True)
class Cell:
    colour: str
    jitter_ms: float
    trials: int
    nominal_snr: float


@dataclass(frozen=True)
class NullPair:
    """Two states with equal latency and jitter whose SNR differs by ``ratio`` (propofol over awake)."""

    colour: str
    jitter_ms: float
    awake_snr: float
    ratio: float


def trial_times_ms(spec: SnrControl) -> tuple[np.ndarray, int]:
    """Sample times relative to the pulse over the committed trial span, and the onset sample."""
    before = samples(-EVOKED.baseline_ms[0], spec.sampling_hz)
    after = samples(EVOKED.response_end_ms + EVOKED.max_shift_ms, spec.sampling_hz)
    return (np.arange(before + after) - before) * MS_PER_SECOND / spec.sampling_hz, before


def unit_noise(colour: str, shape: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """Gaussian noise of unit SD per trial: white, or pink (power falling as 1/f)."""
    white = rng.standard_normal(shape)
    if colour == PINK:
        spectrum = np.fft.rfft(white, axis=1)
        frequency = np.arange(spectrum.shape[1], dtype=float)
        frequency[0] = 1.0
        white = np.fft.irfft(spectrum / np.sqrt(frequency), n=shape[1], axis=1)
    elif colour != WHITE:
        raise ValueError(f"unknown noise colour {colour!r}")
    return white / white.std(axis=1, keepdims=True)


def synthetic_trials(spec: SnrControl, cell: Cell, rng: np.random.Generator) -> np.ndarray:
    """N1 of amplitude ``nominal_snr`` (noise SD 1) at the stated latency plus Gaussian jitter, one row per trial."""
    times, _ = trial_times_ms(spec)
    latencies = spec.latency_ms + rng.normal(0.0, cell.jitter_ms, cell.trials)
    responses = -cell.nominal_snr * np.exp(-0.5 * ((times[None, :] - latencies[:, None]) / spec.width_ms) ** 2)
    return responses + unit_noise(cell.colour, responses.shape, rng)


def _median_or_none(values: list) -> float | None:
    kept = [v for v in values if v is not None]
    return float(np.median(kept)) if kept else None


def simulate_cell(spec: SnrControl, cell: Cell, rng: np.random.Generator) -> dict:
    _, onset = trial_times_ms(spec)
    layout = snr_matching.trial_layout(spec.sampling_hz, onset)
    spreads, snrs = [], []
    for _ in range(spec.connections):
        trials = synthetic_trials(spec, cell, rng)
        snrs.append(snr_matching.state_snr(pipeline_prios.baseline_corrected(trials, spec.sampling_hz)[0], layout)["snr"])
        measured = pipeline_prios.measure(trials, spec.sampling_hz)
        spreads.append(None if measured is None else measured[SD_FIELD])
    responding = [s for s in spreads if s is not None]
    return {**asdict(cell), "measured_snr": float(np.median(snrs)), SD_FIELD: _median_or_none(responding), "share_responding": len(responding) / spec.connections}


def simulate(spec: SnrControl, rng: np.random.Generator) -> list[dict]:
    grid = product(spec.colours, spec.jitter_ms, spec.trial_counts, spec.nominal_snr)
    return [simulate_cell(spec, Cell(*values), rng) for values in grid]


def null_pair(spec: SnrControl, pair: NullPair, rng: np.random.Generator) -> dict:
    """The SNR control on states that differ only in SNR: r as run, and r after matching."""
    awake = Cell(pair.colour, pair.jitter_ms, spec.null_trials, pair.awake_snr)
    propofol = replace(awake, nominal_snr=pair.awake_snr * pair.ratio)
    comparison = Comparison(spec.sampling_hz, NO_POSITIONS, rng)
    rows = [snr_matching.matched_connection(synthetic_trials(spec, awake, rng), synthetic_trials(spec, propofol, rng), comparison) for _ in range(spec.connections)]
    kept = [r for r in rows if r is not None]
    return {
        **asdict(pair),
        "trials": spec.null_trials,
        "connections": len(kept),
        "median_relative_change": _median_or_none([r["relative_change"] for r in kept]),
        "median_matched_relative_change": _median_or_none([r["matched_relative_change"] for r in kept]),
    }


def null_check(spec: SnrControl, rng: np.random.Generator) -> list[dict]:
    grid = product(spec.colours, spec.jitter_ms, spec.null_awake_snr, spec.null_snr_ratios)
    return [null_pair(spec, NullPair(*values), rng) for values in grid]


def _condition(row: dict) -> tuple:
    return tuple(row[k] for k in CONDITION_KEYS)


def _positive(row: dict) -> bool:
    return (row[SD_FIELD] or 0.0) > 0


def amplitude_drop_table(cells: list[dict]) -> list[dict]:
    """For each pair of SNRs at equal colour, jitter and trials: r = log(spread at the lower SNR / spread at the higher)."""
    ordered = sorted((r for r in cells if _positive(r)), key=lambda r: (_condition(r), -r["nominal_snr"]))
    return [
        {**dict(zip(CONDITION_KEYS, _condition(high))), "awake_snr": high["measured_snr"], "propofol_snr": low["measured_snr"], "relative_change": float(np.log(low[SD_FIELD] / high[SD_FIELD]))}
        for high, low in combinations(ordered, 2)
        if _condition(high) == _condition(low)
    ]


def snr_only_change(cells: list[dict], snr_pair: tuple[float, float]) -> list[dict]:
    """r that an SNR change alone produces, for each condition, interpolated in log SNR at (awake, propofol)."""
    out = []
    for condition in sorted({_condition(r) for r in cells}):
        out.append({**dict(zip(CONDITION_KEYS, condition)), **_interpolated_change(_usable_rows(cells, condition), snr_pair)})
    return out


def _usable_rows(cells: list[dict], condition: tuple) -> list[dict]:
    return sorted((r for r in cells if _condition(r) == condition and _positive(r)), key=lambda r: r["measured_snr"])


def _log_curve(rows: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    return np.log([r["measured_snr"] for r in rows]), np.log([r[SD_FIELD] for r in rows])


def _interpolated_change(rows: list[dict], snr_pair: tuple[float, float]) -> dict:
    if not rows:
        return {"relative_change": None, "inside_simulated_range": False}
    x, y = _log_curve(rows)
    log_sd = [float(np.interp(np.log(s), x, y)) for s in snr_pair]
    inside = all(x[0] <= np.log(s) <= x[-1] for s in snr_pair)
    return {"relative_change": log_sd[1] - log_sd[0], "inside_simulated_range": bool(inside)}


def spread_at(cells: list[dict], condition: tuple, snr: float) -> float | None:
    """Median simulated spread (ms) under one condition (colour, jitter, trials), interpolated in log SNR."""
    rows = _usable_rows(cells, condition)
    if not rows:
        return None
    x, y = _log_curve(rows)
    return float(np.exp(np.interp(np.log(snr), x, y)))
