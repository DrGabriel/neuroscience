"""Neural inertia of the percolation model on the three connectome graphs, calibrated and tested on disjoint seeds.

The percolation model's reference feedback λ was calibrated (calibrate_feedback.py) and its inertia tested
(validation_study.py, C2 and C3) only on random graphs of mean degree 8. Here the same model, with every reference
parameter unchanged, runs on the undirected graphs of the C. elegans, Drosophila and human connectomes
(percolation_thresholds.undirected_graph). For each seed, λ is scanned on a fine grid; on the calibration seeds the λ
whose mean loss-to-recovery ratio is closest to each published ratio is chosen, among the values at which every
calibration seed loses quorum and regains it; the chosen values are then tested on held-out seeds.

Dependencies: numpy and scipy (through the connectome loaders); the model itself is dpc_simulator.py.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Sequence

import calibrate_feedback
import calibration as cal
import comparisons
import dpc_simulator as dpc
import percolation_thresholds
import reporting
import species_study as species

ORGANISMS = ("celegans", "human", "drosophila")
HIGHEST_FEEDBACK_MS = calibrate_feedback.HIGHEST_FEEDBACK_MS
FULL_FEEDBACK_STEP_MS = 0.1
QUICK_FEEDBACK_STEP_MS = 1.0
QUICK_CONCENTRATION_STEP = 0.05
RATIO_TOLERANCE = calibrate_feedback.RATIO_TOLERANCE
# Measured ratios the percolation model reproduces on random graphs: 1.07 (Warnaby et al., 2017) to 1.63 (Sepulveda et
# al., 2018). Halothane's 2.85 is reproduced on no graph tried (Section 10, item 2) and is left out.
HIGHEST_REPRODUCED_RATIO = 1.63
TARGETS = tuple(t for t in calibrate_feedback.PUBLISHED_TARGETS if t.ratio <= HIGHEST_REPRODUCED_RATIO)
LOWEST_MEASURED_RATIO = min(t.ratio for t in TARGETS)
REFERENCE_TARGET_RATIO = dpc.REFERENCE_INERTIA_RATIO
NO_FEEDBACK_MS = 0.0
# Grid values are rounded to this many decimal places, so that 0.1 times 3 is stored as 0.3 and matches on lookup.
GRID_DECIMALS = 10


@lru_cache(maxsize=1)
def connectome_graph(organism: str) -> dpc.Graph:
    return percolation_thresholds.undirected_graph(species.load_connectome(organism))


@dataclass(frozen=True)
class ConnectomeGraphBuilder:
    """The fixed undirected graph of one connectome; building it draws nothing, so each seed varies only the
    percolation draws."""

    organism: str

    @property
    def node_count(self) -> int:
        return connectome_graph(self.organism).node_count

    def build(self, rng: random.Random) -> dpc.Graph:
        return connectome_graph(self.organism)

    def resized(self, node_count: int) -> ConnectomeGraphBuilder:
        raise ValueError("a connectome graph has a fixed size")

    def with_mean_degree(self, mean_degree: float) -> ConnectomeGraphBuilder:
        raise ValueError("a connectome graph has a fixed degree distribution")


@dataclass(frozen=True)
class InertiaTask:
    organism: str
    seed: int
    feedback_ms: tuple[float, ...]
    concentration_step: float


@dataclass(frozen=True)
class InertiaProfile:
    """Loss and recovery concentrations of one seed at each feedback strength."""

    organism: str
    seed: int
    feedback_ms: tuple[float, ...]
    loss: tuple[float | None, ...]
    recovery: tuple[float | None, ...]

    def at(self, feedback_ms: float) -> tuple[float | None, float | None]:
        index = self.feedback_ms.index(feedback_ms)
        return self.loss[index], self.recovery[index]

    def ratio(self, feedback_ms: float) -> float | None:
        loss, recovery = self.at(feedback_ms)
        return None if loss is None or not recovery else loss / recovery


def scenario_for(task: InertiaTask, feedback_ms: float) -> dpc.Scenario:
    base = dpc.REFERENCE_SCENARIO
    return replace(
        base,
        graph_builder=ConnectomeGraphBuilder(task.organism),
        timing=replace(base.timing, feedback_jitter_ms=feedback_ms),
        grid=replace(base.grid, step=task.concentration_step),
        seed=task.seed,
    )


def run_inertia_task(task: InertiaTask) -> InertiaProfile:
    results = [dpc.run_scenario(scenario_for(task, feedback)) for feedback in task.feedback_ms]
    return InertiaProfile(
        task.organism, task.seed, task.feedback_ms, tuple(r.loss_concentration for r in results), tuple(r.recovery_concentration for r in results)
    )


def feedback_grid(step_ms: float) -> tuple[float, ...]:
    return tuple(round(index * step_ms, GRID_DECIMALS) for index in range(round(HIGHEST_FEEDBACK_MS / step_ms) + 1))


# ---------------------------------------------------------------------------
# Calibration on the calibration seeds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectomeCalibration:
    organism: str
    target_ratio: float
    feedback_ms: float | None
    mean_ratio: float | None

    @property
    def reproduced(self) -> bool:
        return self.mean_ratio is not None and abs(self.mean_ratio - self.target_ratio) <= RATIO_TOLERANCE


def mean_ratio(profiles: Sequence[InertiaProfile], feedback_ms: float) -> float | None:
    """Mean ratio across seeds; None unless every seed loses quorum and regains it above zero."""
    ratios = [profile.ratio(feedback_ms) for profile in profiles]
    return None if not ratios or None in ratios else statistics.fmean(ratios)


def calibrate(profiles: Sequence[InertiaProfile], target_ratio: float) -> ConnectomeCalibration:
    organism = profiles[0].organism
    candidates = [(f, ratio) for f in profiles[0].feedback_ms if (ratio := mean_ratio(profiles, f)) is not None]
    if not candidates:
        return ConnectomeCalibration(organism, target_ratio, None, None)
    feedback, ratio = min(candidates, key=lambda candidate: abs(candidate[1] - target_ratio))
    return ConnectomeCalibration(organism, target_ratio, feedback, ratio)


def calibrated_series(calibrations: Sequence[ConnectomeCalibration]) -> tuple[float, ...]:
    """No feedback, then each reproduced target's λ in order of the targets: the series of test PI2 (C3's form)."""
    reproduced = [c.feedback_ms for c in sorted(calibrations, key=lambda c: c.target_ratio) if c.reproduced]
    return (NO_FEEDBACK_MS, *reproduced)


def reference_feedback(calibrations: Sequence[ConnectomeCalibration]) -> float | None:
    reference = next(c for c in calibrations if c.target_ratio == REFERENCE_TARGET_RATIO)
    return reference.feedback_ms if reference.reproduced else None


# ---------------------------------------------------------------------------
# Tests on the held-out seeds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeldOutSeed:
    """One held-out seed's profile over the calibrated series, with the organism's reference-target λ."""

    profile: InertiaProfile
    reference_feedback_ms: float | None


def inertia_width(profile: InertiaProfile, feedback_ms: float) -> float | None:
    """Hysteresis width; never recovering counts as unbounded inertia, as in validation_study (C3)."""
    loss, recovery = profile.at(feedback_ms)
    if loss is None:
        return None
    return math.inf if recovery is None else loss - recovery


def inertia_at_reference(seed: HeldOutSeed) -> bool | None:
    """PI1: at the reference λ, quorum is lost and regained at a strictly lower concentration."""
    if seed.reference_feedback_ms is None:
        return None
    loss, recovery = seed.profile.at(seed.reference_feedback_ms)
    return loss is not None and recovery is not None and comparisons.exceeds(loss, recovery)


def inertia_grows_with_feedback(seed: HeldOutSeed) -> bool | None:
    """PI2 (C3's form): hysteresis never shrinks along the calibrated series and is larger at its end than without
    feedback; undefined when no target was reproduced."""
    series = seed.profile.feedback_ms
    if len(series) < 2:
        return None
    widths = [inertia_width(seed.profile, f) for f in series]
    if None in widths:
        return False
    never_shrinks = all(comparisons.at_most(a, b) for a, b in zip(widths, widths[1:]))
    return never_shrinks and comparisons.exceeds(widths[-1], widths[0])


def no_inertia_without_feedback(seed: HeldOutSeed) -> bool:
    """PI3 (C2's form, a consistency check): without feedback the hysteresis is exactly zero."""
    width = inertia_width(seed.profile, NO_FEEDBACK_MS)
    return width is not None and comparisons.equals(width, 0)


def measured_inertia_reproduced(seed: HeldOutSeed) -> bool | None:
    """PI4: at the reference λ, the seed's ratio lies within the measured range 1.07 to 1.63."""
    if seed.reference_feedback_ms is None:
        return None
    ratio = seed.profile.ratio(seed.reference_feedback_ms)
    return ratio is not None and comparisons.at_most(LOWEST_MEASURED_RATIO, ratio) and comparisons.at_most(ratio, HIGHEST_REPRODUCED_RATIO)


HELD_OUT_TESTS = (
    reporting.Check("PI1", f"Percolation model on the connectome, λ calibrated to {REFERENCE_TARGET_RATIO}: quorum returns below its loss", inertia_at_reference),
    reporting.Check("PI2", "Percolation model on the connectome: hysteresis grows with the calibrated λ (C3's form)", inertia_grows_with_feedback),
    reporting.Check("PI3", "Percolation model on the connectome: no hysteresis without feedback (C2's form)", no_inertia_without_feedback, reporting.CONSISTENCY_CHECK),
    reporting.Check("PI4", f"Percolation model on the connectome: held-out ratio within {LOWEST_MEASURED_RATIO}-{HIGHEST_REPRODUCED_RATIO}", measured_inertia_reproduced),
)


def evaluate(held_out: Sequence[HeldOutSeed]) -> list[reporting.CheckOutcome]:
    groups = {cal.ORGANISMS[o].display_name: [s for s in held_out if s.profile.organism == o] for o in ORGANISMS}
    return [o for o in reporting.evaluate(HELD_OUT_TESTS, groups) if o.runs_applicable > 0]


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InertiaDesign:
    calibration_seeds: tuple[int, ...]
    held_out_seeds: tuple[int, ...]
    feedback_step_ms: float
    concentration_step: float
    organisms: tuple[str, ...] = ORGANISMS


@dataclass(frozen=True)
class OrganismInertia:
    organism: str
    calibrations: tuple[ConnectomeCalibration, ...]
    held_out: tuple[HeldOutSeed, ...]


def run_tasks(organism: str, tasks: list[InertiaTask], label: str) -> list[InertiaProfile]:
    workers = cal.ORGANISMS[organism].worker_processes
    return reporting.run_in_parallel(run_inertia_task, tasks, reporting.ParallelRun(f"{label}: {cal.ORGANISMS[organism].display_name}", workers))


def run_organism(organism: str, design: InertiaDesign) -> OrganismInertia:
    grid = feedback_grid(design.feedback_step_ms)
    scan = run_tasks(organism, [InertiaTask(organism, s, grid, design.concentration_step) for s in design.calibration_seeds], "connectome inertia calibration")
    calibrations = tuple(calibrate(scan, target.ratio) for target in TARGETS)
    series = calibrated_series(calibrations)
    tests = run_tasks(organism, [InertiaTask(organism, s, series, design.concentration_step) for s in design.held_out_seeds], "connectome inertia held-out")
    reference = reference_feedback(calibrations)
    return OrganismInertia(organism, calibrations, tuple(HeldOutSeed(profile, reference) for profile in tests))


def run_all(design: InertiaDesign) -> list[OrganismInertia]:
    return [run_organism(organism, design) for organism in design.organisms]
