"""The post hoc diagnostic behind Appendix C.13: how much the pair rule alone moves the giant component.

After the human connectome failed T2b-D in Appendix C.12, this static estimate asked whether the failure could come
from how the readout counts a diffusion-MRI fibre. It runs no oscillators: every arc of the connectome is on time
independently, with the static probability of the C.12 baseline at three times the EC50 of the NMDA-antagonist-like
agent, (1 - failure) * erf(W / (2 * sqrt(2) * sigma_eff)), and the giant component is read under each pair rule
(connection_pairs.py). It is a diagnostic, not a test: it was first run before the pair-rule study was specified, and
it informed that specification.

Usage, from simulator/: ../.venv/bin/python pair_rule_diagnostic.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import calibration as cal
import connectomes
import dpc_simulator as dpc
from connection_pairs import AnatomicalConnections, PairRule
from dpc_readout import read_pair_rule

ORGANISMS = ("celegans", "drosophila", "human")
CONCENTRATION_OVER_EC50 = 3.0
DRAWS = 20
DIAGNOSTIC_SEED = 7


@dataclass(frozen=True)
class StaticDraw:
    """Probability that one arc transmits and is on time, with no oscillator dynamics and no reference feedback."""

    agent: dpc.AnaestheticAgent
    concentration: float

    def sigma_ms(self) -> float:
        return math.hypot(dpc.REFERENCE_BASELINE_JITTER_MS, self.agent.added_jitter_ms(self.concentration))

    def on_time_probability(self) -> float:
        transmits = 1 - self.agent.transmission_failure(self.concentration)
        return transmits * dpc.within_window(dpc.REFERENCE_INTEGRATION_WINDOW_MS, self.sigma_ms())


def mean_giant_shares(connections: AnatomicalConnections, probability: float, rng: np.random.Generator) -> dict[PairRule, float]:
    arc_count = connections.connection_of_arc.size
    draws = [rng.random(arc_count) < probability for _ in range(DRAWS)]
    return {rule: float(np.mean([read_pair_rule(connections, arcs, rule).giant_share for arcs in draws])) for rule in PairRule}


def main() -> None:
    draw = StaticDraw(cal.NMDA_ANTAGONIST_AGENT, CONCENTRATION_OVER_EC50 * cal.NMDA_ANTAGONIST_AGENT.half_effect_concentration)
    probability = draw.on_time_probability()
    print(f"NMDA-antagonist-like agent at {CONCENTRATION_OVER_EC50:g} times the EC50: sigma_eff {draw.sigma_ms():.1f} ms, "
          f"each arc transmits and is on time with probability {probability:.3f}; mean of {DRAWS} draws, seed {DIAGNOSTIC_SEED}")
    rng = np.random.default_rng(DIAGNOSTIC_SEED)
    for organism in ORGANISMS:
        connections = AnatomicalConnections.of(connectomes.LOADERS[organism](cal.CONNECTOME_SEED))
        shares = mean_giant_shares(connections, probability, rng)
        print(organism, ", ".join(f"{rule.value}: {share:.2f}" for rule, share in shares.items()))


if __name__ == "__main__":
    main()
