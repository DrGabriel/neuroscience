"""What every pre-specified study shares: fresh seeds, the pass rule, the run loop and the outcome table.

A pre-specified study's tests, conditions, seeds and pass rule are written into the paper before it runs. Each
study supplies a StudyPlan; this module turns it into tasks, runs them and reports the verdicts.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import partial

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import reporting
import species_study as species

# A test passes for an organism when it holds in at least this share of that organism's seeds.
PASS_SHARE = Fraction(4, 5)

Outcomes = Callable[[Sequence[species.RunSummary], Sequence[str]], list[reporting.CheckOutcome]]


@dataclass(frozen=True)
class StudyPlan:
    """One pre-specified study: its name, conditions, organisms, fresh seeds and tests."""

    name: str
    conditions: Callable[[dynamics.IntegrationSettings], tuple[species.Condition, ...]]
    organisms: tuple[str, ...]
    seed_offset: int
    full_seeds: dict[str, int]
    outcomes: Outcomes


@dataclass(frozen=True)
class StudyDesign:
    label: str
    integration: dynamics.IntegrationSettings
    seeds_per_organism: dict[str, int]


def first_seed(plan: StudyPlan) -> int:
    return cal.BASE_SEED + plan.seed_offset


def passes(outcome: reporting.CheckOutcome) -> bool:
    return comparisons.at_least_share(outcome.runs_holding, outcome.runs_applicable, PASS_SHARE)


def tasks_for(plan: StudyPlan, design: StudyDesign) -> list[species.RunTask]:
    return [
        species.RunTask(organism, condition, first_seed(plan) + index)
        for condition in plan.conditions(design.integration)
        for organism in condition.organisms
        for index in range(design.seeds_per_organism[organism])
    ]


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


def outcomes_markdown(runs: list[species.RunSummary], plan: StudyPlan, organism: str) -> str:
    return "\n".join(outcome_table(plan.outcomes(runs, [organism]), [organism]))


def run_study(plan: StudyPlan, design: StudyDesign) -> list[species.RunSummary]:
    """Runs each organism in turn, writing its interim verdicts to results/live/ as seeds complete."""
    tasks = tasks_for(plan, design)
    runs: list[species.RunSummary] = []
    for organism in plan.organisms:
        spec = cal.ORGANISMS[organism]
        live = reporting.ParallelRun(f"{plan.name}: {spec.display_name}", spec.worker_processes, partial(outcomes_markdown, plan=plan, organism=organism))
        runs.extend(reporting.run_in_parallel(species.run_task, [t for t in tasks if t.organism == organism], live))
    return runs


def parse_design(plan: StudyPlan, arguments: Sequence[str], description: str) -> StudyDesign:
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="short smoke run instead of the full study")
    if parser.parse_args(arguments).quick:
        return StudyDesign(reporting.RunLabel.QUICK, cal.QUICK_INTEGRATION, {o: 1 for o in plan.organisms})
    return StudyDesign(reporting.RunLabel.FULL, cal.FULL_INTEGRATION, plan.full_seeds)


def design_record(plan: StudyPlan, design: StudyDesign) -> dict[str, object]:
    return {
        "integration": asdict(design.integration),
        "seeds_per_organism": design.seeds_per_organism,
        "first_seed": first_seed(plan),
        "pass_share": float(PASS_SHARE),
    }
