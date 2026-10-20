"""Cross-species study: the DPC pillars tested on empirical connectomes and on plant tissue.

For each organism, every condition is run over independent seeds in parallel. Each pillar
of the paper is checked per seed, and a JSON and Markdown report records the results with
the machine, software versions, dataset digests and source hashes of the run.

Usage:
    ../.venv/bin/python species_study.py            # full study
    ../.venv/bin/python species_study.py --quick    # short smoke run

Exit status is non-zero if any pillar fails for any seed of any organism. A failing pillar
is a scientific result, not a software error: the report is written either way.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from datetime import datetime, timezone
from functools import lru_cache, partial
from pathlib import Path
from typing import Callable, Sequence

import calibration as cal
import comparisons
import connectomes
import phase_dynamics as dynamics
import plant_tissue
import provenance
import reporting

REPORTED_PACKAGES = (*provenance.NUMERICAL_PACKAGES, "pyarrow", "matplotlib")


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------


class ConditionName(StrEnum):
    """Experimental conditions of the cross-species study; names appear in reports and figures."""

    GABAERGIC = "GABAergic-like"
    NMDA_ANTAGONIST = "NMDA-antagonist-like"
    NMDA_FIXED_OFFSETS = "NMDA-antagonist-like, fixed timing offsets"
    NO_REFERENCE_FEEDBACK = "GABAergic-like, no reference feedback"
    SENSORY_STIMULUS = "GABAergic-like, sensory stimulus"
    NMDA_CONDUCTION_LENGTH_JITTER = "NMDA-antagonist-like, conduction-length jitter"
    CONDUCTION_DELAYS = "GABAergic-like, conduction delays"
    KETAMINE_PATHWAYS = "NMDA-antagonist-like on sensory pathways, sensory stimulus"
    ADAPTIVE_RATE = "GABAergic-like, adaptive reference rate"
    NMDA_ADAPTIVE_RATE = "NMDA-antagonist-like, adaptive reference rate"
    SIGNED = "GABAergic-like, signed connections (GABA inhibitory)"
    SIGNED_WITH_GLUTAMATE = "GABAergic-like, signed connections (GABA and glutamate inhibitory)"
    NULL_REWIRED = "GABAergic-like, rewired connectome (null model)"
    NULL_REWIRED_STIMULUS = "GABAergic-like, sensory stimulus, rewired connectome (null model)"


@dataclass(frozen=True)
class Condition:
    """One experimental manipulation applied to a connectome."""

    name: str
    design: dynamics.SweepDesign
    organisms: tuple[str, ...]
    rewired: bool = False


EVERY_ORGANISM = tuple(cal.ORGANISMS)
WITH_TRACT_LENGTHS = tuple(organism for organism, spec in cal.ORGANISMS.items() if spec.has_tract_lengths)
WITH_CONNECTION_SIGNS = tuple(organism for organism, spec in cal.ORGANISMS.items() if spec.has_connection_signs)


def agent_conditions(base: dynamics.SweepDesign) -> tuple[Condition, ...]:
    nmda = replace(base, agent=cal.NMDA_ANTAGONIST_AGENT)
    return (
        Condition(ConditionName.GABAERGIC, base, EVERY_ORGANISM),
        Condition(ConditionName.NMDA_ANTAGONIST, nmda, EVERY_ORGANISM),
        Condition(ConditionName.NMDA_FIXED_OFFSETS, replace(nmda, jitter_dynamics=dynamics.JitterDynamics.FIXED), EVERY_ORGANISM),
    )


def reference_conditions(base: dynamics.SweepDesign) -> tuple[Condition, ...]:
    without_feedback = replace(cal.POPULATION_DYNAMICS, reference_feedback=0.0)
    with_fallback = replace(cal.POPULATION_DYNAMICS, fallback_frequency_hz=cal.ALPHA_FALLBACK_FREQUENCY_HZ)
    return (
        Condition(ConditionName.NO_REFERENCE_FEEDBACK, replace(base, dynamics=without_feedback), EVERY_ORGANISM),
        Condition(ConditionName.ADAPTIVE_RATE, replace(base, dynamics=with_fallback), EVERY_ORGANISM),
        Condition(ConditionName.NMDA_ADAPTIVE_RATE, replace(base, agent=cal.NMDA_ANTAGONIST_AGENT, dynamics=with_fallback), EVERY_ORGANISM),
    )


def signed_conditions(base: dynamics.SweepDesign) -> tuple[Condition, ...]:
    return (
        Condition(ConditionName.SIGNED, replace(base, sign_rule=connectomes.SIGN_RULE_GABA), WITH_CONNECTION_SIGNS),
        Condition(ConditionName.SIGNED_WITH_GLUTAMATE, replace(base, sign_rule=connectomes.SIGN_RULE_GABA_AND_GLUTAMATE), WITH_CONNECTION_SIGNS),
    )


def stimulus_and_tract_conditions(base: dynamics.SweepDesign) -> tuple[Condition, ...]:
    length_jitter = replace(base, agent=cal.NMDA_ANTAGONIST_AGENT, jitter_scaling=dynamics.JitterScaling.CONDUCTION_LENGTH)
    delays = replace(base, conduction_velocity_m_per_s=cal.CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S)
    return (
        Condition(ConditionName.SENSORY_STIMULUS, replace(base, stimulus=cal.SENSORY_STIMULUS), EVERY_ORGANISM),
        Condition(ConditionName.NMDA_CONDUCTION_LENGTH_JITTER, length_jitter, WITH_TRACT_LENGTHS),
        Condition(ConditionName.CONDUCTION_DELAYS, delays, WITH_TRACT_LENGTHS),
    )


def null_and_pathway_conditions(base: dynamics.SweepDesign) -> tuple[Condition, ...]:
    with_stimulus = replace(base, stimulus=cal.SENSORY_STIMULUS)
    ketamine_pathways = replace(with_stimulus, agent=cal.NMDA_ANTAGONIST_AGENT, jitter_scaling=dynamics.JitterScaling.SENSORY_PATHWAYS)
    return (
        Condition(ConditionName.NULL_REWIRED, base, cal.NULL_MODEL_ORGANISMS, rewired=True),
        Condition(ConditionName.NULL_REWIRED_STIMULUS, with_stimulus, cal.NULL_MODEL_ORGANISMS, rewired=True),
        Condition(ConditionName.KETAMINE_PATHWAYS, ketamine_pathways, EVERY_ORGANISM),
    )


CONDITION_GROUPS = (agent_conditions, reference_conditions, signed_conditions, stimulus_and_tract_conditions, null_and_pathway_conditions)


def build_conditions(integration: dynamics.IntegrationSettings) -> tuple[Condition, ...]:
    base = cal.base_sweep_design(integration)
    return tuple(condition for group in CONDITION_GROUPS for condition in group(base))


# ---------------------------------------------------------------------------
# Running one seed
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunTask:
    organism: str
    condition: Condition
    seed: int


@dataclass(frozen=True)
class RunSummary:
    organism: str
    condition: str
    seed: int
    loss_concentration: float | None
    recovery_concentration: float | None
    hysteresis_width: float | None
    susceptibility_surge: float
    susceptibility_peak_concentration: float
    local_global_dissociation: float | None
    awake_broadcast_ratio: float | None
    unconscious_broadcast_ratio: float | None
    awake_sensory_entrainment: float | None
    unconscious_sensory_entrainment: float | None
    awake_susceptibility: float
    loss_susceptibility: float | None
    deepest_coherence_fraction: float
    deepest_broadcast_ratio: float | None
    concentrations: tuple[float, ...]
    induction_coherence: tuple[float, ...]
    emergence_coherence: tuple[float, ...]
    induction_susceptibility: tuple[float, ...]
    induction_broadcast_ratio: tuple[float | None, ...]
    seconds: float
    # Absolute locking values, needed to subtract a chance floor (K1c); absent from reports written before 20 October 2026.
    awake_broadcast_entrainment: float | None = None
    deepest_broadcast_entrainment: float | None = None
    deepest_sensory_entrainment: float | None = None


@lru_cache(maxsize=None)
def load_connectome(organism: str) -> connectomes.Connectome:
    return connectomes.LOADERS[organism](cal.CONNECTOME_SEED)


def susceptibility_at_loss(record: dynamics.InductionEmergenceRecord) -> float | None:
    """Susceptibility at the last conscious concentration of induction."""
    loss = dynamics.loss_concentration(record)
    return None if loss is None else record.at(loss).susceptibility


def design_for(task: RunTask) -> dynamics.SweepDesign:
    """The condition's design with the task's seed and any organism-specific numerical resolution."""
    spec = cal.ORGANISMS[task.organism]
    design = replace(task.condition.design, seed=task.seed)
    design = replace(design, grid=replace(design.grid, step=spec.grid_step(design.grid.step)))
    if spec.relaxation_steps is not None and design.integration.relaxation_steps > spec.relaxation_steps:
        design = replace(design, integration=replace(design.integration, relaxation_steps=spec.relaxation_steps))
    return design


def connectome_for(task: RunTask) -> connectomes.Connectome:
    """The organism's connectome, or its rewired copy for this seed when the condition is a null model."""
    connectome = load_connectome(task.organism)
    return connectome.rewired(task.seed) if task.condition.rewired else connectome


def run_task(task: RunTask, design: dynamics.SweepDesign | None = None) -> RunSummary:
    """One sweep. design replaces design_for(task) when a caller, such as the convergence study, has already
    adjusted the organism's numerical settings and must not have them reapplied."""
    started = time.perf_counter()
    record = dynamics.run_induction_emergence(connectome_for(task), design or design_for(task))
    return summarise(task, record, time.perf_counter() - started)


def summarise(task: RunTask, record: dynamics.InductionEmergenceRecord, seconds: float) -> RunSummary:
    """The quantities every study reads from one sweep."""
    unconscious = record.first_unconscious
    awake = record.induction[0]
    return RunSummary(
        organism=task.organism,
        condition=task.condition.name,
        seed=task.seed,
        loss_concentration=dynamics.loss_concentration(record),
        recovery_concentration=dynamics.recovery_concentration(record),
        hysteresis_width=dynamics.hysteresis_width(record),
        susceptibility_surge=dynamics.susceptibility_surge(record),
        susceptibility_peak_concentration=dynamics.susceptibility_peak(record).concentration,
        local_global_dissociation=dynamics.local_global_dissociation(record),
        awake_broadcast_ratio=dynamics.broadcast_ratio(awake),
        unconscious_broadcast_ratio=None if unconscious is None else dynamics.broadcast_ratio(unconscious),
        awake_sensory_entrainment=awake.sensory_entrainment,
        unconscious_sensory_entrainment=None if unconscious is None else unconscious.sensory_entrainment,
        awake_susceptibility=awake.susceptibility,
        loss_susceptibility=susceptibility_at_loss(record),
        deepest_coherence_fraction=record.induction[-1].global_coherence / record.awake_coherence,
        deepest_broadcast_ratio=dynamics.broadcast_ratio(record.induction[-1]),
        concentrations=tuple(point.concentration for point in record.induction),
        induction_coherence=tuple(point.global_coherence for point in record.induction),
        emergence_coherence=tuple(point.global_coherence for point in reversed(record.emergence)),
        induction_susceptibility=tuple(point.susceptibility for point in record.induction),
        induction_broadcast_ratio=tuple(dynamics.broadcast_ratio(point) for point in record.induction),
        seconds=seconds,
        awake_broadcast_entrainment=awake.broadcast_entrainment,
        deepest_broadcast_entrainment=record.induction[-1].broadcast_entrainment,
        deepest_sensory_entrainment=record.induction[-1].sensory_entrainment,
    )


# ---------------------------------------------------------------------------
# Pillars
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pillar:
    identifier: str
    statement: str
    condition: str
    holds_for: Callable[[RunSummary], bool]


def fluctuation_surge_at_collapse(run: RunSummary) -> bool:
    if run.loss_concentration is None:
        return False
    distance = abs(run.susceptibility_peak_concentration - run.loss_concentration)
    return run.susceptibility_surge >= cal.MINIMUM_SUSCEPTIBILITY_SURGE and comparisons.at_most(distance, cal.SURGE_WINDOW)


def quorum_is_lost(run: RunSummary) -> bool:
    return run.loss_concentration is not None


def no_hysteresis(run: RunSummary) -> bool:
    return run.hysteresis_width is not None and comparisons.equals(run.hysteresis_width, 0)


def non_negative_hysteresis(run: RunSummary) -> bool:
    return run.hysteresis_width is not None and comparisons.at_most(0, run.hysteresis_width)


def broadcast_collapses_while_sensory_retains(run: RunSummary, retention: float) -> bool:
    values = (
        run.awake_broadcast_ratio,
        run.unconscious_broadcast_ratio,
        run.awake_sensory_entrainment,
        run.unconscious_sensory_entrainment,
    )
    if any(value is None for value in values):
        return False
    broadcast_collapses = run.unconscious_broadcast_ratio <= cal.BROADCAST_COLLAPSE_FRACTION * run.awake_broadcast_ratio
    sensory_persists = run.unconscious_sensory_entrainment >= retention * run.awake_sensory_entrainment
    return broadcast_collapses and sensory_persists


def local_processing_without_broadcast(run: RunSummary) -> bool:
    return broadcast_collapses_while_sensory_retains(run, retention=1.0)


def local_processing_without_broadcast_post_hoc(run: RunSummary) -> bool:
    return broadcast_collapses_while_sensory_retains(run, retention=cal.POST_HOC_SENSORY_RETENTION)


def fluctuations_rise_before_collapse(run: RunSummary) -> bool:
    if run.loss_susceptibility is None:
        return False
    awake = max(run.awake_susceptibility, sys.float_info.min)
    return run.loss_susceptibility / awake >= cal.MINIMUM_SUSCEPTIBILITY_SURGE


def disconnected_but_internally_coherent(run: RunSummary) -> bool:
    """At the highest concentration, quorum still holds while the stimulus no longer propagates."""
    if run.deepest_broadcast_ratio is None or run.awake_broadcast_ratio is None:
        return False
    keeps_quorum = run.deepest_coherence_fraction >= cal.QUORUM_FRACTION
    broadcast_collapses = run.deepest_broadcast_ratio <= cal.BROADCAST_COLLAPSE_FRACTION * run.awake_broadcast_ratio
    return keeps_quorum and broadcast_collapses


def local_coherence_outlasts_global(run: RunSummary) -> bool:
    return run.local_global_dissociation is not None and run.local_global_dissociation > 0


PILLARS = (
    Pillar("P1", "Coherence fluctuations surge at the collapse (paradoxical excitation as critical fluctuation)", ConditionName.GABAERGIC, fluctuation_surge_at_collapse),
    Pillar("P2a", "GABAergic-like agent abolishes quorum", ConditionName.GABAERGIC, quorum_is_lost),
    Pillar("P2b", "NMDA-antagonist-like agent abolishes quorum", ConditionName.NMDA_ANTAGONIST, quorum_is_lost),
    Pillar("P3", "Stimulated sensory area keeps processing while broadcast collapses", ConditionName.SENSORY_STIMULUS, local_processing_without_broadcast),
)

# Reported, not part of the verdict. Neural inertia is tested by the percolation model, where
# it is calibrated; in the oscillator model it stayed within run-to-run noise (calibration.py).
@dataclass(frozen=True)
class FallbackComparison:
    """Loss concentrations of one organism and seed with a fixed and an adaptive reference rate, for both agents."""

    organism: str
    seed: int
    gabaergic_fixed: float | None
    gabaergic_adaptive: float | None
    nmda_fixed: float | None
    nmda_adaptive: float | None

    @property
    def gabaergic_gain(self) -> float | None:
        return gain(self.gabaergic_fixed, self.gabaergic_adaptive)

    @property
    def nmda_gain(self) -> float | None:
        return gain(self.nmda_fixed, self.nmda_adaptive)


def gain(fixed: float | None, adaptive: float | None) -> float | None:
    """Rise in the loss concentration produced by the adaptive rate; undefined if either loss is."""
    return None if fixed is None or adaptive is None else adaptive - fixed


FALLBACK_CONDITIONS = (
    ConditionName.GABAERGIC, ConditionName.ADAPTIVE_RATE, ConditionName.NMDA_ANTAGONIST, ConditionName.NMDA_ADAPTIVE_RATE,
)


def fallback_comparisons(runs: Sequence[RunSummary]) -> list[FallbackComparison]:
    by_key = {(r.organism, r.condition, r.seed): r.loss_concentration for r in runs}
    keys = {(r.organism, r.seed) for r in runs}
    comparisons = []
    for organism, seed in sorted(keys):
        losses = [by_key.get((organism, condition, seed), MISSING) for condition in FALLBACK_CONDITIONS]
        if MISSING not in losses:
            comparisons.append(FallbackComparison(organism, seed, *losses))
    return comparisons


MISSING = object()


def larger_gain_against_jitter(comparison: FallbackComparison) -> bool | None:
    if comparison.gabaergic_gain is None or comparison.nmda_gain is None:
        return None
    return comparisons.exceeds(comparison.nmda_gain, comparison.gabaergic_gain)


FALLBACK_TESTS = (
    reporting.Check(
        "F1", "Adaptive reference rate (P8) raises the loss concentration, GABAergic-like agent, paired by seed",
        lambda c: None if c.gabaergic_gain is None else comparisons.exceeds(c.gabaergic_gain, 0),
    ),
    reporting.Check(
        "F2", "Adaptive reference rate (P8) raises the loss concentration, NMDA-antagonist-like agent, paired by seed",
        lambda c: None if c.nmda_gain is None else comparisons.exceeds(c.nmda_gain, 0),
    ),
    reporting.Check(
        "F3", "The adaptive rate protects more against the jitter-type than the failure-type agent, paired by seed",
        larger_gain_against_jitter,
    ),
)


def evaluate_fallback(runs: Sequence[RunSummary], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    comparisons = fallback_comparisons(runs)
    groups = {cal.ORGANISMS[o].display_name: [c for c in comparisons if c.organism == o] for o in organisms}
    return reporting.evaluate(FALLBACK_TESTS, groups)


# Pre-specified tests of the extensions the author adopted to answer reviewer objections
# (Section 9). Reported, not part of the verdict.
EXTENSION_TESTS = (
    Pillar("D1", "With measured conduction delays, the GABAergic-like agent still abolishes quorum", ConditionName.CONDUCTION_DELAYS, quorum_is_lost),
    Pillar("SG1", "With GABA connections signed inhibitory, the GABAergic-like agent still abolishes quorum", ConditionName.SIGNED, quorum_is_lost),
    Pillar("SG2", "With GABA and glutamate connections signed inhibitory, the GABAergic-like agent still abolishes quorum", ConditionName.SIGNED_WITH_GLUTAMATE, quorum_is_lost),
    Pillar("K1", "Ketamine pathway hypothesis: quorum persists while the stimulus stops propagating", ConditionName.KETAMINE_PATHWAYS, disconnected_but_internally_coherent),
)

SECONDARY_ANALYSES = (
    Pillar("P1b", "Post hoc: fluctuations rise at least tenfold on the conscious side of the threshold", ConditionName.GABAERGIC, fluctuations_rise_before_collapse),
    Pillar("P3b", "Post hoc: sensory area retains at least 80% of its entrainment while broadcast collapses", ConditionName.SENSORY_STIMULUS, local_processing_without_broadcast_post_hoc),
    Pillar("H0", "No hysteresis without reference feedback", ConditionName.NO_REFERENCE_FEEDBACK, no_hysteresis),
    Pillar("N1", "Null model: on a rewired connectome with the same degrees, the GABAergic-like agent abolishes quorum", ConditionName.NULL_REWIRED, quorum_is_lost),
    Pillar("N2", "Null model: on a rewired connectome, the stimulated area keeps processing while broadcast collapses", ConditionName.NULL_REWIRED_STIMULUS, local_processing_without_broadcast),
    Pillar("H1", "Hysteresis is never negative with reference feedback", ConditionName.GABAERGIC, non_negative_hysteresis),
    Pillar("S1", "Spontaneous local coherence outlasts global coherence (uniform jitter)", ConditionName.NMDA_ANTAGONIST, local_coherence_outlasts_global),
    Pillar("S2", "Spontaneous local coherence outlasts global coherence (conduction-length jitter)", ConditionName.NMDA_CONDUCTION_LENGTH_JITTER, local_coherence_outlasts_global),
    Pillar("S3", "Hysteresis is strictly positive with reference feedback", ConditionName.GABAERGIC, lambda run: comparisons.exceeds(run.hysteresis_width or 0, 0)),
    Pillar("S4", "NMDA-antagonist-like agent abolishes quorum with fixed timing offsets instead of fluctuating jitter", ConditionName.NMDA_FIXED_OFFSETS, quorum_is_lost),
)


def evaluate(pillars: Sequence[Pillar], runs: Sequence[RunSummary], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    """Each pillar is evaluated on its own condition, separately for each organism."""
    outcomes = []
    for pillar in pillars:
        groups = {
            cal.ORGANISMS[organism].display_name: [r for r in runs if r.organism == organism and r.condition == pillar.condition]
            for organism in organisms
        }
        outcomes += reporting.evaluate([reporting.Check(pillar.identifier, pillar.statement, pillar.holds_for)], groups)
    return outcomes


# ---------------------------------------------------------------------------
# Plant tissue
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlantSummary:
    junction_conductance: float
    seed: int
    block_open_fraction: float | None


def run_plant_task(conductance_and_seed: tuple[float, int]) -> PlantSummary:
    conductance, seed = conductance_and_seed
    design = replace(cal.PLANT_TISSUE, junction_conductance=conductance, seed=seed)
    sweep = plant_tissue.concentration_sweep(design)
    return PlantSummary(conductance, seed, plant_tissue.block_open_fraction(sweep, cal.PROPAGATION_FAILURE_FRACTION))


def blocks_by_conductance(summaries: Sequence[PlantSummary]) -> dict[float, list[float | None]]:
    return {
        conductance: [s.block_open_fraction for s in summaries if s.junction_conductance == conductance]
        for conductance in cal.PLANT_JUNCTION_CONDUCTANCES
        if any(s.junction_conductance == conductance for s in summaries)
    }


def never_below_bond_threshold(blocks: Sequence[float | None]) -> bool:
    return None not in blocks and all(value >= plant_tissue.SQUARE_LATTICE_BOND_THRESHOLD for value in blocks)


def block_falls_with_conductance(by_conductance: dict[float, list[float | None]]) -> bool:
    means = [statistics.fmean(values) for values in by_conductance.values() if None not in values]
    return len(means) == len(by_conductance) and all(earlier > later for earlier, later in zip(means, means[1:]))


def plant_claims(summaries: Sequence[PlantSummary]) -> dict[str, bool]:
    by_conductance = blocks_by_conductance(summaries)
    blocks = [value for values in by_conductance.values() for value in values]
    return {
        "Propagation is blocked in every run": None not in blocks,
        "Block never occurs below the bond-percolation threshold (1/2)": never_below_bond_threshold(blocks),
        "Block point falls as junction conductance rises": block_falls_with_conductance(by_conductance),
    }


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StudyDesign:
    label: str
    integration: dynamics.IntegrationSettings
    seeds_per_organism: dict[str, int]
    plant_seeds: int


def tasks_for(design: StudyDesign) -> list[RunTask]:
    return [
        RunTask(organism, condition, cal.BASE_SEED + index)
        for condition in build_conditions(design.integration)
        for organism in condition.organisms
        for index in range(design.seeds_per_organism[organism])
    ]


@dataclass(frozen=True)
class SpeciesResults:
    """Everything one study run produced, before it is turned into a report."""

    label: str
    started_utc: str
    design: dict[str, object]
    runs: list[RunSummary]
    plants: list[PlantSummary]


def pillars_markdown(runs: Sequence[RunSummary], organisms: Sequence[str]) -> str:
    sections = [
        (title, evaluate(pillars, runs, organisms))
        for title, pillars in (("Pillars", PILLARS), ("Extension tests", EXTENSION_TESTS), ("Secondary analyses", SECONDARY_ANALYSES))
    ]
    return reporting.outcome_sections(sections, [cal.ORGANISMS[o].display_name for o in organisms])


def run_study(design: StudyDesign) -> SpeciesResults:
    started = datetime.now(timezone.utc).isoformat()
    runs: list[RunSummary] = []
    tasks = tasks_for(design)
    for organism, spec in cal.ORGANISMS.items():
        organism_tasks = [task for task in tasks if task.organism == organism]
        live = reporting.ParallelRun(f"species: {spec.display_name}", spec.worker_processes, live_markdown=partial(pillars_markdown, organisms=[organism]))
        runs.extend(reporting.run_in_parallel(run_task, organism_tasks, live))
    plant_inputs = [(g, cal.BASE_SEED + i) for g in cal.PLANT_JUNCTION_CONDUCTANCES for i in range(design.plant_seeds)]
    plants = reporting.run_in_parallel(run_plant_task, plant_inputs, reporting.ParallelRun("species: plant tissue"))
    design_record = {"integration": asdict(design.integration), "seeds_per_organism": design.seeds_per_organism, "plant_seeds": design.plant_seeds}
    return SpeciesResults(design.label, started, design_record, runs, plants)


def assemble_report(results: SpeciesResults) -> dict[str, object]:
    organisms = list(cal.ORGANISMS)
    return {
        "label": results.label,
        "started_utc": results.started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES)
        | {"datasets": [dataset_record(source) for source in connectomes.DATASET_SOURCES]},
        "calibration": cal.as_record(),
        "design": results.design,
        "pillars": [asdict(o) | {"holds": o.holds} for o in evaluate(PILLARS, results.runs, organisms)],
        "extension_tests": [asdict(o) for o in evaluate(EXTENSION_TESTS, results.runs, organisms) + evaluate_fallback(results.runs, organisms)],
        "fallback_comparisons": [asdict(c) for c in fallback_comparisons(results.runs)],
        "secondary": [asdict(o) for o in evaluate(SECONDARY_ANALYSES, results.runs, organisms)],
        "plant_claims": plant_claims(results.plants),
        "runs": [asdict(run) for run in results.runs],
        "plant_runs": [asdict(plant) for plant in results.plants],
    }


def dataset_record(source: connectomes.DatasetSource) -> dict[str, object]:
    present = source.path.exists()
    return {
        "key": source.key,
        "organism": source.organism,
        "url": source.url,
        "licence": source.licence,
        "redistributed": source.redistributed,
        "sha256": provenance.file_sha256(source.path) if present else "not downloaded",
        "citations": list(source.citations),
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


QUANTITIES: tuple[tuple[str, str, str], ...] = (
    ("c_off", ConditionName.GABAERGIC, "loss_concentration"),
    ("c_off, adaptive reference rate (P8)", ConditionName.ADAPTIVE_RATE, "loss_concentration"),
    ("c_on", ConditionName.GABAERGIC, "recovery_concentration"),
    ("Hysteresis", ConditionName.GABAERGIC, "hysteresis_width"),
    ("Susceptibility surge (peak / awake)", ConditionName.GABAERGIC, "susceptibility_surge"),
    ("c_off", ConditionName.NMDA_ANTAGONIST, "loss_concentration"),
    ("Broadcast ratio, awake", ConditionName.SENSORY_STIMULUS, "awake_broadcast_ratio"),
    ("Broadcast ratio, first unconscious", ConditionName.SENSORY_STIMULUS, "unconscious_broadcast_ratio"),
    ("Sensory entrainment, awake", ConditionName.SENSORY_STIMULUS, "awake_sensory_entrainment"),
    ("Sensory entrainment, first unconscious", ConditionName.SENSORY_STIMULUS, "unconscious_sensory_entrainment"),
    ("Local minus global coherence above chance", ConditionName.NMDA_ANTAGONIST, "local_global_dissociation"),
    ("Seconds per run", ConditionName.GABAERGIC, "seconds"),
)


def outcomes_from(records: Sequence[dict[str, object]]) -> list[reporting.CheckOutcome]:
    return [reporting.CheckOutcome(**{key: value for key, value in record.items() if key != "holds"}) for record in records]


def measurement_rows_for(
    quantities: Sequence[tuple[str, str, str]], runs: Sequence[dict[str, object]], organisms: Sequence[str]
) -> list[list[str]]:
    return [
        [label, condition, *[reporting.describe([r[field] for r in runs if r["organism"] == o and r["condition"] == condition]) for o in organisms]]
        for label, condition, field in quantities
    ]


def plant_rows(report: dict[str, object]) -> list[list[str]]:
    return [
        [f"{conductance:g}", reporting.describe([p["block_open_fraction"] for p in report["plant_runs"] if p["junction_conductance"] == conductance])]
        for conductance in cal.PLANT_JUNCTION_CONDUCTANCES
    ]


def reevaluation_note(report: dict[str, object]) -> list[str]:
    if "reevaluated_from" not in report:
        return []
    return [
        f"Re-evaluation: the runs of `{report['reevaluated_from']}` (run {report['run_started_utc']} to {report['run_finished_utc']}), "
        "unchanged, with every verdict recomputed by the code recorded above. No simulation was run.",
        "",
    ]


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in cal.ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    datasets = [f"| Dataset `{d['key']}` | {d['licence']}; SHA-256 `{d['sha256']}` |" for d in report["provenance"]["datasets"]]
    return "\n".join([
        *reporting.run_metadata_section(report, [*provenance.markdown_rows(report["provenance"]), *datasets]),
        *reevaluation_note(report),
        "### Pillars (seeds in which the pillar holds)",
        "",
        *reporting.outcome_table(outcomes_from(report["pillars"]), names),
        "",
        "### Extension tests (pre-specified; not part of the verdict)",
        "",
        *reporting.outcome_table(outcomes_from(report["extension_tests"]), names),
        "",
        "### Secondary analyses (not part of the verdict)",
        "",
        *reporting.outcome_table(outcomes_from(report["secondary"]), names),
        "",
        "### Measurements (mean ± SD across seeds; concentrations relative to EC50)",
        "",
        *reporting.markdown_table(["Quantity", "Condition", *names], measurement_rows_for(QUANTITIES, report["runs"], organisms)),
        "",
        "### Plant tissue (cellular control)",
        "",
        *reporting.markdown_table(["Claim", "Holds"], [[claim, "yes" if holds else "no"] for claim, holds in report["plant_claims"].items()]),
        "",
        *reporting.markdown_table(["Junction conductance", "Open-junction fraction at propagation block"], plant_rows(report)),
        "",
    ])


def all_pillars_hold(report: dict[str, object]) -> bool:
    return all(outcome["holds"] for outcome in report["pillars"]) and all(report["plant_claims"].values())


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="short smoke run instead of the full study")
    parser.add_argument(
        "--reevaluate", type=Path, metavar="REPORT",
        help="recompute the verdicts of a stored report's runs with the current code; no simulation is run",
    )
    return parser.parse_args(arguments)


def design_from(options: argparse.Namespace) -> StudyDesign:
    if options.quick:
        return StudyDesign(reporting.RunLabel.QUICK, cal.QUICK_INTEGRATION, {o: 1 for o in cal.ORGANISMS}, plant_seeds=1)
    seeds = {organism: spec.full_study_seeds for organism, spec in cal.ORGANISMS.items()}
    return StudyDesign(reporting.RunLabel.FULL, cal.FULL_INTEGRATION, seeds, cal.PLANT_SEEDS)


def results_from_report(stored: dict[str, object]) -> SpeciesResults:
    """The runs of a stored report, unchanged, ready to be evaluated again. The new report is named by the time of
    evaluation, so it never replaces the report it was read from."""
    def run_from(record: dict[str, object]) -> RunSummary:
        return RunSummary(**{field: tuple(value) if isinstance(value, list) else value for field, value in record.items()})
    return SpeciesResults(
        str(stored["label"]), datetime.now(timezone.utc).isoformat(), dict(stored["design"]),
        [run_from(record) for record in stored["runs"]], [PlantSummary(**record) for record in stored["plant_runs"]],
    )


def reevaluation_record(source: Path, stored: dict[str, object]) -> dict[str, object]:
    """Where the re-evaluated runs came from, and the record of the run that produced them."""
    return {
        "reevaluated_from": source.name,
        "run_started_utc": stored["started_utc"],
        "run_finished_utc": stored["finished_utc"],
        "run_provenance": stored["provenance"],
    }


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    options = parse_arguments(arguments)
    if options.reevaluate:
        stored = json.loads(options.reevaluate.read_text())
        report = assemble_report(results_from_report(stored)) | reevaluation_record(options.reevaluate, stored)
    else:
        report = assemble_report(run_study(design_from(options)))
    reporting.publish("species", report, to_markdown(report))
    return 0 if all_pillars_hold(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
