"""I1, I2: neural inertia in the phase model, scanned beyond the locking threshold, calibrated and validated on
held-out seeds."""

from __future__ import annotations

import statistics
from dataclasses import replace
from typing import Callable, Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_runs
import reporting
import species_study as species
from readout_study.calibrated_values import Calibrated, closest
from readout_study.conditions import feedback_condition, feedback_condition_name, validation_condition_name
from readout_study.running import ReadoutRun, concentration_step, runs_of
from readout_study.settings import HIGHEST_REPRODUCED_INERTIA_RATIO, LOWEST_MEASURED_INERTIA_RATIO, SCANNED_FEEDBACK


def dpc_inertia(run: ReadoutRun) -> bool:
    """I1: DPC quorum returns on emergence more than one concentration step below where it was lost."""
    loss, recovery = run.dpc_loss_concentration, run.dpc_recovery_concentration
    return loss is not None and recovery is not None and comparisons.exceeds(loss - recovery, concentration_step(run.organism))


def inertia_tests() -> tuple[species.Pillar, ...]:
    return tuple(
        species.Pillar(f"I1, λ = {feedback:.3f}", "DPC quorum returns more than one step below its loss (hysteresis)", feedback_condition_name(feedback), dpc_inertia)
        for feedback in SCANNED_FEEDBACK
    )


def evaluate_inertia_scan(runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    return species.evaluate(inertia_tests(), runs, organisms)


def mean_inertia_ratio(runs: Sequence[ReadoutRun]) -> float | None:
    """Mean ratio across seeds; None unless every seed loses quorum and regains it above zero."""
    ratios = [run.inertia_ratio for run in runs]
    return None if not ratios or None in ratios else statistics.fmean(ratios)


def calibrate_feedback(runs: Sequence[ReadoutRun], organism: str) -> Calibrated:
    """Among scanned values at which every calibration seed loses and regains DPC quorum, the one whose mean ratio is
    closest to the reference ratio."""
    ratios = [(f, mean_inertia_ratio(runs_of(runs, organism, feedback_condition_name(f)))) for f in SCANNED_FEEDBACK]
    return closest(organism, [(f, r) for f, r in ratios if r is not None], cal.INERTIA_TARGET_RATIO)


def within_measured_inertia(run: ReadoutRun) -> bool:
    """I2: on a held-out seed, the DPC inertia ratio lies within the measured range the percolation model reproduces."""
    ratio = run.inertia_ratio
    return ratio is not None and comparisons.at_most(LOWEST_MEASURED_INERTIA_RATIO, ratio) and comparisons.at_most(ratio, HIGHEST_REPRODUCED_INERTIA_RATIO)


def validation_conditions(calibrations: Sequence[Calibrated]) -> Callable[[dynamics.IntegrationSettings], tuple[species.Condition, ...]]:
    def conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
        return tuple(
            replace(feedback_condition(c.value, (c.organism,), integration), name=validation_condition_name(c.value))
            for c in calibrations if c.value is not None
        )
    return conditions


def evaluate_validation(calibrations: Sequence[Calibrated]) -> prespecified_runs.Outcomes:
    statement = f"Held-out seeds: the DPC inertia ratio lies within {LOWEST_MEASURED_INERTIA_RATIO}-{HIGHEST_REPRODUCED_INERTIA_RATIO}"
    tests = tuple(species.Pillar("I2", statement, validation_condition_name(c.value), within_measured_inertia) for c in calibrations if c.value is not None)
    return lambda runs, organisms: [o for o in species.evaluate(tests, runs, organisms) if o.runs_applicable > 0]
