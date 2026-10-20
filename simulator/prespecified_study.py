"""Pre-specified tests on fresh seeds: K2 (ketamine's timing faults on feedback connections) and P1c.

The tests, their conditions, the seeds and the pass rule were written into the paper (Appendix C.7)
before this study was first run. Seeds start at BASE_SEED + SEED_OFFSET, which no earlier run used.
A test passes for an organism when it holds in at least prespecified_runs.PASS_SHARE of that organism's seeds.

Usage:
    ../.venv/bin/python prespecified_study.py            # full study
    ../.venv/bin/python prespecified_study.py --quick    # short smoke run, one seed each

Exit status is non-zero if any test fails for any organism. A failing test is a scientific
result, not a software error: the report is written either way.
"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_runs
import provenance
import reporting
import species_study as species

SEED_OFFSET = 2000
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


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------


PLAN = prespecified_runs.StudyPlan(
    name="prespecified",
    conditions=build_conditions,
    organisms=tuple(cal.ORGANISMS),
    seed_offset=SEED_OFFSET,
    full_seeds=FULL_SEEDS,
    outcomes=evaluate,
)


def feedback_shares() -> dict[str, float]:
    """Share of each directed connectome's connections that are feedback, as reported in the paper."""
    return {o: float(species.load_connectome(o).feedback_connections().mean()) for o in DIRECTED_ORGANISMS}


def assemble_report(design: prespecified_runs.StudyDesign, started: str, results: Sequence[species.RunSummary]) -> dict[str, object]:
    outcomes = evaluate(results, PLAN.organisms)
    return {
        "label": design.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "design": prespecified_runs.design_record(PLAN, design),
        "feedback_shares": feedback_shares(),
        "tests": [asdict(o) | {"passes": prespecified_runs.passes(o)} for o in outcomes],
        "runs": [asdict(run) for run in results],
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


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in cal.ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "passes"}) for t in report["tests"]]
    shares = [[cal.ORGANISMS[o].display_name, f"{100 * share:.1f}%"] for o, share in report["feedback_shares"].items()]
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"### Pre-specified tests (seeds in which the test holds; passes at {float(100 * prespecified_runs.PASS_SHARE):.0f}% or more)",
        "",
        *prespecified_runs.outcome_table(outcomes, organisms),
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


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = prespecified_runs.parse_design(PLAN, arguments, __doc__)
    started = datetime.now(timezone.utc).isoformat()
    report = assemble_report(design, started, prespecified_runs.run_study(PLAN, design))
    reporting.publish("prespecified", report, to_markdown(report))
    return 0 if all(test["passes"] for test in report["tests"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
