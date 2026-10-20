"""Pre-specified test K1c: do ketamine-like timing faults on the sensory pathways cut the senses off from an agreement
that survives, once the chance floor of the broadcast measure is removed?

K1 asked this with broadcast measured over two stimulus cycles and failed in about half the seeds. A post hoc
diagnostic then found that a coherent population shows some locking to any rhythm over so short a window (limitation
31 of the paper). K1c repeats K1's condition on fresh seeds with a window of eight stimulus cycles, and runs each seed
twice: with the stimulus applied and with a phantom stimulus of zero strength, whose locking measures the floor. The
tests, conditions, seeds and pass rule were written into the paper (Appendix C.11) before this study was first run.

Usage:
    ../.venv/bin/python disconnection_study.py            # full study
    ../.venv/bin/python disconnection_study.py --quick    # short smoke run, one seed each

Exit status is non-zero unless K1c passes for every organism on which it can be evaluated. A failing test is a
scientific result, not a software error: the report is written either way.
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from fractions import Fraction
from typing import Sequence

import calibration as cal
import comparisons
import phase_dynamics as dynamics
import prespecified_runs
import provenance
import reporting
import species_study as species

SEED_OFFSET = 4000
# The fly is not run: each run takes about an hour, and its awake broadcast (about 0.05 to 0.06) is likely mostly floor.
ORGANISMS = ("celegans", "human")
FULL_SEEDS = {"celegans": 20, "human": 20}
WINDOW_CYCLES = 8
# A seed can lose broadcast only if there is some to lose: awake locking to the stimulus must be at least this many
# times the awake locking to the phantom.
AWAKE_SIGNAL_MULTIPLE = 2
# K1c is evaluated for an organism only when at least this share of its seeds passes that gate.
MIN_EVALUABLE_SHARE = Fraction(1, 2)
NOT_EVALUABLE = "not evaluable (fewer than half the seeds have an awake broadcast above the floor)"

APPLIED = f"{species.ConditionName.KETAMINE_PATHWAYS}, {WINDOW_CYCLES}-cycle window"
PHANTOM = f"NMDA-antagonist-like on sensory pathways, phantom stimulus of zero strength, {WINDOW_CYCLES}-cycle window"


def long_window(integration: dynamics.IntegrationSettings) -> dynamics.IntegrationSettings:
    """The full study measures over eight stimulus cycles; the smoke run keeps its short window."""
    if integration != cal.FULL_INTEGRATION:
        return integration
    return replace(integration, measurement_steps=cal.measurement_steps_for(WINDOW_CYCLES))


def build_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    k1 = next(c for c in species.build_conditions(integration) if c.name == species.ConditionName.KETAMINE_PATHWAYS)
    applied = replace(k1.design, integration=long_window(integration))
    phantom = replace(applied, stimulus=replace(applied.stimulus, strength=0.0))
    return (species.Condition(APPLIED, applied, ORGANISMS), species.Condition(PHANTOM, phantom, ORGANISMS))


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StimulusPair:
    """The same organism and seed with the stimulus applied and with the phantom."""

    applied: species.RunSummary
    phantom: species.RunSummary

    @property
    def awake_excess(self) -> float:
        return self.applied.awake_broadcast_entrainment - self.phantom.awake_broadcast_entrainment

    @property
    def deepest_excess(self) -> float:
        return self.applied.deepest_broadcast_entrainment - self.phantom.deepest_broadcast_entrainment

    @property
    def has_awake_broadcast(self) -> bool:
        floor = AWAKE_SIGNAL_MULTIPLE * self.phantom.awake_broadcast_entrainment
        return comparisons.at_most(floor, self.applied.awake_broadcast_entrainment)


def disconnected_above_the_floor(pair: StimulusPair) -> bool | None:
    """K1c: quorum holds at the highest concentration while the broadcast above the floor falls to half its awake
    value or less. Undefined (None) for a seed whose awake broadcast does not clear the floor."""
    if not pair.has_awake_broadcast:
        return None
    keeps_quorum = comparisons.at_most(cal.QUORUM_FRACTION, pair.applied.deepest_coherence_fraction)
    return keeps_quorum and comparisons.at_most(pair.deepest_excess, cal.BROADCAST_COLLAPSE_FRACTION * pair.awake_excess)


K1C = reporting.Check(
    "K1c",
    "Ketamine-like faults on the sensory pathways keep quorum while the broadcast above the floor falls to half or less",
    disconnected_above_the_floor,
)


def stimulus_pairs(runs: Sequence[species.RunSummary]) -> list[StimulusPair]:
    by_key = {(r.organism, r.condition, r.seed): r for r in runs}
    return [
        StimulusPair(run, by_key[(run.organism, PHANTOM, run.seed)])
        for run in runs
        if run.condition == APPLIED and (run.organism, PHANTOM, run.seed) in by_key
    ]


def evaluate(runs: Sequence[species.RunSummary], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    pairs = stimulus_pairs(runs)
    groups = {cal.ORGANISMS[o].display_name: [p for p in pairs if p.applied.organism == o] for o in organisms}
    return reporting.evaluate((K1C,), groups)


def seeds_run(outcome: reporting.CheckOutcome, runs: Sequence[species.RunSummary]) -> int:
    return sum(r.condition == APPLIED and cal.ORGANISMS[r.organism].display_name == outcome.group for r in runs)


def verdict_for(runs: Sequence[species.RunSummary]) -> prespecified_runs.Verdict:
    def verdict(outcome: reporting.CheckOutcome) -> str:
        evaluable = comparisons.at_least_share(outcome.runs_applicable, seeds_run(outcome, runs), MIN_EVALUABLE_SHARE)
        return prespecified_runs.pass_or_fail(outcome) if evaluable else NOT_EVALUABLE
    return verdict


# ---------------------------------------------------------------------------
# Study and report
# ---------------------------------------------------------------------------


PLAN = prespecified_runs.StudyPlan(
    name="disconnection",
    conditions=build_conditions,
    organisms=ORGANISMS,
    seed_offset=SEED_OFFSET,
    full_seeds=FULL_SEEDS,
    outcomes=evaluate,
)


def assemble_report(design: prespecified_runs.StudyDesign, started: str, results: Sequence[species.RunSummary]) -> dict[str, object]:
    verdict = verdict_for(results)
    return {
        "label": design.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "design": prespecified_runs.design_record(PLAN, design) | {
            "window_cycles": WINDOW_CYCLES,
            "awake_signal_multiple": AWAKE_SIGNAL_MULTIPLE,
            "min_evaluable_share": float(MIN_EVALUABLE_SHARE),
        },
        "tests": [asdict(o) | {"verdict": verdict(o)} for o in evaluate(results, ORGANISMS)],
        "runs": [asdict(run) for run in results],
    }


def secondary_rows(runs: list[dict[str, object]], organisms: Sequence[str]) -> list[list[str]]:
    """Context, no verdict: the original K1 criterion at the long window, and the medians behind K1c."""
    summaries = [species.RunSummary(**{k: tuple(v) if isinstance(v, list) else v for k, v in r.items()}) for r in runs]
    pairs = stimulus_pairs(summaries)
    rows = []
    for organism in organisms:
        mine = [p for p in pairs if p.applied.organism == organism]
        k1 = sum(species.disconnected_but_internally_coherent(p.applied) for p in mine)
        rows.append([
            cal.ORGANISMS[organism].display_name,
            f"{sum(p.has_awake_broadcast for p in mine)}/{len(mine)}",
            f"{k1}/{len(mine)}",
            *[f"{statistics.median(values):.3f}" for values in (
                [p.applied.awake_broadcast_entrainment for p in mine], [p.phantom.awake_broadcast_entrainment for p in mine],
                [p.applied.deepest_broadcast_entrainment for p in mine], [p.phantom.deepest_broadcast_entrainment for p in mine],
            )],
        ])
    return rows


def to_markdown(report: dict[str, object]) -> str:
    organisms = [o for o in ORGANISMS if any(run["organism"] == o for run in report["runs"])]
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "verdict"}) for t in report["tests"]]
    verdicts = {(t["identifier"], t["group"]): t["verdict"] for t in report["tests"]}
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"### Pre-specified test K1c (seeds in which it holds, of the seeds that pass the awake gate; passes at {float(100 * prespecified_runs.PASS_SHARE):.0f}% or more)",
        "",
        *prespecified_runs.outcome_table(outcomes, organisms, lambda o: verdicts[(o.identifier, o.group)]),
        "",
        "### Context, no verdict (medians across seeds of the locking value of the non-sensory populations)",
        "",
        *reporting.markdown_table(
            ["Organism", "Seeds passing the awake gate", "Original K1 criterion at this window", "Awake, applied", "Awake, phantom", "Highest dose, applied", "Highest dose, phantom"],
            secondary_rows(report["runs"], organisms),
        ),
        "",
    ])


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = prespecified_runs.parse_design(PLAN, arguments, __doc__)
    started = datetime.now(timezone.utc).isoformat()
    report = assemble_report(design, started, prespecified_runs.run_study(PLAN, design))
    reporting.publish("disconnection", report, to_markdown(report))
    evaluated = [t for t in report["tests"] if t["verdict"] != NOT_EVALUABLE]
    return 0 if evaluated and all(t["verdict"] == "passes" for t in evaluated) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
