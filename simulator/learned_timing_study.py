"""Pre-specified test of P4b: can a learned expectation of arrival times make constant delays harmless?

P4b proposes that the brain integrates inputs against learned expectations of when they arrive, so that a constant
delay is harmless and only variability matters. The models have no such learning, and in them constant offsets are
as harmful as jitter (Section 3.3). Here each connection learns its expected arrival offset
(phase_dynamics.ArrivalExpectation). The tests, conditions, seeds and pass rule were written into the paper
(Appendix C.10) before this study was first run. A test passes for an organism when it holds in at least PASS_SHARE
of that organism's seeds.

Usage:
    ../.venv/bin/python learned_timing_study.py            # full study
    ../.venv/bin/python learned_timing_study.py --quick    # short smoke run, one seed each

Exit status is non-zero if any test fails for any organism. A failing test is a scientific result, not a software
error: the report is written either way.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from functools import partial
from typing import Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_study as prespecified
import provenance
import reporting
import species_study as species

SEED_OFFSET = 3000
# The fly connectome has 2.5 million connections; its runs would take most of a day.
ORGANISMS = ("celegans", "human")
WITH_TRACT_LENGTHS = ("human",)
FULL_SEEDS = {"celegans": 20, "human": 20}
AWAKE_COHERENCE_KEPT = 0.9


class ConditionName(StrEnum):
    FIXED_OFFSETS = "NMDA-antagonist-like, fixed timing offsets"
    FIXED_OFFSETS_LEARNED = "NMDA-antagonist-like, fixed timing offsets, learned arrival times"
    JITTER = "NMDA-antagonist-like"
    JITTER_LEARNED = "NMDA-antagonist-like, learned arrival times"
    GABAERGIC = "GABAergic-like"
    GABAERGIC_LEARNED = "GABAergic-like, learned arrival times"
    DELAYS = "GABAergic-like, conduction delays"
    DELAYS_LEARNED = "GABAergic-like, conduction delays, learned arrival times"


def build_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    base = cal.base_sweep_design(integration)
    learning = replace(cal.POPULATION_DYNAMICS, arrival_learning_time=cal.ARRIVAL_LEARNING_TIME)
    fixed = replace(base, agent=cal.NMDA_ANTAGONIST_AGENT, jitter_dynamics=dynamics.JitterDynamics.FIXED)
    jitter = replace(base, agent=cal.NMDA_ANTAGONIST_AGENT)
    delays = replace(base, conduction_velocity_m_per_s=cal.CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S)
    designs = {
        ConditionName.FIXED_OFFSETS: (fixed, ORGANISMS),
        ConditionName.JITTER: (jitter, ORGANISMS),
        ConditionName.GABAERGIC: (base, ORGANISMS),
        ConditionName.DELAYS: (delays, WITH_TRACT_LENGTHS),
    }
    learned_name = {
        ConditionName.FIXED_OFFSETS: ConditionName.FIXED_OFFSETS_LEARNED,
        ConditionName.JITTER: ConditionName.JITTER_LEARNED,
        ConditionName.GABAERGIC: ConditionName.GABAERGIC_LEARNED,
        ConditionName.DELAYS: ConditionName.DELAYS_LEARNED,
    }
    return tuple(
        condition
        for name, (design, organisms) in designs.items()
        for condition in (
            species.Condition(name, design, organisms),
            species.Condition(learned_name[name], replace(design, dynamics=learning), organisms),
        )
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningPair:
    """The same organism and seed in a condition with learned arrival times and in its comparison condition."""

    learned: species.RunSummary
    comparison: species.RunSummary


def concentration_step(organism: str) -> float:
    return cal.ORGANISMS[organism].concentration_step or cal.CONCENTRATION_GRID.step


def quorum_never_lost(run: species.RunSummary) -> bool:
    return run.loss_concentration is None


def loss_not_delayed_by_more_than_a_step(pair: LearningPair) -> bool:
    """L2: with learning, quorum is still lost, at most one concentration step later than without."""
    learned, comparison = pair.learned.loss_concentration, pair.comparison.loss_concentration
    if learned is None or comparison is None:
        return False
    return comparisons.at_most(learned - comparison, concentration_step(pair.learned.organism))


def loss_not_lowered_by_more_than_a_step(pair: LearningPair) -> bool:
    """L3: with learning, quorum is lost at most one concentration step earlier than without delays."""
    learned, comparison = pair.learned.loss_concentration, pair.comparison.loss_concentration
    if learned is None or comparison is None:
        return False
    return comparisons.at_most(comparison - learned, concentration_step(pair.learned.organism))


def awake_state_and_loss_kept(pair: LearningPair) -> bool:
    """L4: learning keeps at least 90% of the awake coherence and moves the loss by at most one step either way."""
    learned, comparison = pair.learned, pair.comparison
    if learned.loss_concentration is None or comparison.loss_concentration is None:
        return False
    keeps_awake = comparisons.at_most(AWAKE_COHERENCE_KEPT * comparison.induction_coherence[0], learned.induction_coherence[0])
    shift = abs(learned.loss_concentration - comparison.loss_concentration)
    return keeps_awake and comparisons.at_most(shift, concentration_step(learned.organism))


@dataclass(frozen=True)
class PairedTest:
    check: reporting.Check
    learned: str
    comparison: str


RUN_TESTS = (
    species.Pillar("L1", "With learned arrival times, fixed timing offsets never abolish quorum", ConditionName.FIXED_OFFSETS_LEARNED, quorum_never_lost),
)

PAIRED_TESTS = (
    PairedTest(
        reporting.Check("L2", "With learned arrival times, timing jitter of the same size still abolishes quorum, at most one step later", loss_not_delayed_by_more_than_a_step),
        ConditionName.JITTER_LEARNED, ConditionName.JITTER,
    ),
    PairedTest(
        reporting.Check("L3", "With learned arrival times, conduction delays no longer lower the loss concentration by more than one step", loss_not_lowered_by_more_than_a_step),
        ConditionName.DELAYS_LEARNED, ConditionName.GABAERGIC,
    ),
    PairedTest(
        reporting.Check("L4", "Learning keeps the awake state (at least 90% of its coherence) and moves the GABAergic-like loss by at most one step", awake_state_and_loss_kept),
        ConditionName.GABAERGIC_LEARNED, ConditionName.GABAERGIC,
    ),
)


def pairs_for(test: PairedTest, runs: Sequence[species.RunSummary]) -> list[LearningPair]:
    by_key = {(r.organism, r.condition, r.seed): r for r in runs}
    return [
        LearningPair(run, by_key[(run.organism, test.comparison, run.seed)])
        for run in runs
        if run.condition == test.learned and (run.organism, test.comparison, run.seed) in by_key
    ]


def evaluate(runs: Sequence[species.RunSummary], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    outcomes = species.evaluate(RUN_TESTS, runs, organisms)
    for test in PAIRED_TESTS:
        pairs = pairs_for(test, runs)
        groups = {cal.ORGANISMS[o].display_name: [p for p in pairs if p.learned.organism == o] for o in organisms}
        outcomes += [o for o in reporting.evaluate((test.check,), groups) if o.runs_applicable > 0]
    return outcomes


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StudyDesign:
    label: str
    integration: dynamics.IntegrationSettings
    seeds_per_organism: dict[str, int]


def tasks_for(design: StudyDesign) -> list[species.RunTask]:
    return [
        species.RunTask(organism, condition, cal.BASE_SEED + SEED_OFFSET + index)
        for condition in build_conditions(design.integration)
        for organism in condition.organisms
        for index in range(design.seeds_per_organism[organism])
    ]


def outcomes_markdown(runs: list[species.RunSummary], organisms: Sequence[str]) -> str:
    return "\n".join(prespecified.outcome_table(evaluate(runs, organisms), organisms))


def run_study(design: StudyDesign) -> list[species.RunSummary]:
    tasks = tasks_for(design)
    runs: list[species.RunSummary] = []
    for organism in ORGANISMS:
        spec = cal.ORGANISMS[organism]
        live = reporting.ParallelRun(f"learned timing: {spec.display_name}", spec.worker_processes, partial(outcomes_markdown, organisms=[organism]))
        runs.extend(reporting.run_in_parallel(species.run_task, [t for t in tasks if t.organism == organism], live))
    return runs


def assemble_report(design: StudyDesign, started: str, runs: Sequence[species.RunSummary]) -> dict[str, object]:
    outcomes = evaluate(runs, ORGANISMS)
    return {
        "label": design.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "design": {
            "integration": asdict(design.integration),
            "seeds_per_organism": design.seeds_per_organism,
            "first_seed": cal.BASE_SEED + SEED_OFFSET,
            "pass_share": float(prespecified.PASS_SHARE),
            "arrival_learning_time": cal.ARRIVAL_LEARNING_TIME,
        },
        "tests": [asdict(o) | {"passes": prespecified.passes(o)} for o in outcomes],
        "runs": [asdict(run) for run in runs],
    }


QUANTITIES: tuple[tuple[str, str, str], ...] = tuple(
    ("Loss concentration", name, "loss_concentration") for name in ConditionName
)


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "passes"}) for t in report["tests"]]
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"### Pre-specified tests of learned arrival times (seeds in which the test holds; passes at {float(100 * prespecified.PASS_SHARE):.0f}% or more)",
        "",
        *prespecified.outcome_table(outcomes, organisms),
        "",
        "### Measurements (mean ± SD across seeds; concentrations relative to EC50)",
        "",
        *reporting.markdown_table(["Quantity", "Condition", *names], species.measurement_rows_for(QUANTITIES, report["runs"], organisms)),
        "",
    ])


def parse_design(arguments: Sequence[str]) -> StudyDesign:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="short smoke run instead of the full study")
    if parser.parse_args(arguments).quick:
        return StudyDesign("quick", cal.QUICK_INTEGRATION, {o: 1 for o in ORGANISMS})
    return StudyDesign("full", cal.FULL_INTEGRATION, FULL_SEEDS)


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    started = datetime.now(timezone.utc).isoformat()
    report = assemble_report(design, started, run_study(design))
    reporting.publish("learned_timing", report, to_markdown(report))
    return 0 if all(test["passes"] for test in report["tests"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
