"""Pre-specified tests on fresh seeds: K2 (ketamine's timing faults on feedback connections) and P1c.

The tests, their conditions, the seeds and the pass rule were written into the paper (Appendix C.7)
before this study was first run. Seeds start at BASE_SEED + SEED_OFFSET, which no earlier run used.
A test passes for an organism when it holds in at least PASS_SHARE of that organism's seeds.

Usage:
    ../.venv/bin/python prespecified_study.py            # full study
    ../.venv/bin/python prespecified_study.py --quick    # short smoke run, one seed each

Exit status is non-zero if any test fails for any organism. A failing test is a scientific
result, not a software error: the report is written either way.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from fractions import Fraction
from functools import partial
from typing import Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import provenance
import reporting
import species_study as species

SEED_OFFSET = 2000
PASS_SHARE = Fraction(4, 5)
# Diffusion imaging gives no direction, so the human connectome has no feedback connections to test.
DIRECTED_ORGANISMS = ("celegans", "drosophila")
FULL_SEEDS = {"celegans": 20, "drosophila": 6, "human": 20}


class ConditionName(StrEnum):
    FEEDBACK_FAULTS = "NMDA-antagonist-like on feedback connections, sensory stimulus"
    MATCHED_RANDOM_FAULTS = "NMDA-antagonist-like on as many random connections, sensory stimulus"


def build_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    base = cal.base_sweep_design(integration)
    ketamine_with_stimulus = replace(base, agent=cal.NMDA_ANTAGONIST_AGENT, stimulus=cal.SENSORY_STIMULUS)
    return (
        species.Condition(
            ConditionName.FEEDBACK_FAULTS,
            replace(ketamine_with_stimulus, jitter_scaling=dynamics.JitterScaling.FEEDBACK_CONNECTIONS),
            DIRECTED_ORGANISMS,
        ),
        species.Condition(
            ConditionName.MATCHED_RANDOM_FAULTS,
            replace(ketamine_with_stimulus, jitter_scaling=dynamics.JitterScaling.MATCHED_RANDOM_CONNECTIONS),
            DIRECTED_ORGANISMS,
        ),
        species.Condition(species.ConditionName.GABAERGIC, base, tuple(cal.ORGANISMS)),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def forward_spread_survives(run: species.RunSummary) -> bool:
    """Where quorum is lost, the stimulus still spreads at half its awake broadcast or more; false where it is not lost."""
    if run.unconscious_broadcast_ratio is None or run.awake_broadcast_ratio is None:
        return False
    return run.unconscious_broadcast_ratio >= cal.BROADCAST_COLLAPSE_FRACTION * run.awake_broadcast_ratio


@dataclass(frozen=True)
class FaultPlacementPair:
    """The same organism and seed with the added timing error on feedback and on matched random connections."""

    feedback: species.RunSummary
    matched_random: species.RunSummary


def feedback_faults_act_at_a_lower_concentration(pair: FaultPlacementPair) -> bool:
    feedback_loss, random_loss = pair.feedback.loss_concentration, pair.matched_random.loss_concentration
    if feedback_loss is None:
        return False
    return random_loss is None or comparisons.exceeds(random_loss, feedback_loss)


RUN_TESTS = (
    species.Pillar("K2a", "Timing faults on feedback connections alone abolish quorum", ConditionName.FEEDBACK_FAULTS, species.quorum_is_lost),
    species.Pillar(
        "K2b", "Where they do, the stimulus still spreads (broadcast at least half its awake value)",
        ConditionName.FEEDBACK_FAULTS, forward_spread_survives,
    ),
    species.Pillar(
        "P1c", "Replication of P1b: fluctuations rise at least tenfold on the conscious side of the threshold",
        species.ConditionName.GABAERGIC, species.fluctuations_rise_before_collapse,
    ),
)

PAIRED_TESTS = (
    reporting.Check(
        "K2c", "Control: as many random connections need a higher concentration, or never abolish quorum",
        feedback_faults_act_at_a_lower_concentration,
    ),
)


def fault_placement_pairs(runs: Sequence[species.RunSummary]) -> list[FaultPlacementPair]:
    by_key = {(r.organism, r.condition, r.seed): r for r in runs}
    return [
        FaultPlacementPair(run, by_key[(run.organism, ConditionName.MATCHED_RANDOM_FAULTS, run.seed)])
        for run in runs
        if run.condition == ConditionName.FEEDBACK_FAULTS and (run.organism, ConditionName.MATCHED_RANDOM_FAULTS, run.seed) in by_key
    ]


def evaluate(runs: Sequence[species.RunSummary], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    pairs = fault_placement_pairs(runs)
    groups = {cal.ORGANISMS[o].display_name: [p for p in pairs if p.feedback.organism == o] for o in organisms}
    return species.evaluate(RUN_TESTS, runs, organisms) + reporting.evaluate(PAIRED_TESTS, groups)


def passes(outcome: reporting.CheckOutcome) -> bool:
    return comparisons.at_least_share(outcome.runs_holding, outcome.runs_applicable, PASS_SHARE)


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
    return "\n".join(outcome_table(evaluate(runs, organisms), organisms))


def run_study(design: StudyDesign) -> list[species.RunSummary]:
    tasks = tasks_for(design)
    runs: list[species.RunSummary] = []
    for organism, spec in cal.ORGANISMS.items():
        live = reporting.ParallelRun(f"prespecified: {spec.display_name}", spec.worker_processes, partial(outcomes_markdown, organisms=[organism]))
        runs.extend(reporting.run_in_parallel(species.run_task, [t for t in tasks if t.organism == organism], live))
    return runs


def feedback_shares() -> dict[str, float]:
    """Share of each directed connectome's connections that are feedback, as reported in the paper."""
    return {o: float(species.load_connectome(o).feedback_connections().mean()) for o in DIRECTED_ORGANISMS}


def assemble_report(design: StudyDesign, started: str, runs: Sequence[species.RunSummary]) -> dict[str, object]:
    outcomes = evaluate(runs, list(cal.ORGANISMS))
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
            "pass_share": float(PASS_SHARE),
        },
        "feedback_shares": feedback_shares(),
        "tests": [asdict(o) | {"passes": passes(o)} for o in outcomes],
        "runs": [asdict(run) for run in runs],
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


QUANTITIES: tuple[tuple[str, str, str], ...] = (
    ("Loss concentration", ConditionName.FEEDBACK_FAULTS, "loss_concentration"),
    ("Loss concentration", ConditionName.MATCHED_RANDOM_FAULTS, "loss_concentration"),
    ("Broadcast ratio, awake", ConditionName.FEEDBACK_FAULTS, "awake_broadcast_ratio"),
    ("Broadcast ratio, first unconscious", ConditionName.FEEDBACK_FAULTS, "unconscious_broadcast_ratio"),
    ("Coherence at the highest concentration, relative to awake", ConditionName.FEEDBACK_FAULTS, "deepest_coherence_fraction"),
    ("Coherence at the highest concentration, relative to awake", ConditionName.MATCHED_RANDOM_FAULTS, "deepest_coherence_fraction"),
    ("Loss concentration", species.ConditionName.GABAERGIC, "loss_concentration"),
)


def outcome_cell(outcome: reporting.CheckOutcome) -> str:
    return f"{outcome.cell()}, {'passes' if passes(outcome) else 'fails'}"


def outcome_table(outcomes: Sequence[reporting.CheckOutcome], organisms: Sequence[str]) -> list[str]:
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    rows = []
    for identifier in dict.fromkeys(o.identifier for o in outcomes):
        by_group = {o.group: o for o in outcomes if o.identifier == identifier}
        statement = next(iter(by_group.values())).statement
        rows.append([identifier, statement, *[outcome_cell(by_group[n]) if n in by_group else "not run" for n in names]])
    return reporting.markdown_table(["ID", "Statement", *names], rows)


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in cal.ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "passes"}) for t in report["tests"]]
    shares = [[cal.ORGANISMS[o].display_name, f"{100 * share:.1f}%"] for o, share in report["feedback_shares"].items()]
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"### Pre-specified tests (seeds in which the test holds; passes at {float(100 * PASS_SHARE):.0f}% or more)",
        "",
        *outcome_table(outcomes, organisms),
        "",
        "### Feedback connections (share of all connections)",
        "",
        *reporting.markdown_table(["Organism", "Feedback share"], shares),
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
        return StudyDesign("quick", cal.QUICK_INTEGRATION, {o: 1 for o in cal.ORGANISMS})
    return StudyDesign("full", cal.FULL_INTEGRATION, FULL_SEEDS)


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    started = datetime.now(timezone.utc).isoformat()
    report = assemble_report(design, started, run_study(design))
    reporting.publish("prespecified", report, to_markdown(report))
    return 0 if all(test["passes"] for test in report["tests"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
