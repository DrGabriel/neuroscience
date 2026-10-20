"""The blocks of the DPC readout study, their seeds and their order: every calibration first, then every test."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from typing import Callable, Sequence

import calibration as cal
import connectome_inertia
import disconnection_study
import dpc_simulator as dpc
import phase_dynamics as dynamics
import prespecified_runs
import reporting
import species_study as species
from readout_study import agents, fluctuations, static_baseline, transitions
from readout_study.calibrated_values import Calibrated
from readout_study.conditions import agent_conditions, coupling_calibration_conditions, disconnection_conditions, inertia_scan_conditions
from readout_study.disconnection import evaluate_disconnection
from readout_study.pass_rule import reliable_or_not
from readout_study.phase_inertia import calibrate_feedback, evaluate_inertia_scan, evaluate_validation, validation_conditions
from readout_study.running import ReadoutRun, evaluate_paired, run_readout_task
from readout_study.settings import (
    AGENT_ORGANISMS,
    AGENT_SEEDS,
    CALIBRATION_SEED_OFFSET,
    COUPLING_CALIBRATION_SEED_OFFSET,
    COUPLING_CALIBRATION_SEEDS,
    DISCONNECTION_ORGANISMS,
    INERTIA_ORGANISMS,
    INERTIA_SCAN_SEEDS,
    PERCOLATION_CALIBRATION_SEEDS,
    PERCOLATION_HELD_OUT_SEEDS,
    SEED_OFFSET,
    SMOKE_GRID,
    SMOKE_INTEGRATION,
    SMOKE_ORGANISMS,
    VALIDATION_SEEDS,
)
from readout_study.weaker_coupling import calibrate_coupling, evaluate_metastable, metastable_conditions


class StudyMode(Enum):
    """FULL: the pre-specified study. QUICK: one seed per organism and condition, shortened integration. SMOKE:
    C. elegans only, one seed, the shortest integration and two concentrations, a few minutes in all."""

    FULL = "full"
    QUICK = "quick"
    SMOKE = "smoke"


def evaluate_agents(runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    single = species.evaluate(agents.AGENT_TESTS + static_baseline.STATIC_TESTS + fluctuations.FLUCTUATION_TESTS, runs, organisms)
    paired = evaluate_paired(agents.WIRING_TESTS + transitions.TRANSITION_TESTS, runs, organisms)
    return single + paired + fluctuations.evaluate_size(runs, organisms)


def no_tests(runs: Sequence[object], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    return []


# Every test block reads its runs with the DPC readout and judges them by the same pass rule.
readout_plan = partial(prespecified_runs.StudyPlan, seed_offset=SEED_OFFSET, work=run_readout_task, verdict=reliable_or_not)

AGENT_PLAN = readout_plan(
    name="dpc readout: agents", conditions=agent_conditions, organisms=AGENT_ORGANISMS,
    full_seeds={o: AGENT_SEEDS[o] for o in AGENT_ORGANISMS}, outcomes=evaluate_agents,
)
DISCONNECTION_PLAN = readout_plan(
    name="dpc readout: sensory disconnection", conditions=disconnection_conditions, organisms=DISCONNECTION_ORGANISMS,
    full_seeds=dict(disconnection_study.FULL_SEEDS), outcomes=evaluate_disconnection,
)
INERTIA_SCAN_PLAN = readout_plan(
    name="dpc readout: inertia scan", conditions=inertia_scan_conditions, organisms=INERTIA_ORGANISMS,
    full_seeds=INERTIA_SCAN_SEEDS, outcomes=evaluate_inertia_scan, seed_offset=CALIBRATION_SEED_OFFSET,
)
# The awake-only calibration of the weaker coupling needs global coherence alone, so it runs the reference sweep.
COUPLING_CALIBRATION_PLAN = prespecified_runs.StudyPlan(
    name="dpc readout: coupling calibration", conditions=coupling_calibration_conditions, organisms=AGENT_ORGANISMS,
    seed_offset=COUPLING_CALIBRATION_SEED_OFFSET, full_seeds=COUPLING_CALIBRATION_SEEDS, outcomes=no_tests, verdict=reliable_or_not,
)


def calibrated_plan(name: str, calibrations: Sequence[Calibrated], seeds: dict[str, int]) -> Callable[..., prespecified_runs.StudyPlan]:
    calibrated = {c.organism: seeds[c.organism] for c in calibrations if c.value is not None}
    return partial(readout_plan, name=f"dpc readout: {name}", organisms=tuple(calibrated), full_seeds=calibrated)


def validation_plan(calibrations: Sequence[Calibrated]) -> prespecified_runs.StudyPlan:
    plan = calibrated_plan("held-out validation", calibrations, VALIDATION_SEEDS)
    return plan(conditions=validation_conditions(calibrations), outcomes=evaluate_validation(calibrations))


def metastable_plan(calibrations: Sequence[Calibrated]) -> prespecified_runs.StudyPlan:
    plan = calibrated_plan("weaker coupling", calibrations, AGENT_SEEDS)
    return plan(conditions=metastable_conditions(calibrations), outcomes=evaluate_metastable(calibrations))


# ---------------------------------------------------------------------------
# The smoke mode: the same blocks, cut down to C. elegans, two concentrations and the shortest integration
# ---------------------------------------------------------------------------


def smoke_condition(condition: species.Condition) -> species.Condition:
    """Two concentrations, except for the awake-only conditions, which keep their single one."""
    organisms = tuple(o for o in condition.organisms if o in SMOKE_ORGANISMS)
    grid = condition.design.grid if condition.design.grid.maximum == 0 else SMOKE_GRID
    return replace(condition, design=replace(condition.design, grid=grid), organisms=organisms)


def smoke_plan(plan: prespecified_runs.StudyPlan) -> prespecified_runs.StudyPlan:
    def conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
        return tuple(smoke_condition(c) for c in plan.conditions(integration))
    organisms = tuple(o for o in plan.organisms if o in SMOKE_ORGANISMS)
    return replace(plan, conditions=conditions, organisms=organisms, full_seeds={o: plan.full_seeds[o] for o in organisms})


def study_design(plan: prespecified_runs.StudyPlan, mode: StudyMode) -> prespecified_runs.StudyDesign:
    if mode is StudyMode.SMOKE:
        return prespecified_runs.StudyDesign(reporting.RunLabel.QUICK, SMOKE_INTEGRATION, {o: 1 for o in plan.organisms})
    return prespecified_runs.study_design(plan, mode is StudyMode.QUICK)


# ---------------------------------------------------------------------------
# Running every block
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockResult:
    plan: prespecified_runs.StudyPlan
    design: prespecified_runs.StudyDesign
    runs: list[object]

    def outcomes(self) -> list[reporting.CheckOutcome]:
        return self.plan.outcomes(self.runs, list(self.plan.organisms))


def run_block(plan: prespecified_runs.StudyPlan, mode: StudyMode) -> BlockResult:
    plan = smoke_plan(plan) if mode is StudyMode.SMOKE else plan
    design = study_design(plan, mode)
    runs = prespecified_runs.run_study(plan, design) if plan.organisms else []
    return BlockResult(plan, design, runs)


def percolation_design(mode: StudyMode) -> connectome_inertia.InertiaDesign:
    calibration_first, test_first = cal.BASE_SEED + CALIBRATION_SEED_OFFSET, cal.BASE_SEED + SEED_OFFSET
    if mode is StudyMode.FULL:
        return connectome_inertia.InertiaDesign(
            tuple(range(calibration_first, calibration_first + PERCOLATION_CALIBRATION_SEEDS)),
            tuple(range(test_first, test_first + PERCOLATION_HELD_OUT_SEEDS)),
            connectome_inertia.FULL_FEEDBACK_STEP_MS,
            dpc.REFERENCE_CONCENTRATION_STEP,
        )
    quick = connectome_inertia.InertiaDesign((calibration_first,), (test_first,), connectome_inertia.QUICK_FEEDBACK_STEP_MS, connectome_inertia.QUICK_CONCENTRATION_STEP)
    return replace(quick, organisms=SMOKE_ORGANISMS) if mode is StudyMode.SMOKE else quick


@dataclass(frozen=True)
class Calibrations:
    feedback: tuple[Calibrated, ...]
    coupling: tuple[Calibrated, ...]


@dataclass(frozen=True)
class StudyResults:
    label: str
    started_utc: str
    blocks: tuple[BlockResult, ...]
    calibrations: Calibrations
    percolation: tuple[connectome_inertia.OrganismInertia, ...]


def run_calibrations(mode: StudyMode) -> tuple[BlockResult, BlockResult, Calibrations]:
    scan, coupling = run_block(INERTIA_SCAN_PLAN, mode), run_block(COUPLING_CALIBRATION_PLAN, mode)
    calibrations = Calibrations(
        tuple(calibrate_feedback(scan.runs, o) for o in scan.plan.organisms),
        tuple(calibrate_coupling(coupling.runs, o) for o in coupling.plan.organisms),
    )
    return scan, coupling, calibrations


def run_all(mode: StudyMode) -> StudyResults:
    """Every calibration first, on its own seeds; then every test block."""
    started = datetime.now(timezone.utc).isoformat()
    scan, coupling, calibrations = run_calibrations(mode)
    percolation = tuple(connectome_inertia.run_all(percolation_design(mode)))
    plans = (AGENT_PLAN, DISCONNECTION_PLAN, metastable_plan(calibrations.coupling), validation_plan(calibrations.feedback))
    blocks = (scan, coupling, *(run_block(p, mode) for p in plans))
    return StudyResults(blocks[-1].design.label, started, blocks, calibrations, percolation)
