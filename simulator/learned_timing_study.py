"""Pre-specified test of P4b: can a learned expectation of arrival times make constant delays harmless?

P4b proposes that the brain integrates inputs against learned expectations of when they arrive, so that a constant
delay is harmless and only variability matters. The models have no such learning, and in them constant offsets are
as harmful as jitter (Section 3.3). Here each connection learns its expected arrival offset
(phase_dynamics.ArrivalExpectation). The tests, conditions, seeds and pass rule were written into the paper
(Appendix C.10) before this study was first run; the pass rule is prespecified_runs.PASS_SHARE.

Usage:
    ../.venv/bin/python learned_timing_study.py            # full study
    ../.venv/bin/python learned_timing_study.py --quick    # short smoke run, one seed each

Exit status is non-zero if any test fails for any organism. A failing test is a scientific result, not a software
error: the report is written either way.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_runs
import provenance
import reporting
import species_study as species

SEED_OFFSET = 3000
# The fly connectome has 2.7 million directed connections; its runs would take most of a day.
ORGANISMS = ("celegans", "human")
WITH_TRACT_LENGTHS = ("human",)
FULL_SEEDS = {"celegans": 20, "human": 20}
AWAKE_COHERENCE_KEPT = 0.9
LEARNED_SUFFIX = ", learned arrival times"

Baseline = species.ConditionName


def learned(name: str) -> str:
    """The name of a condition run with learned arrival times."""
    return f"{name}{LEARNED_SUFFIX}"


def baseline_designs(integration: dynamics.IntegrationSettings) -> dict[str, tuple[dynamics.SweepDesign, tuple[str, ...]]]:
    """The species-study conditions this study repeats with learning, with the organisms each is run on."""
    base = cal.base_sweep_design(integration)
    return {
        Baseline.NMDA_FIXED_OFFSETS: (replace(base, agent=cal.NMDA_ANTAGONIST_AGENT, jitter_dynamics=dynamics.JitterDynamics.FIXED), ORGANISMS),
        Baseline.NMDA_ANTAGONIST: (replace(base, agent=cal.NMDA_ANTAGONIST_AGENT), ORGANISMS),
        Baseline.GABAERGIC: (base, ORGANISMS),
        Baseline.CONDUCTION_DELAYS: (replace(base, conduction_velocity_m_per_s=cal.CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S), WITH_TRACT_LENGTHS),
    }


def with_learning(design: dynamics.SweepDesign) -> dynamics.SweepDesign:
    return replace(design, dynamics=replace(design.dynamics, arrival_learning_time=cal.ARRIVAL_LEARNING_TIME))


def build_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    return tuple(
        condition
        for name, (design, organisms) in baseline_designs(integration).items()
        for condition in (species.Condition(name, design, organisms), species.Condition(learned(name), with_learning(design), organisms))
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LearningPair:
    """The same organism and seed in a condition with learned arrival times and in its comparison condition."""

    learned: species.RunSummary
    comparison: species.RunSummary

    @property
    def concentration_step(self) -> float:
        return cal.ORGANISMS[self.learned.organism].grid_step(cal.CONCENTRATION_GRID.step)

    def loss_shift(self) -> float | None:
        """Loss concentration with learning minus without; None unless quorum is lost in both."""
        learned_loss, comparison_loss = self.learned.loss_concentration, self.comparison.loss_concentration
        return None if learned_loss is None or comparison_loss is None else learned_loss - comparison_loss


def quorum_never_lost(run: species.RunSummary) -> bool:
    return run.loss_concentration is None


def loss_not_delayed_by_more_than_a_step(pair: LearningPair) -> bool:
    """L2: with learning, quorum is still lost, at most one concentration step later than without."""
    shift = pair.loss_shift()
    return shift is not None and comparisons.at_most(shift, pair.concentration_step)


def loss_not_lowered_by_more_than_a_step(pair: LearningPair) -> bool:
    """L3: with learning, quorum is lost at most one concentration step earlier than without delays."""
    shift = pair.loss_shift()
    return shift is not None and comparisons.at_most(-shift, pair.concentration_step)


def awake_state_and_loss_kept(pair: LearningPair) -> bool:
    """L4: learning keeps at least 90% of the awake coherence and moves the loss by at most one step either way."""
    shift = pair.loss_shift()
    awake_kept = AWAKE_COHERENCE_KEPT * pair.comparison.induction_coherence[0]
    keeps_awake = comparisons.at_most(awake_kept, pair.learned.induction_coherence[0])
    return keeps_awake and shift is not None and comparisons.at_most(abs(shift), pair.concentration_step)


@dataclass(frozen=True)
class PairedTest:
    """A test comparing each seed's run in a condition with learning against the same seed in another condition."""

    check: reporting.Check[LearningPair]
    learned: str
    comparison: str


RUN_TESTS = (
    species.Pillar("L1", "With learned arrival times, fixed timing offsets never abolish quorum", learned(Baseline.NMDA_FIXED_OFFSETS), quorum_never_lost),
)

PAIRED_TESTS = (
    PairedTest(
        reporting.Check("L2", "With learned arrival times, timing jitter of the same size still abolishes quorum, at most one step later", loss_not_delayed_by_more_than_a_step),
        learned(Baseline.NMDA_ANTAGONIST), Baseline.NMDA_ANTAGONIST,
    ),
    PairedTest(
        reporting.Check("L3", "With learned arrival times, conduction delays no longer lower the loss concentration by more than one step", loss_not_lowered_by_more_than_a_step),
        learned(Baseline.CONDUCTION_DELAYS), Baseline.GABAERGIC,
    ),
    PairedTest(
        reporting.Check("L4", "Learning keeps the awake state (at least 90% of its coherence) and moves the GABAergic-like loss by at most one step", awake_state_and_loss_kept),
        learned(Baseline.GABAERGIC), Baseline.GABAERGIC,
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


PLAN = prespecified_runs.StudyPlan(
    name="learned timing",
    conditions=build_conditions,
    organisms=ORGANISMS,
    seed_offset=SEED_OFFSET,
    full_seeds=FULL_SEEDS,
    outcomes=evaluate,
)


def assemble_report(design: prespecified_runs.StudyDesign, started: str, results: Sequence[species.RunSummary]) -> dict[str, object]:
    outcomes = evaluate(results, ORGANISMS)
    return {
        "label": design.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "design": prespecified_runs.design_record(PLAN, design) | {"arrival_learning_time": cal.ARRIVAL_LEARNING_TIME},
        "tests": [asdict(o) | {"passes": prespecified_runs.passes(o)} for o in outcomes],
        "runs": [asdict(run) for run in results],
    }


def quantities() -> tuple[tuple[str, str, str], ...]:
    return tuple(("Loss concentration", condition.name, "loss_concentration") for condition in build_conditions(cal.QUICK_INTEGRATION))


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "passes"}) for t in report["tests"]]
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"### Pre-specified tests of learned arrival times (seeds in which the test holds; passes at {float(100 * prespecified_runs.PASS_SHARE):.0f}% or more)",
        "",
        *prespecified_runs.outcome_table(outcomes, organisms),
        "",
        "### Measurements (mean ± SD across seeds; concentrations relative to EC50)",
        "",
        *reporting.markdown_table(["Quantity", "Condition", *names], species.measurement_rows_for(quantities(), report["runs"], organisms)),
        "",
    ])


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = prespecified_runs.parse_design(PLAN, arguments, __doc__)
    started = datetime.now(timezone.utc).isoformat()
    report = assemble_report(design, started, prespecified_runs.run_study(PLAN, design))
    reporting.publish("learned_timing", report, to_markdown(report))
    return 0 if all(test["passes"] for test in report["tests"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
