"""Analysis B: the generating-function estimate of the giant strongly connected component of a directed network.

For an uncorrelated directed network with joint in/out-degree distribution p_jk (Newman, Strogatz and Watts, 2001;
Dorogovtsev, Mendes and Samukhin, 2001), each arc kept with probability pi:

    onset          pi_c = <k> / <j k>
    out-component  x = 1 - pi + pi * sum_jk p_jk j x^k / <k>     (an arc does not lead to the giant out-component)
    in-component   y = 1 - pi + pi * sum_jk p_jk k y^j / <k>     (an arc does not come from the giant in-component)
    strong share   S = sum_jk p_jk (1 - x^k) (1 - y^j)

where j is a population's in-degree and k its out-degree. The estimate keeps each population's own pair (j, k) and
ignores every correlation between populations, including reciprocity and degree assortativity. Every arc counts, as
in the directed measurement of Appendix B.5, so a repeated arc is a second chance; self-connections join nothing and
are left out.

Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import dpc_simulator as dpc
from connectomes import Connectome

FIXED_POINT_TOLERANCE = 1e-13
FIXED_POINT_ITERATIONS = 100_000
QUORUM_BISECTION_STEPS = 40


@dataclass(frozen=True)
class JointDegrees:
    """The distinct (in-degree, out-degree) pairs of a directed network and the share of populations with each."""

    in_degrees: np.ndarray
    out_degrees: np.ndarray
    shares: np.ndarray

    @classmethod
    def of_arcs(cls, sources: np.ndarray, targets: np.ndarray, population_count: int) -> JointDegrees:
        joins = sources != targets
        in_degrees = np.bincount(targets[joins], minlength=population_count)
        out_degrees = np.bincount(sources[joins], minlength=population_count)
        pairs, counts = np.unique(np.stack([in_degrees, out_degrees]), axis=1, return_counts=True)
        return cls(pairs[0].astype(float), pairs[1].astype(float), counts / population_count)

    @classmethod
    def of(cls, connectome: Connectome) -> JointDegrees:
        return cls.of_arcs(connectome.sources.astype(np.int64), connectome.targets.astype(np.int64), connectome.node_count)

    def mean_degree(self) -> float:
        return float(np.sum(self.shares * self.out_degrees))

    def mean_in_out_product(self) -> float:
        return float(np.sum(self.shares * self.in_degrees * self.out_degrees))

    def onset_threshold(self) -> float:
        """pi_c = <k> / <j k>: below it no giant strongly connected component exists."""
        return self.mean_degree() / self.mean_in_out_product()

    def strong_component_share(self, occupation: float) -> float:
        not_to_giant_out = smallest_fixed_point(ExcessMap(self.in_degrees, self.out_degrees, self), occupation)
        not_from_giant_in = smallest_fixed_point(ExcessMap(self.out_degrees, self.in_degrees, self), occupation)
        reaches_out = 1 - not_to_giant_out**self.out_degrees
        reached_in = 1 - not_from_giant_in**self.in_degrees
        return float(np.sum(self.shares * reaches_out * reached_in))

    def quorum_threshold(self, quorum: float) -> float:
        """Smallest occupation at which the estimated strong component reaches the quorum, by bisection."""
        return dpc.smallest_crossing(lambda occupation: self.strong_component_share(occupation) >= quorum, QUORUM_BISECTION_STEPS)


@dataclass(frozen=True)
class ExcessMap:
    """Generating function of the degrees met at the end of an arc: arriving_by weights the population by how often an
    arc reaches it, leaving_by counts its arcs onward."""

    arriving_by: np.ndarray
    leaving_by: np.ndarray
    joint: JointDegrees

    def __call__(self, value: float) -> float:
        weights = self.joint.shares * self.arriving_by
        return float(np.sum(weights * value**self.leaving_by) / np.sum(weights))


def smallest_fixed_point(excess: ExcessMap, occupation: float) -> float:
    """Smallest solution in [0, 1] of z = 1 - pi + pi G1(z), by iteration from zero, which rises monotonically to it."""
    value = 0.0
    for _ in range(FIXED_POINT_ITERATIONS):
        following = 1 - occupation + occupation * excess(value)
        if abs(following - value) < FIXED_POINT_TOLERANCE:
            return following
        value = following
    return value
