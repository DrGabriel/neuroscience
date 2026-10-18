"""Sensitivity of the conclusions to every free parameter, varied one at a time.

Percolation model: each free parameter of dpc_simulator is set to each value in its range, with
every other parameter at its reference value, and claims C1-C7 of validation_study.py are
evaluated over independent seeds. When the arousal level changes, λ is taken from the
calibration at that level, so the inertia ratio stays at its measured value.

Phase-oscillator model (human connectome): coupling, frequency spread, noise and quorum are
varied in the same way, and pillars P2a, P2b and P3 of species_study.py are evaluated.

Usage: ../.venv/bin/python sensitivity_study.py [--quick]
Exit status is non-zero if a claim fails at the reference values; like every failure in a range,
that is a result, reported in the tables.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Callable, Sequence

import calibration as cal
import dpc_simulator as dpc
import phase_dynamics as dynamics
import provenance
import reporting
from species_study import ConditionName
import species_study
import validation_study

REPORTED_PACKAGES = ("numpy", "scipy")

PERCOLATION_NODE_COUNT = 10_000
FULL_PERCOLATION_SEEDS, QUICK_PERCOLATION_SEEDS = 10, 2
FULL_OSCILLATOR_SEEDS, QUICK_OSCILLATOR_SEEDS = 5, 1
OSCILLATOR_ORGANISM = "human"
OSCILLATOR_CONDITIONS = (ConditionName.GABAERGIC, ConditionName.NMDA_ANTAGONIST, ConditionName.SENSORY_STIMULUS)
OSCILLATOR_PILLARS = ("P2a", "P2b", "P3")


ScenarioChange = Callable[[dpc.Scenario], dpc.Scenario]
DesignChange = Callable[[dynamics.SweepDesign], dynamics.SweepDesign]


@dataclass(frozen=True)
class Variation:
    parameter: str
    value: float
    is_reference: bool


def with_quorum(value: float) -> ScenarioChange:
    return lambda s: replace(s, quorum_fraction=value)


def with_arousal_level(value: float) -> ScenarioChange:
    feedback = dpc.CALIBRATED_FEEDBACK_MS_BY_AROUSAL[value]
    return lambda s: dpc.with_arousal(replace(s, timing=replace(s.timing, feedback_jitter_ms=feedback)), value)


def with_hill_coefficient(value: float) -> ScenarioChange:
    return lambda s: replace(s, agent=replace(s.agent, hill_coefficient=value))


def with_mean_degree(value: float) -> ScenarioChange:
    return lambda s: replace(s, graph_builder=s.graph_builder.with_mean_degree(value))


def with_integration_window(value: float) -> ScenarioChange:
    return lambda s: replace(s, timing=replace(s.timing, integration_window_ms=value))


def with_baseline_jitter(value: float) -> ScenarioChange:
    return lambda s: replace(s, timing=replace(s.timing, baseline_jitter_ms=value))


def with_maximal_failure(value: float) -> ScenarioChange:
    """Applies to the GABAergic-like agent only; the comparison agents in claim C1 keep their own values."""
    return lambda s: replace(s, agent=replace(s.agent, max_transmission_failure=value))


PERCOLATION_RANGES: dict[str, tuple[tuple[float, ...], float, Callable[[float], ScenarioChange]]] = {
    "Quorum fraction": ((0.3, 0.5, 0.7), dpc.REFERENCE_QUORUM_FRACTION, with_quorum),
    "Arousal level (λ recalibrated)": (tuple(dpc.CALIBRATED_FEEDBACK_MS_BY_AROUSAL), dpc.REFERENCE_AROUSAL_LEVEL, with_arousal_level),
    "Hill coefficient": ((2.0, 4.0, 8.0), dpc.GABAERGIC_LIKE_AGENT.hill_coefficient, with_hill_coefficient),
    "Mean degree": ((4.0, 8.0, 16.0), dpc.REFERENCE_MEAN_DEGREE, with_mean_degree),
    # λ is held at its reference value, so the inertia ratio is not recalibrated across these ranges.
    "Integration window W (ms)": ((1.0, 3.0, 10.0), dpc.REFERENCE_INTEGRATION_WINDOW_MS, with_integration_window),
    "Baseline jitter (ms)": ((1.0, 3.0, 10.0), dpc.REFERENCE_BASELINE_JITTER_MS, with_baseline_jitter),
    "Maximal transmission failure, GABAergic-like": ((0.6, 0.8, 0.95), dpc.GABAERGIC_LIKE_AGENT.max_transmission_failure, with_maximal_failure),
}

OSCILLATOR_RANGES: dict[str, tuple[tuple[float, ...], float, Callable[[float], DesignChange]]] = {
    "Synaptic coupling K": ((2.0, 4.0, 8.0), cal.SYNAPTIC_COUPLING, lambda v: lambda d: replace(d, dynamics=replace(d.dynamics, synaptic_coupling=v))),
    "Natural-frequency spread": ((0.25, 0.5, 1.0), cal.NATURAL_FREQUENCY_SPREAD, lambda v: lambda d: replace(d, dynamics=replace(d.dynamics, natural_frequency_spread=v))),
    "Noise intensity D": ((0.02, 0.05, 0.1), cal.NOISE_INTENSITY, lambda v: lambda d: replace(d, dynamics=replace(d.dynamics, noise_intensity=v))),
    "Quorum fraction": ((0.3, 0.5, 0.7), cal.QUORUM_FRACTION, lambda v: lambda d: replace(d, quorum_fraction=v)),
    "Jitter correlation time τ": ((0.25, 1.0, 4.0), cal.JITTER_CORRELATION_TIME, lambda v: lambda d: replace(d, dynamics=replace(d.dynamics, jitter_correlation_time=v))),
}


# ---------------------------------------------------------------------------
# Percolation model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PercolationTask:
    variation: Variation
    seed: int


def percolation_scenario(scenario: dpc.Scenario, variation: Variation) -> dpc.Scenario:
    _, _, change = PERCOLATION_RANGES[variation.parameter]
    return change(variation.value)(scenario)


def run_percolation(task: PercolationTask) -> tuple[Variation, validation_study.SeedMeasurement]:
    """Every experiment of the validation study, with this variation applied to every scenario it builds."""
    base_task = validation_study.SeedTask(PERCOLATION_NODE_COUNT, task.seed)
    return task.variation, validation_study.measure_seed(base_task, transform=lambda s: percolation_scenario(s, task.variation))


# ---------------------------------------------------------------------------
# Phase-oscillator model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OscillatorTask:
    variation: Variation
    condition: species_study.Condition
    seed: int


def run_oscillator(task: OscillatorTask) -> tuple[Variation, str, species_study.RunSummary]:
    _, _, change = OSCILLATOR_RANGES[task.variation.parameter]
    condition = replace(task.condition, design=change(task.variation.value)(task.condition.design))
    return task.variation, task.condition.name, species_study.run_task(species_study.RunTask(OSCILLATOR_ORGANISM, condition, task.seed))


def oscillator_pillars() -> dict[str, species_study.Pillar]:
    return {pillar.identifier: pillar for pillar in species_study.PILLARS if pillar.identifier in OSCILLATOR_PILLARS}


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------


def variations(ranges: dict[str, tuple[tuple[float, ...], float, object]]) -> list[Variation]:
    return [Variation(parameter, value, value == reference) for parameter, (values, reference, _) in ranges.items() for value in values]


def label(variation: Variation) -> str:
    return f"{variation.parameter} = {variation.value:g}{' (reference)' if variation.is_reference else ''}"


def grid_rows(outcomes: Sequence[reporting.CheckOutcome], variations_in_order: Sequence[Variation]) -> list[list[str]]:
    """One row per variation, one cell per check, in the order the checks were evaluated."""
    rows = []
    for variation in variations_in_order:
        cells = [outcome.cell() for outcome in outcomes if outcome.group == label(variation)]
        rows.append([label(variation), *cells])
    return rows


def percolation_outcomes(results: Sequence[tuple[Variation, validation_study.SeedMeasurement]]) -> list[reporting.CheckOutcome]:
    groups = {label(v): [m for w, m in results if w == v] for v in dict.fromkeys(v for v, _ in results)}
    return [outcome for group in groups for outcome in reporting.evaluate(validation_study.CLAIMS, {group: groups[group]})]


def oscillator_outcomes(results: Sequence[tuple[Variation, str, species_study.RunSummary]]) -> list[reporting.CheckOutcome]:
    outcomes = []
    for variation in dict.fromkeys(v for v, _, _ in results):
        for pillar in oscillator_pillars().values():
            runs = [run for v, condition, run in results if v == variation and condition == pillar.condition]
            outcomes += reporting.evaluate([reporting.Check(pillar.identifier, pillar.statement, pillar.holds_for)], {label(variation): runs})
    return outcomes


def main(arguments: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true")
    quick = parser.parse_args(arguments).quick
    started = datetime.now(timezone.utc)
    percolation_seeds = QUICK_PERCOLATION_SEEDS if quick else FULL_PERCOLATION_SEEDS
    oscillator_seeds = QUICK_OSCILLATOR_SEEDS if quick else FULL_OSCILLATOR_SEEDS
    integration = cal.QUICK_INTEGRATION if quick else cal.FULL_INTEGRATION
    conditions = [c for c in species_study.build_conditions(integration) if c.name in OSCILLATOR_CONDITIONS]

    percolation_tasks = [PercolationTask(v, cal.BASE_SEED + i) for v in variations(PERCOLATION_RANGES) for i in range(percolation_seeds)]
    oscillator_tasks = [
        OscillatorTask(v, c, cal.BASE_SEED + i) for v in variations(OSCILLATOR_RANGES) for c in conditions for i in range(oscillator_seeds)
    ]
    percolation_live = reporting.ParallelRun(
        "sensitivity: percolation", live_markdown=lambda done: "\n".join(reporting.outcome_table(percolation_outcomes(done), [label(v) for v in variations(PERCOLATION_RANGES)]))
    )
    oscillator_live = reporting.ParallelRun(
        "sensitivity: oscillator", live_markdown=lambda done: "\n".join(reporting.outcome_table(oscillator_outcomes(done), [label(v) for v in variations(OSCILLATOR_RANGES)]))
    )
    percolation_results = reporting.run_in_parallel(run_percolation, percolation_tasks, percolation_live)
    oscillator_results = reporting.run_in_parallel(run_oscillator, oscillator_tasks, oscillator_live)

    percolation = percolation_outcomes(percolation_results)
    oscillator = oscillator_outcomes(oscillator_results)
    reference_labels = {label(v) for v in variations(PERCOLATION_RANGES) if v.is_reference}
    reference_holds = all(o.holds for o in percolation if o.group in reference_labels)
    document = {
        "label": "quick" if quick else "full",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES),
        "percolation": [asdict(o) for o in percolation],
        "oscillator": [asdict(o) for o in oscillator],
        "oscillator_runs": [{"variation": asdict(v), "condition": c, "run": asdict(r)} for v, c, r in oscillator_results],
    }
    markdown = "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"### Percolation model: claims holding across seeds (N = {PERCOLATION_NODE_COUNT:,})",
        "",
        *reporting.markdown_table(["Variation", *[c.identifier for c in validation_study.CLAIMS]], grid_rows(percolation, variations(PERCOLATION_RANGES))),
        "",
        f"### Phase-oscillator model, {OSCILLATOR_ORGANISM} connectome: pillars holding across seeds",
        "",
        *reporting.markdown_table(["Variation", *oscillator_pillars()], grid_rows(oscillator, variations(OSCILLATOR_RANGES))),
        "",
    ])
    reporting.publish("sensitivity", document, markdown)
    return 0 if reference_holds else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
