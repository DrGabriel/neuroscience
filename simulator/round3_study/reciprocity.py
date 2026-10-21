"""Analysis C: static estimates of how reciprocity and the maximal timing error move the human giant component.

No oscillators run, as in pair_rule_diagnostic.py: every arc is on time independently with the static probability of
the C.12 baseline, (1 - failure) * erf(W / (2 * sqrt(2) * sigma_eff)), and the giant component is read under the
either-direction rule of Appendix C.12 (connection_pairs.py). A share r of the anatomical connections is made two-way
and the rest one-way, in a random direction, so the number of anatomical connections never changes.

Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

import numpy as np

import calibration as cal
from connection_pairs import AnatomicalConnections, PairRule
from connectomes import Connectome
from dpc_readout import read_pair_rule
from pair_rule_diagnostic import CONCENTRATION_OVER_EC50, StaticDraw
from round3_study.crossings import SweptPoint, first_fall_below

READ_RULE = PairRule.EITHER_DIRECTION
RECIPROCAL_SHARE_STEP = 0.05
RECIPROCAL_SHARES = tuple(round(index * RECIPROCAL_SHARE_STEP, 2) for index in range(round(1 / RECIPROCAL_SHARE_STEP) + 1))
FULLY_RECIPROCAL = 1.0
REFERENCE_TIMING_ERROR_MS = cal.NMDA_ANTAGONIST_AGENT.max_added_jitter_ms
SMALLEST_TIMING_ERROR_MS, LARGEST_TIMING_ERROR_MS, TIMING_ERROR_STEP_MS = 20, 80, 5
MAXIMAL_TIMING_ERRORS_MS = tuple(float(value) for value in range(SMALLEST_TIMING_ERROR_MS, LARGEST_TIMING_ERROR_MS + TIMING_ERROR_STEP_MS, TIMING_ERROR_STEP_MS))
# A one-way connection runs from the lower- to the higher-indexed population with this probability.
ASCENDING_PROBABILITY = 0.5
RECIPROCITY_PARAMETER = "reciprocal share r"
TIMING_ERROR_PARAMETER = "maximal added timing error (ms)"
ASSIGNMENTS_PER_VALUE = 10
# As pair_rule_diagnostic.py.
DRAWS_PER_ASSIGNMENT = 20


@dataclass(frozen=True)
class SweepSize:
    """How many random assignments of direction, and how many timing draws on each, every swept value gets."""

    assignments: int
    draws: int


FULL_SIZE = SweepSize(ASSIGNMENTS_PER_VALUE, DRAWS_PER_ASSIGNMENT)


def with_reciprocal_share(fibres: AnatomicalConnections, share: float, rng: np.random.Generator) -> AnatomicalConnections:
    """The same anatomical connections, a random share of them two-way and the rest one-way in a random direction."""
    count = fibres.count
    two_way = np.zeros(count, dtype=bool)
    two_way[rng.choice(count, size=round(share * count), replace=False)] = True
    ascending = rng.random(count) < ASCENDING_PROBABILITY
    forward_sources = np.where(two_way | ascending, fibres.lower, fibres.higher)
    forward_targets = np.where(two_way | ascending, fibres.higher, fibres.lower)
    sources = np.concatenate([forward_sources, fibres.higher[two_way]])
    targets = np.concatenate([forward_targets, fibres.lower[two_way]])
    return AnatomicalConnections.of(wiring_of(sources, targets, fibres.population_count))


def wiring_of(sources: np.ndarray, targets: np.ndarray, population_count: int) -> Connectome:
    return Connectome(
        name="reassigned directions", organism="human", node_count=population_count, sources=sources, targets=targets,
        weights=np.ones(sources.size), modules=np.zeros(population_count, dtype=np.int64), module_basis="none",
        sensory_nodes=np.zeros(0, dtype=np.int64), sensory_description="none",
    )


@dataclass(frozen=True)
class StaticSetting:
    """One swept value: the fibres' reciprocal share and the probability that each arc is on time."""

    reciprocal_share: float
    on_time: float


def on_time_probability(maximal_timing_error_ms: float) -> float:
    """The static probability at three times the EC50 of the NMDA-antagonist-like agent with this maximal error."""
    agent = replace(cal.NMDA_ANTAGONIST_AGENT, max_added_jitter_ms=maximal_timing_error_ms)
    return StaticDraw(agent, CONCENTRATION_OVER_EC50 * agent.half_effect_concentration).on_time_probability()


@dataclass(frozen=True)
class StaticSweep:
    """A swept parameter, its mean giant-component share at each value, and where that share first falls below q*."""

    parameter: str
    points: tuple[SweptPoint, ...]
    crossing: float | None


@dataclass(frozen=True)
class StaticEstimator:
    """Mean giant-component share on the human fibres, over random assignments of direction and timing draws."""

    fibres: AnatomicalConnections
    size: SweepSize
    rng: np.random.Generator

    def giant_share(self, setting: StaticSetting) -> float:
        """Mean over the assignments of direction of the mean over each one's timing draws."""
        shares = [
            self.mean_over_draws(with_reciprocal_share(self.fibres, setting.reciprocal_share, self.rng), setting.on_time)
            for _ in range(self.size.assignments)
        ]
        return float(np.mean(shares))

    def mean_over_draws(self, connections: AnatomicalConnections, on_time: float) -> float:
        arc_count = connections.connection_of_arc.size
        draws = [read_pair_rule(connections, self.rng.random(arc_count) < on_time, READ_RULE).giant_share for _ in range(self.size.draws)]
        return float(np.mean(draws))

    def reciprocity_sweep(self, shares: Sequence[float]) -> StaticSweep:
        """From fully reciprocal down to fully one-way, at the reference maximal timing error."""
        on_time = on_time_probability(REFERENCE_TIMING_ERROR_MS)
        points = tuple(SweptPoint(share, self.giant_share(StaticSetting(share, on_time))) for share in sorted(shares, reverse=True))
        return StaticSweep(RECIPROCITY_PARAMETER, points, first_fall_below(points, cal.QUORUM_FRACTION))

    def timing_error_sweep(self, errors_ms: Sequence[float]) -> StaticSweep:
        """At full reciprocity, from the smallest to the largest maximal timing error."""
        points = tuple(
            SweptPoint(error, self.giant_share(StaticSetting(FULLY_RECIPROCAL, on_time_probability(error)))) for error in sorted(errors_ms)
        )
        return StaticSweep(TIMING_ERROR_PARAMETER, points, first_fall_below(points, cal.QUORUM_FRACTION))
