"""T2a-M, T2b-M: a weaker synaptic coupling, calibrated so that the awake network is below full synchrony."""

from __future__ import annotations

import statistics
from dataclasses import replace
from typing import Callable, Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_runs
import species_study as species
from readout_study.agents import abolishes_dpc_quorum
from readout_study.calibrated_values import Calibrated, closest
from readout_study.conditions import coupling_condition_name, metastable_name, with_dynamics
from readout_study.settings import COUPLING_GRID, METASTABLE_COHERENCE_RANGE, METASTABLE_COHERENCE_TARGET

AGENTS = (("T2a-M", cal.GABAERGIC_AGENT), ("T2b-M", cal.NMDA_ANTAGONIST_AGENT))


def mean_awake_coherence(runs: Sequence[species.RunSummary], organism: str, coupling: float) -> float | None:
    awake = [r.induction_coherence[0] for r in runs if r.organism == organism and r.condition == coupling_condition_name(coupling)]
    return statistics.fmean(awake) if awake else None


def in_metastable_range(coherence: float) -> bool:
    low, high = METASTABLE_COHERENCE_RANGE
    return comparisons.at_most(low, coherence) and comparisons.at_most(coherence, high)


def calibrate_coupling(runs: Sequence[species.RunSummary], organism: str) -> Calibrated:
    """Among the grid's couplings whose mean awake coherence on the calibration seeds lies in the target range, the
    one closest to the target."""
    means = [(k, mean_awake_coherence(runs, organism, k)) for k in COUPLING_GRID]
    return closest(organism, [(k, m) for k, m in means if m is not None and in_metastable_range(m)], METASTABLE_COHERENCE_TARGET)


def metastable_conditions(calibrations: Sequence[Calibrated]) -> Callable[[dynamics.IntegrationSettings], tuple[species.Condition, ...]]:
    def conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
        return tuple(
            species.Condition(metastable_name(agent, c.value), replace(with_dynamics(integration, synaptic_coupling=c.value), agent=agent), (c.organism,))
            for c in calibrations if c.value is not None
            for _, agent in AGENTS
        )
    return conditions


def statement(agent_name: str) -> str:
    low, high = METASTABLE_COHERENCE_RANGE
    return f"Weaker coupling (awake coherence {low}-{high}): the {agent_name} agent abolishes DPC quorum"


def evaluate_metastable(calibrations: Sequence[Calibrated]) -> prespecified_runs.Outcomes:
    tests = tuple(
        species.Pillar(identifier, statement(agent.name), metastable_name(agent, c.value), abolishes_dpc_quorum)
        for c in calibrations if c.value is not None
        for identifier, agent in AGENTS
    )
    return lambda runs, organisms: [o for o in species.evaluate(tests, runs, organisms) if o.runs_applicable > 0]
