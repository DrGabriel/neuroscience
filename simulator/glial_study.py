"""Glial regulation study (postulate P9): myelin, microglia and astrocytes in the percolation model.

Every check below was specified before the multi-seed run. A single exploratory seed at
N = 1,000 was run beforehand to confirm that the code executes; its results were seen before
the checks were written, so the checks are not blind to the direction of the effects.

Usage:
    python3 glial_study.py           # full study
    python3 glial_study.py --quick   # small smoke run

Exit status is non-zero if any pre-specified test fails for any seed at any size.
"""

from __future__ import annotations

import argparse
import operator
import os
import sys
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Callable, Sequence

import comparisons
import dpc_simulator as dpc
import glial_regulation as glia
import provenance
import reporting
from validation_study import (
    SeedTask,
    StudyDesign,
    SummarySelector,
    ThresholdSummary,
    evaluate_claims,
    inertia_width,
    size_label,
    sized,
)

FULL_NODE_COUNTS = (302, 1_000, 10_000, 100_000)
FULL_SEEDS_PER_SIZE = 20
QUICK_NODE_COUNTS = (302, 1_000)
QUICK_SEEDS_PER_SIZE = 3


@dataclass(frozen=True)
class GlialMeasurement:
    node_count: int
    seed: int
    # (parameter value, thresholds) pairs, in the order of glial_regulation's series.
    by_myelin_integrity: tuple[tuple[float, ThresholdSummary], ...]
    by_microglial_gain: tuple[tuple[float, ThresholdSummary], ...]
    global_sleep: dpc.StableStates
    global_sleep_astrocytes_silenced: dpc.StableStates
    duration_seconds: float

    def microglial(self, gain: float) -> ThresholdSummary:
        return dict(self.by_microglial_gain)[gain]


def measure_seed(task: SeedTask) -> GlialMeasurement:
    started = time.perf_counter()
    reference = sized(dpc.REFERENCE_SCENARIO, task)
    curve = dpc.build_curve(reference)
    return GlialMeasurement(
        node_count=task.node_count,
        seed=task.seed,
        by_myelin_integrity=tuple(
            (integrity, ThresholdSummary.of(dpc.run_on_curve(curve, glia.demyelinated(reference, integrity))))
            for integrity in glia.MYELIN_INTEGRITY_SERIES
        ),
        by_microglial_gain=tuple(
            (gain, ThresholdSummary.of(dpc.run_on_curve(curve, reference, glia.with_microglia(gain))))
            for gain in glia.MICROGLIAL_GAIN_SERIES
        ),
        global_sleep=dpc.stable_states(replace(reference, state=glia.GLOBAL_SLEEP), concentration=0.0),
        global_sleep_astrocytes_silenced=dpc.stable_states(
            replace(reference, state=glia.astrocytes_silenced(glia.GLOBAL_SLEEP)), concentration=0.0
        ),
        duration_seconds=time.perf_counter() - started,
    )


# ---------------------------------------------------------------------------
# Pre-specified tests
# ---------------------------------------------------------------------------


def consecutive_pairs_hold(values: Sequence[float | None], relation: Callable[[float, float], bool]) -> bool:
    """True when every value is defined and relation(earlier, later) holds for each consecutive pair."""
    if any(value is None for value in values):
        return False
    return all(relation(earlier, later) for earlier, later in zip(values, values[1:]))


def damaged_myelin_lowers_loss_concentration(m: GlialMeasurement) -> bool:
    return consecutive_pairs_hold([summary.loss_concentration for _, summary in m.by_myelin_integrity], operator.gt)


def depletion_hastens_emergence(m: GlialMeasurement) -> bool:
    """Recovery at a higher concentration without microglia; a loop that never recovers counts as later."""
    depleted, strongest = m.microglial(glia.MICROGLIAL_DEPLETED_GAIN), m.microglial(glia.STRONGEST_MICROGLIAL_GAIN)
    if depleted.recovery_concentration is None:
        return False
    return strongest.recovery_concentration is None or depleted.recovery_concentration > strongest.recovery_concentration


def depletion_does_not_hasten_induction(m: GlialMeasurement) -> bool:
    depleted, strongest = m.microglial(glia.MICROGLIAL_DEPLETED_GAIN), m.microglial(glia.STRONGEST_MICROGLIAL_GAIN)
    return consecutive_pairs_hold([depleted.loss_concentration, strongest.loss_concentration], operator.ge)


def inertia_grows_with_microglial_gain(m: GlialMeasurement) -> bool:
    widths = [inertia_width(summary) for _, summary in m.by_microglial_gain]
    never_shrinks = consecutive_pairs_hold(widths, comparisons.at_most)
    return never_shrinks and comparisons.exceeds(widths[-1], widths[0])


def silenced_astrocytes_wake_the_sleeper(m: GlialMeasurement) -> bool:
    """Sleep with global down-states has lost quorum; without the astrocytic share of them, quorum returns."""
    asleep, silenced = m.global_sleep, m.global_sleep_astrocytes_silenced
    return not asleep.holds_quorum and silenced.holds_quorum


TESTS = (
    reporting.Check(
        "M1",
        f"Damaged myelin lowers the loss concentration (integrity {' > '.join(map(str, glia.MYELIN_INTEGRITY_SERIES))})",
        damaged_myelin_lowers_loss_concentration,
        reporting.CONSISTENCY_CHECK,
    ),
    reporting.Check(
        "G1",
        "Removing the microglial loop hastens emergence (direction of Cao et al., 2023, P2Y12 loss)",
        depletion_hastens_emergence,
        reporting.CONSISTENCY_CHECK,
    ),
    reporting.Check(
        "G2",
        "Removing the microglial loop does not hasten induction",
        depletion_does_not_hasten_induction,
        reporting.CONSISTENCY_CHECK,
    ),
    reporting.Check(
        "G3",
        "Neural inertia grows with the strength of the microglial loop",
        inertia_grows_with_microglial_gain,
        reporting.CONSISTENCY_CHECK,
    ),
    reporting.Check(
        "A1",
        f"Re-specified after the down-state model changed: with global down-states ({glia.GLOBAL_DOWN_STATE_SHARE} of populations), "
        f"sleep loses quorum, and silencing astrocytes' share ({glia.ASTROCYTIC_DOWN_STATE_SHARE}) of them restores it",
        silenced_astrocytes_wake_the_sleeper,
    ),
)


def myelin_loss(integrity: float) -> SummarySelector:
    return lambda m: dict(m.by_myelin_integrity)[integrity].loss_concentration


def microglial_threshold(gain: float, field: str) -> SummarySelector:
    return lambda m: getattr(m.microglial(gain), field)


REPORTED_QUANTITIES: tuple[tuple[str, SummarySelector], ...] = (
    *[(f"c_off, myelin integrity {integrity}", myelin_loss(integrity)) for integrity in glia.MYELIN_INTEGRITY_SERIES],
    *[
        (f"{label}, microglial gain {gain}", microglial_threshold(gain, field))
        for gain in glia.MICROGLIAL_GAIN_SERIES
        for label, field in (("c_off", "loss_concentration"), ("c_on", "recovery_concentration"))
    ],
    ("Seconds per seed", lambda m: m.duration_seconds),
)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GlialReport:
    started_utc: datetime
    finished_utc: datetime
    provenance: dict[str, object]
    measurements: list[GlialMeasurement]
    outcomes: list[reporting.CheckOutcome]

    @property
    def all_tests_pass(self) -> bool:
        return all(outcome.holds for outcome in self.outcomes)


def collect_provenance(design: StudyDesign, worker_count: int) -> dict[str, object]:
    return provenance.collect(provenance.loaded_sources()) | {
        "design": {
            "label": design.label,
            "node_counts": list(design.node_counts),
            "seeds_per_size": design.seeds_per_size,
            "base_seed": design.base_seed,
            "worker_processes": worker_count,
            "reference_scenario": asdict(dpc.REFERENCE_SCENARIO),
            "demyelination_jitter_gain": glia.DEMYELINATION_JITTER_GAIN,
            "myelin_integrity_series": list(glia.MYELIN_INTEGRITY_SERIES),
            "microglial_gain_series": list(glia.MICROGLIAL_GAIN_SERIES),
            "astrocytic_down_state_share": glia.ASTROCYTIC_DOWN_STATE_SHARE,
            "global_down_state_share": glia.GLOBAL_DOWN_STATE_SHARE,
        },
    }


def to_markdown(report: GlialReport) -> str:
    design = report.provenance["design"]
    node_counts = design["node_counts"]
    sizes = [size_label(n) for n in node_counts]
    timestamps = {
        "started_utc": report.started_utc.isoformat(timespec="seconds"),
        "finished_utc": report.finished_utc.isoformat(timespec="seconds"),
    }
    study_rows = [
        f"| Wall time | {(report.finished_utc - report.started_utc).total_seconds():.1f} s |",
        f"| Worker processes | {design['worker_processes']} |",
        f"| Seeds per size | {design['seeds_per_size']} (base seed {design['base_seed']}) |",
    ]
    statistics_rows = [
        [label, *[reporting.describe([select(m) for m in report.measurements if m.node_count == n]) for n in node_counts]]
        for label, select in REPORTED_QUANTITIES
    ]
    verdict = (
        "Every pre-specified test passes for every seed at every size."
        if report.all_tests_pass
        else "At least one pre-specified test failed; see the table."
    )
    lines = [
        *reporting.run_metadata_section(timestamps, [*provenance.markdown_rows(report.provenance), *study_rows]),
        "### Pre-specified tests (seeds in which the test passes)",
        "",
        *reporting.outcome_table(report.outcomes, sizes),
        "",
        "### Thresholds (mean ± SD across seeds, relative concentration units)",
        "",
        *reporting.markdown_table(["Quantity", *sizes], statistics_rows),
        "",
        f"**Verdict:** {verdict}",
        "",
    ]
    return "\n".join(lines)


def to_document(report: GlialReport, label: str) -> dict[str, object]:
    return {
        "label": label,
        "started_utc": report.started_utc.isoformat(),
        "finished_utc": report.finished_utc.isoformat(),
        "all_tests_pass": report.all_tests_pass,
        "provenance": report.provenance,
        "tests": [asdict(outcome) | {"holds": outcome.holds} for outcome in report.outcomes],
        "measurements": [asdict(measurement) for measurement in report.measurements],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def tests_markdown(measurements: Sequence[GlialMeasurement], node_counts: Sequence[int]) -> str:
    outcomes = evaluate_claims(TESTS, measurements, node_counts)
    return "\n".join(reporting.outcome_table(outcomes, [size_label(n) for n in node_counts]))


def run_study(design: StudyDesign, worker_count: int) -> GlialReport:
    started = datetime.now(timezone.utc)
    record = collect_provenance(design, worker_count)
    live = reporting.ParallelRun("glia", worker_count, live_markdown=lambda done: tests_markdown(done, design.node_counts))
    measurements = reporting.run_in_parallel(measure_seed, design.tasks(), live)
    return GlialReport(
        started_utc=started,
        finished_utc=datetime.now(timezone.utc),
        provenance=record,
        measurements=measurements,
        outcomes=evaluate_claims(TESTS, measurements, design.node_counts),
    )


def parse_design(arguments: Sequence[str]) -> StudyDesign:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="small smoke run instead of the full study")
    if parser.parse_args(arguments).quick:
        return StudyDesign("quick", QUICK_NODE_COUNTS, QUICK_SEEDS_PER_SIZE)
    return StudyDesign("full", FULL_NODE_COUNTS, FULL_SEEDS_PER_SIZE)


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    report = run_study(design, os.cpu_count() or 1)
    reporting.publish("glia", to_document(report, design.label), to_markdown(report))
    return 0 if report.all_tests_pass else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
