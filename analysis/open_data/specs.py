"""Parameter objects passed between modules, so that no function needs more than three arguments."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np


@dataclass(frozen=True)
class SurrogateSpec:
    """Edge test: keep an edge above the (1 - alpha) quantile of ``count`` surrogates."""

    alpha: float
    count: int


@dataclass(frozen=True)
class EdgeTest:
    surrogates: SurrogateSpec
    rng: np.random.Generator

    def at_alpha(self, alpha: float) -> EdgeTest:
        return replace(self, surrogates=replace(self.surrogates, alpha=alpha))


@dataclass(frozen=True)
class Resampling:
    """Number of surrogates or bootstrap resamples, and the generator that draws them."""

    count: int
    rng: np.random.Generator


@dataclass(frozen=True)
class Span:
    """Half-open range of samples [start, end)."""

    start: int
    end: int


@dataclass(frozen=True)
class Margins:
    """Samples of filter margin available before and after a segment."""

    before: int
    after: int


@dataclass(frozen=True)
class FilterSpec:
    sampling_hz: float
    order: int


@dataclass(frozen=True)
class LineNoise:
    frequencies_hz: tuple[float, ...]
    quality: float
