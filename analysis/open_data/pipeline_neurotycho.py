"""Tests H2b (critical slowing down before LOC) and H3 (lag variability across agents) on Neurotycho macaque ECoG.

Awake blocks come from the awake eyes-closed condition, because the monkeys wore an eye mask from then until recovery,
so eye closure is matched. Anaesthetised blocks come from the marked anaesthetised condition. The induction segment
runs from the injection marker to the start of the anaesthetised condition (loss of consciousness, LOC).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import early_warning, network, phase
from .constants import State
from .loaders import Marker, epoch, find_marker, load_markers
from .montage import Experiment, Montage, Segment, build_montage, derive, filtered, load_padded
from .phase import PairedSignals, ShiftSurrogates
from .settings import ECOG, GAMMA, Band
from .specs import Margins, Resampling, Span

EPOCH_MARKERS = {
    State.AWAKE: ("AwakeEyesClosed-Start", "AwakeEyesClosed-End"),
    State.ANAESTHETISED: ("Anesthetized-Start", "Anesthetized-End"),
}
INJECTION, LOC = "AnestheticInjection", "Anesthetized-Start"
FEATURES = ("lag_variability_ms", "mean_lag_ms", "log_power", "plv", "wpli")
MUSCLE_BAND = Band("muscle", *ECOG.muscle_band)
Z_SUFFIX = "_z"
MIN_SAMPLES_FOR_SD = 2
SHIFT_FRACTION_OF_MINIMUM = 2


@dataclass(frozen=True)
class Epoch:
    """Bipolar signals of one condition, with the filter margins they carry."""

    signals: np.ndarray
    margins: Margins
    state: State


def _block_row(zb: PairedSignals, high_block: np.ndarray, band: Band) -> dict:
    window = int(ECOG.window_seconds * ECOG.sampling_hz)
    lags = phase.lag_statistics(phase.windowed_phase_differences(zb, window), band.centre_hz)
    return {
        "lag_variability_ms": float(np.mean(lags["lag_variability_ms"])),
        "mean_lag_ms": float(np.mean(lags["mean_lag_ms"])),
        "log_power": float(np.mean(phase.log_power(zb.analytic))),
        "plv": float(np.mean(phase.plv(zb))),
        "wpli": float(np.mean(phase.wpli(zb))),
        "muscle_log_power": float(np.mean(phase.log_power(high_block))),
    }


def block_feature_rows(epoch_data: Epoch, montage: Montage, band: Band) -> list[dict]:
    """One row per block: lag statistics, PLV and wPLI averaged over long-range pairs, and mean log power."""
    z = filtered(epoch_data.signals, band, epoch_data.margins)
    high = filtered(epoch_data.signals, MUSCLE_BAND, epoch_data.margins)
    block = int(ECOG.block_seconds * ECOG.sampling_hz)
    rows = []
    for start in range(0, z.shape[1] - block + 1, block):
        span = slice(start, start + block)
        rows.append({"state": epoch_data.state, **_block_row(PairedSignals(z[:, span], montage.long_range), high[:, span], band)})
    return rows


def _muscle_limit(values: np.ndarray) -> float:
    median = np.median(values)
    return median + ECOG.muscle_mad_limit * max(np.median(np.abs(values - median)), ECOG.muscle_mad_floor)


def flag_muscle(rows: list[dict]) -> list[dict]:
    """Mark blocks whose high-frequency power exceeds the median of the same state by more than the MAD limit.

    The reference is the block's own state, not the awake state, because some agents (ketamine) raise high-frequency
    power across the cortex; an awake reference would discard their anaesthetised blocks. The rule therefore removes
    transient bursts (movement, chewing) but cannot remove tonic muscle activity, which the beta-band sensitivity
    analysis addresses.
    """
    limits = {s: _muscle_limit(np.array([r["muscle_log_power"] for r in rows if r["state"] == s])) for s in {r["state"] for r in rows}}
    return [{**r, "muscle_artefact": bool(r["muscle_log_power"] > limits[r["state"]])} for r in rows]


def _standardised(value: float, reference: np.ndarray) -> float:
    sd = reference.std(ddof=1) if reference.size >= MIN_SAMPLES_FOR_SD else 0.0
    return float((value - reference.mean()) / sd) if sd > 0 else 0.0


def normalise_to_awake(rows: list[dict]) -> list[dict]:
    kept = [r for r in rows if not r["muscle_artefact"]]
    awake = {f: np.array([r[f] for r in kept if r["state"] == State.AWAKE]) for f in FEATURES}
    return [{**r, **{f"{f}{Z_SUFFIX}": _standardised(r[f], awake[f]) for f in FEATURES}} for r in kept]


def _epoch(experiment: Experiment, markers: list[Marker], state: State) -> Epoch:
    session, start, end = epoch(markers, EPOCH_MARKERS[state])
    raw, margins = load_padded(experiment, Segment(session, Span(start, end)))
    return Epoch(derive(raw, build_montage(experiment.channels, experiment.xy_all)), margins, state)


def session_blocks(experiment: Experiment, band: Band = GAMMA) -> list[dict]:
    markers = load_markers(experiment.path)
    montage = build_montage(experiment.channels, experiment.xy_all)
    rows = [row for state in EPOCH_MARKERS for row in block_feature_rows(_epoch(experiment, markers, state), montage, band)]
    return normalise_to_awake(flag_muscle(rows))


def window_giant_component(z: np.ndarray, montage: Montage, rng: np.random.Generator) -> float:
    signals = PairedSignals(z, montage.long_range)
    min_shift = int(ECOG.min_shift_seconds * ECOG.sampling_hz) // SHIFT_FRACTION_OF_MINIMUM
    spec = ShiftSurrogates(ECOG.edge_alpha, min_shift, Resampling(ECOG.surrogates_per_window, rng))
    values, threshold = phase.plv(signals), phase.plv_surrogate_threshold(signals, spec)
    adjacency = np.zeros((z.shape[0], z.shape[0]), bool)
    for (i, j), v in zip(montage.long_range, values, strict=True):
        adjacency[i, j] = adjacency[j, i] = v > threshold
    return network.giant_component_fraction(adjacency)


def induction_segment(markers: list[Marker]) -> Segment:
    injection, loc = find_marker(markers, INJECTION), find_marker(markers, LOC)
    if injection.session != loc.session or loc.index <= injection.index:
        raise ValueError("injection and LOC are not in order within one recording session")
    return Segment(injection.session, Span(injection.index, loc.index))


def induction_order_parameter(experiment: Experiment, rng: np.random.Generator, band: Band = GAMMA) -> np.ndarray:
    montage = build_montage(experiment.channels, experiment.xy_all)
    raw, margins = load_padded(experiment, induction_segment(load_markers(experiment.path)))
    z = filtered(derive(raw, montage), band, margins)
    window = int(ECOG.order_parameter_window_seconds * ECOG.sampling_hz)
    return np.array([window_giant_component(z[:, s : s + window], montage, rng) for s in range(0, z.shape[1] - window + 1, window)])


def critical_slowing(experiment: Experiment, resampling: Resampling) -> dict:
    series = induction_order_parameter(experiment, resampling.rng)
    return {"points": int(series.size), "series": series.tolist(), **early_warning.critical_slowing_test(series, resampling.rng, resampling.count)}
