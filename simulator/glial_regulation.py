"""Glial regulation of timing coherence (postulate P9): slower loops nested around the integration cycle.

Three glial cell types are represented as parameters that change slowly compared with the
millisecond integration cycle, so each is held fixed during a concentration sweep (separation
of timescales):

- Oligodendrocytes (myelin): set conduction timing; damaged myelin adds conduction-time
  variability (Kato et al., 2020), modelled as a higher baseline jitter.
- Microglia: under anaesthesia, low noradrenaline activates microglia, which lower
  noradrenaline further (Liu et al., 2019; Stowell et al., 2019; Ma et al., 2024); removing
  microglia delays induction and hastens emergence (Cao et al., 2023; He et al., 2023).
  Modelled as an arousal drive that weakens further as the coherent core collapses.
- Astrocytes: trigger slow-oscillation states (Poskanzer & Yuste, 2016); modelled as the share
  of sleep down-states that depends on astrocytic signalling.

None of these changes the network, so every variant of one seed reuses one percolation curve.
Standard library only, like dpc_simulator.py, which it extends without modifying.
"""

from __future__ import annotations

import random
from dataclasses import replace

import dpc_simulator as dpc

# Free parameters: no published measurement fixes them, so the study reports their effect over a range.
# Complete loss of myelin doubles the baseline conduction-time jitter.
DEMYELINATION_JITTER_GAIN = 1.0
MYELIN_INTEGRITY_SERIES = (1.0, 0.75, 0.5)
# 0 represents microglial depletion (PLX5622 in Cao et al., 2023, and He et al., 2023).
MICROGLIAL_DEPLETED_GAIN = 0.0
MICROGLIAL_GAIN_SERIES = (MICROGLIAL_DEPLETED_GAIN, 0.25, 0.5)
STRONGEST_MICROGLIAL_GAIN = max(MICROGLIAL_GAIN_SERIES)
# Share of sleep down-states lost when astrocytic signalling is silenced.
ASTROCYTIC_DOWN_STATE_SHARE = 0.5

DEEP_SLEEP = dpc.BrainState(dpc.SLEEP_AROUSAL_LEVEL, dpc.HUMAN_SLEEP_DOWN_STATE_FRACTION_UPPER)


def demyelinated(scenario: dpc.Scenario, myelin_integrity: float) -> dpc.Scenario:
    """Scenario with baseline jitter raised in proportion to the share of myelin lost."""
    added_share = DEMYELINATION_JITTER_GAIN * (1 - myelin_integrity)
    jitter_ms = scenario.timing.baseline_jitter_ms * (1 + added_share)
    return replace(scenario, timing=replace(scenario.timing, baseline_jitter_ms=jitter_ms))


def astrocytes_silenced(sleep: dpc.BrainState) -> dpc.BrainState:
    """Sleep state without the down-states that depend on astrocytic signalling."""
    return replace(sleep, down_state_fraction=sleep.down_state_fraction * (1 - ASTROCYTIC_DOWN_STATE_SHARE))


class MicroglialCoherenceModel(dpc.CoherenceModel):
    """Coherence model in which a microglial loop weakens arousal as the coherent core collapses.

    In wakefulness (coherent fraction 1) the loop is silent; in the collapsed state it removes
    the share microglial_gain of the arousal drive, which stabilises the unconscious state.
    With gain 0 it reproduces dpc.CoherenceModel exactly.
    """

    def __init__(
        self, timing: dpc.TimingParameters, agent: dpc.AnaestheticAgent, state: dpc.BrainState, microglial_gain: float
    ) -> None:
        super().__init__(timing, agent, state)
        self._microglial_gain = microglial_gain

    def arousal_at(self, concentration: float, coherent_fraction: float) -> float:
        return self.arousal(concentration) * (1 - self._microglial_gain * (1 - coherent_fraction))

    def reference_error_ms(self, concentration: float, coherent_fraction: float) -> float:
        # Same expression as dpc.CoherenceModel.reference_error_ms, with arousal depending on the core.
        unsustained = 1 - self.arousal_at(concentration, coherent_fraction)
        return self._timing.feedback_jitter_ms * (1 - coherent_fraction) * unsustained


def percolation_curve(scenario: dpc.Scenario) -> dpc.PercolationCurve:
    """The network's percolation curve, drawn in the same order as dpc.build_solver so results match run_scenario."""
    rng = random.Random(scenario.seed)
    return dpc.PercolationCurve.from_graph(scenario.graph_builder.build(rng), rng)


def solver_on(
    curve: dpc.PercolationCurve, scenario: dpc.Scenario, microglial_gain: float = MICROGLIAL_DEPLETED_GAIN
) -> dpc.CoherentCoreSolver:
    coherence = MicroglialCoherenceModel(scenario.timing, scenario.agent, scenario.state, microglial_gain)
    return dpc.CoherentCoreSolver(curve, coherence)


def sweep(
    curve: dpc.PercolationCurve, scenario: dpc.Scenario, microglial_gain: float = MICROGLIAL_DEPLETED_GAIN
) -> dpc.SweepResult:
    solver = solver_on(curve, scenario, microglial_gain)
    return dpc.AnaestheticSweep(solver, scenario.quorum_fraction).run(scenario.grid)


def steady_states(curve: dpc.PercolationCurve, scenario: dpc.Scenario, concentration: float) -> dpc.StableStates:
    """As dpc.stable_states, on an already-built curve."""
    solver = solver_on(curve, scenario)
    return dpc.StableStates(
        concentration=concentration,
        from_awake=solver.solve(concentration, dpc.AnaestheticSweep.AWAKE_FRACTION),
        from_collapsed=solver.solve(concentration, dpc.COLLAPSED_FRACTION),
        quorum_fraction=scenario.quorum_fraction,
    )
