"""Pre-specified test of the congestion account of induction-phase excitation (Section 5.1).

For each compensation mode and global coupling, every seed is run twice, at low and at high
sensory load, so that the effect of load is compared within the same network realisation.

Pre-specified (set before the study was run, from the design in excitatory_inhibitory.py):
    W1-W3  hub excitatory activity rises at least 10% above its awake value before collapse,
           without compensation (W1), with slow compensation (W2), with fast compensation (W3);
    W4     that rise is larger at high than at low sensory load.
Post hoc (noticed in an exploratory probe of single runs, reported as secondary):
    X1     global synchrony surges to at least 1.5 times its awake value before collapse;
    X2     that surge is larger at high than at low sensory load.

Confirmatory mode (--confirm) tests X1 and X2 as pre-specified hypotheses on seeds that no
exploratory run has used, with the thresholds above fixed before those seeds were run.

Usage: ../.venv/bin/python congestion_study.py [--quick | --confirm]
Exit status is non-zero if any pre-specified test fails in any run.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Sequence

import calibration as cal
import connectomes
import dpc_simulator as dpc
import excitatory_inhibitory as ei
import provenance
import reporting

REPORTED_PACKAGES = ("numpy", "scipy")

ORGANISM = "human"
# Free: the strength of long-range coupling is not reported in the text of Abeysuriya et al.
# (2018); results are reported across a range in which the awake network synchronises.
GLOBAL_COUPLINGS = (0.5, 1.0, 2.0)
# Free: extra input to the stimulated sensory regions, about a third of the constant input.
LOW_SENSORY_LOAD = 0.0
HIGH_SENSORY_LOAD = 0.1
# Collapse: global synchrony below half its awake value, as for quorum in the other studies.
COLLAPSE_FRACTION = cal.QUORUM_FRACTION
# Pre-specified: congestion means a rise of at least 10% in hub activity before collapse.
MINIMUM_ACTIVITY_RISE = 1.10
# Post hoc: a synchrony surge means at least 1.5 times the awake synchrony before collapse.
POST_HOC_MINIMUM_SYNCHRONY_SURGE = 1.5
# Pre-specified (P8, graceful degradation): batching means burstiness rises to at least 1.5 times
# its awake value at or beyond the surge, the same factor as for synchrony.
MINIMUM_BURSTINESS_RISE = 1.5
FULL_SEEDS = 10
QUICK_SEEDS = 1
# Worker processes; None uses every core. Set lower when another study shares the machine.
CONGESTION_WORKERS: int | None = None
# Confirmatory seeds start far from every exploratory seed (which start at the base seed).
CONFIRMATORY_SEED_OFFSET = 1000

FULL_DESIGN = ei.CongestionDesign(
    agent=cal.GABAERGIC_AGENT,
    circuit=ei.LocalCircuit(),
    compensation=ei.Compensation.NONE,
    global_coupling=GLOBAL_COUPLINGS[0],
    sensory_extra_input=LOW_SENSORY_LOAD,
    conduction_velocity_m_per_s=cal.CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S,
    grid=dpc.ConcentrationGrid(maximum=3.0, step=0.125),
    # Numerical: a quarter of a millisecond is 1/40 of the excitatory time constant.
    time_step_s=0.00025,
    balancing_s=4.0,
    hold_s=2.0,
    seed=cal.BASE_SEED,
)
QUICK_DESIGN = replace(FULL_DESIGN, grid=dpc.ConcentrationGrid(maximum=3.0, step=0.5), time_step_s=0.0005, hold_s=1.0, balancing_s=2.0)


@dataclass(frozen=True)
class PairedTask:
    design: ei.CongestionDesign


@dataclass(frozen=True)
class PairedRun:
    compensation: str
    global_coupling: float
    seed: int
    low_load_activity_ratio: float
    high_load_activity_ratio: float
    low_load_synchrony_surge: float
    high_load_synchrony_surge: float
    low_load_collapse: float | None
    high_load_collapse: float | None
    low_load_burstiness_rise: float
    low_load_burst_gaps_lengthen: bool | None
    concentrations: tuple[float, ...]
    low_load_burstiness: tuple[float, ...]
    low_load_hub_activity: tuple[float, ...]
    high_load_hub_activity: tuple[float, ...]
    low_load_synchrony: tuple[float, ...]
    high_load_synchrony: tuple[float, ...]


@lru_cache(maxsize=None)
def human_connectome() -> connectomes.Connectome:
    return connectomes.LOADERS[ORGANISM](cal.CONNECTOME_SEED)


def run_pair(task: PairedTask) -> PairedRun:
    low = ei.run_induction(human_connectome(), replace(task.design, sensory_extra_input=LOW_SENSORY_LOAD), COLLAPSE_FRACTION)
    high = ei.run_induction(human_connectome(), replace(task.design, sensory_extra_input=HIGH_SENSORY_LOAD), COLLAPSE_FRACTION)
    return PairedRun(
        compensation=task.design.compensation.value,
        global_coupling=task.design.global_coupling,
        seed=task.design.seed,
        low_load_activity_ratio=low.peak_hub_activity_ratio,
        high_load_activity_ratio=high.peak_hub_activity_ratio,
        low_load_synchrony_surge=low.synchrony_surge,
        high_load_synchrony_surge=high.synchrony_surge,
        low_load_collapse=low.collapse_concentration,
        high_load_collapse=high.collapse_concentration,
        low_load_burstiness_rise=low.burstiness_rise_after_surge,
        low_load_burst_gaps_lengthen=low.burst_gaps_lengthen,
        concentrations=tuple(m.concentration for m in low.measurements),
        low_load_burstiness=tuple(m.burstiness for m in low.measurements),
        low_load_hub_activity=tuple(m.hub_activity for m in low.measurements),
        high_load_hub_activity=tuple(m.hub_activity for m in high.measurements),
        low_load_synchrony=tuple(m.synchrony for m in low.measurements),
        high_load_synchrony=tuple(m.synchrony for m in high.measurements),
    )


def activity_rises(run: PairedRun) -> bool:
    return run.low_load_activity_ratio >= MINIMUM_ACTIVITY_RISE


def rise_grows_with_load(run: PairedRun) -> bool:
    return run.high_load_activity_ratio > run.low_load_activity_ratio and run.high_load_activity_ratio >= MINIMUM_ACTIVITY_RISE


def synchrony_surges(run: PairedRun) -> bool:
    return run.low_load_synchrony_surge >= POST_HOC_MINIMUM_SYNCHRONY_SURGE


def surge_grows_with_load(run: PairedRun) -> bool:
    return run.high_load_synchrony_surge > run.low_load_synchrony_surge


PRE_SPECIFIED = {
    ei.Compensation.NONE: reporting.Check("W1", f"Hub activity rises ≥{MINIMUM_ACTIVITY_RISE - 1:.0%} before collapse, no compensation", activity_rises),
    ei.Compensation.SLOW: reporting.Check("W2", f"Hub activity rises ≥{MINIMUM_ACTIVITY_RISE - 1:.0%} before collapse, slow compensation", activity_rises),
    ei.Compensation.FAST: reporting.Check("W3", f"Hub activity rises ≥{MINIMUM_ACTIVITY_RISE - 1:.0%} before collapse, fast compensation", activity_rises),
}
LOAD_TEST = reporting.Check("W4", f"The rise is larger at high sensory load (and reaches {MINIMUM_ACTIVITY_RISE - 1:.0%})", rise_grows_with_load)
POST_HOC = (
    reporting.Check("X1", f"Post hoc: synchrony surges to ≥{POST_HOC_MINIMUM_SYNCHRONY_SURGE:g} times awake before collapse", synchrony_surges),
    reporting.Check("X2", "Post hoc: the synchrony surge is larger at high sensory load", surge_grows_with_load),
)


DEGRADATION_TESTS = (
    reporting.Check(
        "G1",
        f"Batching: burstiness rises to ≥{MINIMUM_BURSTINESS_RISE:g} times awake at or beyond the synchrony surge",
        lambda run: run.low_load_burstiness_rise >= MINIMUM_BURSTINESS_RISE,
    ),
    reporting.Check(
        "G2",
        "Backoff: bursts are further apart at the deepest step that has them than at the surge",
        lambda run: run.low_load_burst_gaps_lengthen,
    ),
)

CONFIRMATORY = tuple(
    reporting.Check(check.identifier, check.statement.removeprefix("Post hoc: "), check.holds_for) for check in POST_HOC
)


class AnalysisMode(Enum):
    """Exploratory runs test congestion (W1-W4); confirmatory runs test the synchrony surge (X1, X2)."""

    EXPLORATORY = "full"
    CONFIRMATORY = "confirmatory"


@dataclass(frozen=True)
class CongestionAnalysis:
    mode: AnalysisMode
    group_names: list[str]
    primary: list[reporting.CheckOutcome]
    secondary: list[reporting.CheckOutcome]
    degradation: list[reporting.CheckOutcome]


def group_name(compensation: str, coupling: float) -> str:
    return f"{compensation}, C={coupling:g}"


def analyse(runs: Sequence[PairedRun], mode: AnalysisMode) -> CongestionAnalysis:
    """In confirmatory mode the synchrony tests are primary and the activity tests secondary."""
    confirmatory = mode is AnalysisMode.CONFIRMATORY
    analysis = CongestionAnalysis(mode, [], [], [], [])
    for compensation in ei.Compensation:
        for coupling in GLOBAL_COUPLINGS:
            name = group_name(compensation.value, coupling)
            group = {name: [r for r in runs if r.compensation == compensation.value and r.global_coupling == coupling]}
            analysis.group_names.append(name)
            activity_tests = reporting.evaluate([PRE_SPECIFIED[compensation], LOAD_TEST], group)
            synchrony_tests = reporting.evaluate(CONFIRMATORY if confirmatory else POST_HOC, group)
            analysis.primary.extend(synchrony_tests if confirmatory else activity_tests)
            analysis.secondary.extend(activity_tests if confirmatory else synchrony_tests)
            analysis.degradation.extend(reporting.evaluate(DEGRADATION_TESTS, group))
    return analysis


def measurement_rows(runs: Sequence[PairedRun], group_names: Sequence[str]) -> list[list[str]]:
    rows = []
    for name in group_names:
        group = [r for r in runs if group_name(r.compensation, r.global_coupling) == name]
        rows.append([
            name,
            reporting.describe([r.low_load_activity_ratio for r in group]),
            reporting.describe([r.high_load_activity_ratio for r in group]),
            reporting.describe([r.low_load_synchrony_surge for r in group]),
            reporting.describe([r.high_load_synchrony_surge for r in group]),
            reporting.describe([r.low_load_collapse for r in group]),
        ])
    return rows


def to_markdown(document: dict[str, object], runs: Sequence[PairedRun], analysis: CongestionAnalysis) -> str:
    confirmatory = analysis.mode is AnalysisMode.CONFIRMATORY
    return "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"### {'Confirmatory' if confirmatory else 'Pre-specified'} tests (runs in which the test passes)",
        "",
        *reporting.outcome_table(analysis.primary, analysis.group_names),
        "",
        f"### {'Activity tests (secondary in this mode)' if confirmatory else 'Post hoc analyses (not part of the verdict)'}",
        "",
        *reporting.outcome_table(analysis.secondary, analysis.group_names),
        "",
        "### Graceful degradation, P8 (pre-specified; reported separately from the verdict)",
        "",
        *reporting.outcome_table(analysis.degradation, analysis.group_names),
        "",
        "### Measurements (mean ± SD across seeds)",
        "",
        *reporting.markdown_table(
            ["Condition", "Peak hub activity / awake, low load", "Same, high load", "Synchrony surge, low load", "Same, high load", "Collapse concentration"],
            measurement_rows(runs, analysis.group_names),
        ),
        "",
    ])


def paired_tasks(design: ei.CongestionDesign, seeds: int, seed_offset: int) -> list[PairedTask]:
    return [
        PairedTask(replace(design, compensation=compensation, global_coupling=coupling, seed=cal.BASE_SEED + seed_offset + index))
        for compensation in ei.Compensation
        for coupling in GLOBAL_COUPLINGS
        for index in range(seeds)
    ]


def main(arguments: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--quick", action="store_true", help="short smoke run")
    choice.add_argument("--confirm", action="store_true", help="confirmatory test of the synchrony surge on fresh seeds")
    options = parser.parse_args(arguments)
    mode = AnalysisMode.CONFIRMATORY if options.confirm else AnalysisMode.EXPLORATORY
    design, seeds = (QUICK_DESIGN, QUICK_SEEDS) if options.quick else (FULL_DESIGN, FULL_SEEDS)
    seed_offset = CONFIRMATORY_SEED_OFFSET if options.confirm else 0
    started = datetime.now(timezone.utc)
    live = reporting.ParallelRun(f"congestion: {mode.value}", CONGESTION_WORKERS)
    runs = reporting.run_in_parallel(run_pair, paired_tasks(design, seeds, seed_offset), live)
    analysis = analyse(runs, mode)
    document = {
        "label": "quick" if options.quick else mode.value,
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES),
        "design": asdict(design)
        | {"global_couplings": GLOBAL_COUPLINGS, "seeds": seeds, "seed_offset": seed_offset, "loads": (LOW_SENSORY_LOAD, HIGH_SENSORY_LOAD)},
        "primary_tests": [asdict(o) | {"holds": o.holds} for o in analysis.primary],
        "secondary_tests": [asdict(o) for o in analysis.secondary],
        "degradation_tests": [asdict(o) for o in analysis.degradation],
        "runs": [asdict(run) for run in runs],
    }
    reporting.publish("congestion", document, to_markdown(document, runs, analysis))
    return 0 if all(outcome.holds for outcome in analysis.primary) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
