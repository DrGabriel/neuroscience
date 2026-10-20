"""ECoG montage: bipolar derivations, long-range pairs, loading with filter margins and band-limited analytic signals."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import phase
from .loaders import load_ecog
from .settings import ECOG, Band
from .specs import FilterSpec, LineNoise, Margins, Span

FIRST_CHANNEL_NUMBER = 1
ECOG_FILTER = FilterSpec(ECOG.sampling_hz, ECOG.filter_order)
ECOG_LINE_NOISE = LineNoise(ECOG.line_noise_hz, ECOG.notch_quality)


@dataclass(frozen=True)
class Montage:
    signals_from: list[int]  # channel numbers loaded, in order
    pairs: phase.Pairs  # indices into signals_from forming each bipolar derivation
    midpoints: np.ndarray
    long_range: phase.Pairs  # pairs of derivations


@dataclass(frozen=True)
class Experiment:
    """One Neurotycho experiment folder, the channels used and the electrode map of the monkey."""

    path: Path
    channels: list[int]
    xy_all: np.ndarray


@dataclass(frozen=True)
class Segment:
    """A span of samples in one recording session (Session1, Session2, ...)."""

    session: str
    span: Span


def build_montage(channels: list[int], xy_all: np.ndarray) -> Montage:
    xy = xy_all[np.array(channels) - FIRST_CHANNEL_NUMBER]
    pairs = phase.nearest_neighbour_pairs(xy)
    _, midpoints = phase.bipolar(np.zeros((len(channels), 1)), xy, pairs)
    return Montage(channels, pairs, midpoints, phase.long_range_pairs(midpoints, pairs, ECOG.long_range_quantile))


def derive(raw: np.ndarray, montage: Montage) -> np.ndarray:
    clean = phase.remove_line_noise(raw, ECOG.sampling_hz, ECOG_LINE_NOISE)
    return np.stack([clean[a] - clean[b] for a, b in montage.pairs])


def margin_samples() -> int:
    return int(ECOG.filter_margin_seconds * ECOG.sampling_hz)


def load_padded(experiment: Experiment, segment: Segment) -> tuple[np.ndarray, Margins]:
    """Samples of the segment with filter margins on both sides where the recording has them, and the margins obtained."""
    start, end = segment.span.start, segment.span.end
    lo = max(start - margin_samples(), 0)
    raw = load_ecog(experiment.path / segment.session, experiment.channels, slice(lo, end + margin_samples()))
    if raw.shape[1] < end - lo:
        raise ValueError(f"{segment.session}: recording ends before sample {end}")
    return raw, Margins(start - lo, raw.shape[1] - (end - lo))


def filtered(signals: np.ndarray, band: Band, margins: Margins) -> np.ndarray:
    z = phase.analytic(phase.bandpass(signals, band, ECOG_FILTER))
    return z[:, margins.before : z.shape[1] - margins.after]
