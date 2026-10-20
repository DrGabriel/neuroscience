"""The JSON and Markdown report of the DPC readout study."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from operator import attrgetter
from typing import Callable, Sequence

import calibration as cal
import connectome_inertia
import dpc_readout as readout
import prespecified_runs
import provenance
import reporting
import species_study as species
from readout_study.disconnection import NOT_EVALUABLE, disconnection_verdict
from readout_study.pass_rule import PASS_RULE, PASSES, reliable_or_not
from readout_study.plans import DISCONNECTION_PLAN, BlockResult, StudyResults
from readout_study.running import Reading, ReadoutRun
from readout_study.settings import DIRECTED_ORGANISMS, LOCKING_THRESHOLD, METASTABLE_COHERENCE_RANGE, METASTABLE_COHERENCE_TARGET, READOUT

NOT_CALIBRATED = "not calibrated"
NOT_AVAILABLE = "n/a"
YES, NO = "yes", "no"
FEEDBACK_DECIMALS = 3
LAMBDA_MS_DECIMALS = 1
RATIO_DECIMALS = 3
TARGET_DECIMALS = 2

SERIES_FIELDS: tuple[tuple[str, Callable[[readout.ConcentrationReadout], object]], ...] = (
    ("concentration", attrgetter("concentration")),
    ("giant_share", attrgetter("undirected.mean_share")),
    ("cycles_with_quorum", attrgetter("undirected.cycles_with_quorum")),
    ("cycles", attrgetter("undirected.cycles")),
    ("strongly_connected_share", attrgetter("strongly_connected.mean_share")),
    ("receiver_phase_share", attrgetter("receiver_phase.mean_share")),
    ("jitter_only_share", attrgetter("jitter_only.mean_share")),
    ("counting_share", attrgetter("counting_share")),
    ("static_counting_share", attrgetter("budget.static_counting_share")),
    ("effective_coupling", attrgetter("budget.effective_coupling")),
    ("reference_coupling", attrgetter("budget.reference_coupling")),
    ("susceptibility", attrgetter("fluctuations.susceptibility")),
    ("independent_susceptibility", attrgetter("fluctuations.independent_susceptibility")),
    ("coherence_autocorrelation", attrgetter("fluctuations.coherence_autocorrelation")),
)


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def series(readouts: Sequence[readout.ConcentrationReadout]) -> dict[str, list[object]]:
    return {name: [field(point) for point in readouts] for name, field in SERIES_FIELDS}


def at_loss(run: ReadoutRun, loss: float | None) -> dict[str, float | None]:
    """Counting share against its static prediction, and coupling against Kuramoto's threshold, at a loss."""
    point = run.readout_at(loss)
    if point is None:
        return {"counting_over_static": None, "coupling_over_threshold": None}
    static = point.budget.static_counting_share
    return {
        "counting_over_static": point.counting_share / static if static > 0 else None,
        "coupling_over_threshold": point.budget.effective_coupling / LOCKING_THRESHOLD,
    }


def directed_loss(run: ReadoutRun) -> float | None:
    return run.loss_under(Reading.STRONGLY_CONNECTED) if run.organism in DIRECTED_ORGANISMS else None


def loss_fields(run: ReadoutRun) -> dict[str, object]:
    return {
        "dpc_loss_concentration": run.dpc_loss_concentration,
        "dpc_recovery_concentration": run.dpc_recovery_concentration,
        "strongly_connected_loss_concentration": directed_loss(run),
        "receiver_phase_loss_concentration": run.loss_under(Reading.RECEIVER_PHASE),
        "static_loss_concentration": run.loss_under(Reading.JITTER_ONLY),
        "at_dpc_loss": at_loss(run, run.dpc_loss_concentration),
        "at_coherence_loss": at_loss(run, run.coherence.loss_concentration),
    }


def run_record(run: object) -> dict[str, object]:
    if not isinstance(run, ReadoutRun):
        return asdict(run)
    return asdict(run.coherence) | loss_fields(run) | {"induction_readout": series(run.induction), "emergence_readout": series(run.emergence)}


def seeds_used(block: BlockResult) -> list[int]:
    first = prespecified_runs.first_seed(block.plan)
    return list(range(first, first + max(block.design.seeds_per_organism.values(), default=0)))


def block_verdict(block: BlockResult) -> prespecified_runs.Verdict:
    return disconnection_verdict(block.runs) if block.plan.name == DISCONNECTION_PLAN.name else reliable_or_not


def block_record(block: BlockResult) -> dict[str, object]:
    verdict = block_verdict(block)
    return {
        "name": block.plan.name,
        "design": prespecified_runs.design_record(block.plan, block.design) | {"pass_share": PASS_RULE, "seeds": seeds_used(block)},
        "tests": [asdict(o) | {"verdict": verdict(o)} for o in block.outcomes()],
        "runs": [run_record(run) for run in block.runs],
    }


def percolation_record(organism: connectome_inertia.OrganismInertia) -> dict[str, object]:
    return {
        "organism": organism.organism,
        "calibrations": [asdict(c) | {"reproduced": c.reproduced} for c in organism.calibrations],
        "held_out": [asdict(seed) for seed in organism.held_out],
    }


def percolation_tests(results: Sequence[connectome_inertia.OrganismInertia]) -> list[dict[str, object]]:
    outcomes = connectome_inertia.evaluate([seed for organism in results for seed in organism.held_out])
    return [asdict(o) | {"verdict": reliable_or_not(o)} for o in outcomes]


def assemble_report(results: StudyResults) -> dict[str, object]:
    return {
        "label": results.label,
        "started_utc": results.started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "readout": asdict(READOUT) | {"cycle_majority": float(readout.CYCLE_MAJORITY)},
        "pass_rule": PASS_RULE,
        "locking_threshold": LOCKING_THRESHOLD,
        "feedback_calibrations": [asdict(c) for c in results.calibrations.feedback],
        "coupling_calibrations": [asdict(c) for c in results.calibrations.coupling],
        "blocks": [block_record(block) for block in results.blocks],
        "percolation_inertia": {"organisms": [percolation_record(o) for o in results.percolation], "tests": percolation_tests(results.percolation)},
    }


def every_evaluated_test_passes(report: dict[str, object]) -> bool:
    tests = [t for block in report["blocks"] for t in block["tests"]] + report["percolation_inertia"]["tests"]
    verdicts = [t["verdict"] for t in tests if t["verdict"] != NOT_EVALUABLE]
    return bool(verdicts) and all(verdict == PASSES for verdict in verdicts)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def nested(field: str, key: str) -> Callable[[dict[str, object]], object]:
    return lambda record: (record.get(field) or {}).get(key)


# Context, no verdict: quantities read from each block's runs (fields of run_record).
MEASUREMENTS: tuple[tuple[str, Callable[[dict[str, object]], object]], ...] = (
    ("DPC loss concentration", lambda r: r.get("dpc_loss_concentration")),
    ("Coherence-criterion loss concentration", lambda r: r.get("loss_concentration")),
    ("Static percolation loss (timing draws alone)", lambda r: r.get("static_loss_concentration")),
    ("DPC loss, timed at the receiver", lambda r: r.get("receiver_phase_loss_concentration")),
    ("DPC loss, strongly connected component (directed wiring only)", lambda r: r.get("strongly_connected_loss_concentration")),
    ("Counting share over static prediction, at DPC loss", nested("at_dpc_loss", "counting_over_static")),
    ("Effective coupling over Kuramoto threshold, at DPC loss", nested("at_dpc_loss", "coupling_over_threshold")),
    ("Effective coupling over Kuramoto threshold, at coherence loss", nested("at_coherence_loss", "coupling_over_threshold")),
    ("DPC recovery concentration", lambda r: r.get("dpc_recovery_concentration")),
    ("Awake global coherence", lambda r: r["induction_coherence"][0]),
    ("Seconds per run", lambda r: r["seconds"]),
)


def optional(value: float | None, decimals: int) -> str:
    return NOT_AVAILABLE if value is None else f"{value:.{decimals}f}"


def measurement_rows(block: dict[str, object], organisms: Sequence[str]) -> list[list[str]]:
    conditions = list(dict.fromkeys(run["condition"] for run in block["runs"]))
    return [
        [label, condition, *[reporting.describe([value(r) for r in block["runs"] if r["organism"] == o and r["condition"] == condition]) for o in organisms]]
        for condition in conditions
        for label, value in MEASUREMENTS
    ]


def block_heading(block: dict[str, object]) -> str:
    seeds = block["design"]["seeds"]
    return f"### {block['name']} (seeds {seeds[0]} to {seeds[-1]})" if seeds else f"### {block['name']} (not run)"


def outcome_lines(tests: Sequence[dict[str, object]], organisms: Sequence[str]) -> list[str]:
    outcomes = [reporting.CheckOutcome(**{k: v for k, v in t.items() if k != "verdict"}) for t in tests]
    verdicts = {(t["identifier"], t["group"]): t["verdict"] for t in tests}
    return prespecified_runs.outcome_table(outcomes, organisms, lambda o: verdicts[(o.identifier, o.group)])


def block_markdown(block: dict[str, object]) -> list[str]:
    organisms = [o for o in cal.ORGANISMS if any(run["organism"] == o for run in block["runs"])]
    names = [cal.ORGANISMS[o].display_name for o in organisms]
    return [
        block_heading(block),
        "",
        *outcome_lines(block["tests"], organisms),
        "",
        "Measurements (mean ± SD across seeds; concentrations relative to EC50; context, no verdict):",
        "",
        *reporting.markdown_table(["Quantity", "Condition", *names], measurement_rows(block, organisms)),
        "",
    ]


def calibration_rows(records: Sequence[dict[str, object]]) -> list[list[str]]:
    return [
        [cal.ORGANISMS[c["organism"]].display_name, NOT_CALIBRATED if c["value"] is None else f"{c['value']:.{FEEDBACK_DECIMALS}f}", optional(c["achieved"], RATIO_DECIMALS)]
        for c in records
    ]


def calibration_markdown(report: dict[str, object]) -> list[str]:
    low, high = METASTABLE_COHERENCE_RANGE
    return [
        f"### Phase-model feedback calibrated on the scan seeds (target ratio {cal.INERTIA_TARGET_RATIO}; Kuramoto threshold {report['locking_threshold']:.{FEEDBACK_DECIMALS}f})",
        "",
        *reporting.markdown_table(["Organism", "Feedback", "Mean DPC inertia ratio"], calibration_rows(report["feedback_calibrations"])),
        "",
        f"### Weaker coupling calibrated on its own seeds (awake coherence {low} to {high}, target {METASTABLE_COHERENCE_TARGET})",
        "",
        *reporting.markdown_table(["Organism", "Coupling K", "Mean awake coherence"], calibration_rows(report["coupling_calibrations"])),
        "",
    ]


def percolation_calibration_row(organism: str, calibration: dict[str, object]) -> list[str]:
    return [
        cal.ORGANISMS[organism].display_name, f"{calibration['target_ratio']:.{TARGET_DECIMALS}f}", optional(calibration["feedback_ms"], LAMBDA_MS_DECIMALS),
        optional(calibration["mean_ratio"], RATIO_DECIMALS), YES if calibration["reproduced"] else NO,
    ]


def percolation_markdown(report: dict[str, object]) -> list[str]:
    section = report["percolation_inertia"]
    organisms = [o["organism"] for o in section["organisms"]]
    rows = [percolation_calibration_row(o["organism"], c) for o in section["organisms"] for c in o["calibrations"]]
    return [
        "### Percolation model on the connectome graphs: λ calibrated on the calibration seeds, tested on held-out seeds",
        "",
        *reporting.markdown_table(["Organism", "Target ratio", "λ (ms)", "Mean ratio on calibration seeds", "Reproduced"], rows),
        "",
        *outcome_lines(section["tests"], [o for o in cal.ORGANISMS if o in organisms]),
        "",
    ]


def to_markdown(report: dict[str, object]) -> str:
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"Pass rule: {report['pass_rule']}.",
        "",
        *[line for block in report["blocks"] for line in block_markdown(block)],
        *calibration_markdown(report),
        *percolation_markdown(report),
    ])
