"""Analysis A: the JSON and Markdown report, with verdicts for P15a and P15b and the window it needs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Sequence

import dpc_simulator as dpc
import provenance
import reporting
import validation_study as validation
from readout_study.pass_rule import PASS_RULE, PASSES, reliable_or_not
from round3_study import arousal_pulse as pulse
from round3_study.pulse_checks import (
    CONDITIONS,
    OBSERVATIONS,
    SMALLEST_INCREASES,
    TESTS,
    Condition,
    PulseMeasurement,
    condition_key,
    outcome_of,
)

Selector = Callable[[PulseMeasurement], float | None]


def window_value(read: Callable[[pulse.BistableWindow], float]) -> Selector:
    return lambda m: None if m.window is None else read(m.window)


def outcome_value(condition: Condition, read: Callable[[pulse.PulseOutcome], float | None]) -> Selector:
    return lambda m: None if outcome_of(m, condition) is None else read(outcome_of(m, condition))


def increase_value(name: str) -> Selector:
    return lambda m: m.smallest_increases.get(name)


def outcome_quantities(condition: Condition) -> tuple[tuple[str, Selector], ...]:
    name = condition_key(condition)
    return (
        (f"Concentration, {name}", outcome_value(condition, lambda o: o.concentration)),
        (f"S before the pulse, {name}", outcome_value(condition, lambda o: o.before)),
        (f"S at the end of the pulse, {name}", outcome_value(condition, lambda o: o.end_of_pulse)),
        (f"First step of the pulse with quorum, {name}", outcome_value(condition, lambda o: o.first_quorum_step)),
        (f"S after the pulse, {name}", outcome_value(condition, lambda o: o.after)),
    )


QUANTITIES: tuple[tuple[str, Selector], ...] = (
    ("c_off (loss)", window_value(lambda w: w.loss)),
    ("c_on (recovery)", window_value(lambda w: w.recovery)),
    ("Window width c_off - c_on (EC50)", window_value(lambda w: w.width)),
    ("Window midpoint (EC50)", window_value(lambda w: w.midpoint)),
    ("Precision needed to land inside the window: half its width as a share of its midpoint", window_value(lambda w: w.relative_half_width)),
    *(quantity for condition in CONDITIONS for quantity in outcome_quantities(condition)),
    *((f"Smallest increase of A for {name}", increase_value(name)) for name in SMALLEST_INCREASES),
    ("Seconds per seed", lambda m: m.duration_seconds),
)


@dataclass(frozen=True)
class PulseStudy:
    design: validation.StudyDesign
    started_utc: str
    finished_utc: str
    worker_count: int
    measurements: list[PulseMeasurement]

    def groups(self) -> dict[str, list[PulseMeasurement]]:
        return {validation.size_label(n): [m for m in self.measurements if m.node_count == n] for n in self.design.node_counts}


def design_record(study: PulseStudy) -> dict[str, object]:
    return {
        "label": study.design.label,
        "node_counts": list(study.design.node_counts),
        "seeds_per_size": study.design.seeds_per_size,
        "base_seed": study.design.base_seed,
        "worker_processes": study.worker_count,
        "reference_scenario": asdict(dpc.REFERENCE_SCENARIO),
        "pulse_increases": {p.name.lower(): pulse.PULSE_INCREASE[p] for p in pulse.Pulse},
        "maximum_arousal": pulse.MAXIMUM_AROUSAL,
        "pulse_steps": pulse.PULSE_STEPS,
        "above_loss_offset": pulse.ABOVE_LOSS_OFFSET,
        "smallest_increase_bisection_steps": pulse.SMALLEST_INCREASE_BISECTION_STEPS,
        "test_points": {p.name.lower(): p.value for p in pulse.TestPoint},
    }


def assemble_report(study: PulseStudy) -> dict[str, object]:
    groups = study.groups()
    return {
        "label": study.design.label,
        "started_utc": study.started_utc,
        "finished_utc": study.finished_utc,
        "provenance": provenance.collect(provenance.loaded_sources()),
        "design": design_record(study),
        "pass_rule": PASS_RULE,
        "tests": [asdict(o) | {"verdict": reliable_or_not(o)} for o in reporting.evaluate(TESTS, groups)],
        "observations": [asdict(o) for o in reporting.evaluate(OBSERVATIONS, groups)],
        "statistics": {label: {g: asdict(reporting.Distribution.of([select(m) for m in runs])) for g, runs in groups.items()} for label, select in QUANTITIES},
        "measurements": [asdict(m) for m in study.measurements],
    }


def every_test_passes(report: dict[str, object]) -> bool:
    verdicts = [test["verdict"] for test in report["tests"]]
    return bool(verdicts) and all(verdict == PASSES for verdict in verdicts)


def outcomes_with_verdicts(records: Sequence[dict[str, object]], groups: Sequence[str]) -> list[str]:
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in r.items() if k != "verdict"}) for r in records]
    lines = reporting.outcome_table(outcomes, groups)
    verdicts = [[r["identifier"], r["group"], r["verdict"]] for r in records]
    return [*lines, "", *reporting.markdown_table(["ID", "Network size", "Verdict"], verdicts)]


def distribution_text(record: dict[str, object]) -> str:
    return reporting.Distribution(**record).describe()


def to_markdown(report: dict[str, object]) -> str:
    groups = [validation.size_label(n) for n in report["design"]["node_counts"]]
    statistics_rows = [[label, *[distribution_text(by_group[g]) for g in groups]] for label, by_group in report["statistics"].items()]
    observations = [reporting.CheckOutcome(**r) for r in report["observations"]]
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"Seeds per size: {report['design']['seeds_per_size']} (base seed {report['design']['base_seed']}). Pass rule: {report['pass_rule']}.",
        "",
        "### Pre-specified tests (seeds in which the test holds)",
        "",
        *outcomes_with_verdicts(report["tests"], groups),
        "",
        "### Reported without a verdict",
        "",
        *reporting.outcome_table(observations, groups),
        "",
        "### Window and pulse outcomes (mean ± SD across seeds; concentrations relative to the EC50)",
        "",
        *reporting.markdown_table(["Quantity", *groups], statistics_rows),
        "",
    ])
