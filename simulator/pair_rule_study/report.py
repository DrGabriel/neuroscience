"""The JSON and Markdown report of the pair-rule study: verdicts for T2a-1, T2b-1 and SP1-1, and per organism, without
a verdict, the loss under every pair rule, the counting share at loss and the coherence-criterion loss."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from operator import itemgetter
from typing import Callable, Sequence

import calibration as cal
import dpc_readout as readout
import prespecified_runs
import provenance
import reporting
import species_study as species
from connection_pairs import PRIMARY_PAIR_RULE, PairRule
from pair_rule_study.measures import counting_share_at_primary_loss, giant_share_at_highest_concentration, loss_under
from pair_rule_study.plan import PairRuleResults
from readout_study import report as readout_report
from readout_study.pass_rule import PASS_RULE, PASSES, reliable_or_not
from readout_study.running import ReadoutRun
from readout_study.settings import READOUT

LOSS_FIELD = "pair_rule_loss_concentration"
HIGHEST_CONCENTRATION_FIELD = "pair_rule_giant_share_at_highest_concentration"
COUNTING_AT_LOSS_FIELD = "primary_counting_share_at_loss"
RULE_SUFFIX = {PairRule.ONE_PER_CONNECTION: " (primary)", PairRule.BOTH_DIRECTIONS: "", PairRule.EITHER_DIRECTION: " (Appendix C.12's rule)"}


def rule_key(rule: PairRule) -> str:
    return rule.name.lower()


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------


def rule_series(readouts: Sequence[readout.ConcentrationReadout], rule: PairRule) -> dict[str, list[float]]:
    summaries = [point.pair_rules[rule] for point in readouts]
    return {
        "giant_share": [s.component.mean_share for s in summaries],
        "cycles_with_quorum": [s.component.cycles_with_quorum for s in summaries],
        "counting_share": [s.counting_share for s in summaries],
    }


def pair_rule_fields(run: ReadoutRun) -> dict[str, object]:
    return {
        LOSS_FIELD: {rule_key(rule): loss_under(run, rule) for rule in PairRule},
        HIGHEST_CONCENTRATION_FIELD: {rule_key(rule): giant_share_at_highest_concentration(run, rule) for rule in PairRule},
        COUNTING_AT_LOSS_FIELD: counting_share_at_primary_loss(run),
        "pair_rule_induction": {rule_key(rule): rule_series(run.induction, rule) for rule in PairRule},
        "pair_rule_emergence": {rule_key(rule): rule_series(run.emergence, rule) for rule in PairRule},
    }


def run_record(run: ReadoutRun) -> dict[str, object]:
    return readout_report.run_record(run) | pair_rule_fields(run)


def block_record(results: PairRuleResults) -> dict[str, object]:
    block = results.block
    return {
        "name": block.plan.name,
        "design": prespecified_runs.design_record(block.plan, block.design) | {"pass_share": PASS_RULE, "seeds": readout_report.seeds_used(block)},
        "tests": [asdict(o) | {"verdict": reliable_or_not(o)} for o in block.outcomes()],
        "runs": [run_record(run) for run in block.runs],
    }


def assemble_report(results: PairRuleResults) -> dict[str, object]:
    return {
        "label": results.block.design.label,
        "started_utc": results.started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), species.REPORTED_PACKAGES),
        "calibration": cal.as_record(),
        "readout": asdict(READOUT) | {"cycle_majority": float(readout.CYCLE_MAJORITY)},
        "pair_rules": {"primary": rule_key(PRIMARY_PAIR_RULE), "rules": {rule_key(rule): rule.value for rule in PairRule}},
        "pass_rule": PASS_RULE,
        "blocks": [block_record(results)],
    }


def every_evaluated_test_passes(report: dict[str, object]) -> bool:
    verdicts = [test["verdict"] for block in report["blocks"] for test in block["tests"]]
    return bool(verdicts) and all(verdict == PASSES for verdict in verdicts)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def by_rule(field: str, rule: PairRule) -> Callable[[dict[str, object]], object]:
    return lambda record: record[field][rule_key(rule)]


MEASUREMENTS: tuple[tuple[str, Callable[[dict[str, object]], object]], ...] = (
    *((f"DPC loss concentration, {rule.value}{RULE_SUFFIX[rule]}", by_rule(LOSS_FIELD, rule)) for rule in PairRule),
    ("Share of anatomical connections counting at the primary loss", itemgetter(COUNTING_AT_LOSS_FIELD)),
    *((f"Giant component at three times the EC50, {rule.value}", by_rule(HIGHEST_CONCENTRATION_FIELD, rule)) for rule in PairRule),
    ("Coherence-criterion loss concentration", itemgetter("loss_concentration")),
    ("Awake global coherence", lambda r: r["induction_coherence"][0]),
    ("Seconds per run", itemgetter("seconds")),
)


def measurement_rows(block: dict[str, object], organisms: Sequence[str]) -> list[list[str]]:
    conditions = list(dict.fromkeys(run["condition"] for run in block["runs"]))
    return [
        [label, condition, *[reporting.describe([value(r) for r in block["runs"] if r["organism"] == o and r["condition"] == condition]) for o in organisms]]
        for condition in conditions
        for label, value in MEASUREMENTS
    ]


def block_markdown(block: dict[str, object]) -> list[str]:
    organisms = [o for o in cal.ORGANISMS if any(run["organism"] == o for run in block["runs"])]
    return [
        readout_report.block_heading(block),
        "",
        *readout_report.outcome_lines(block["tests"], organisms),
        "",
        "Measurements (mean ± SD across seeds; concentrations relative to EC50; context, no verdict):",
        "",
        *reporting.markdown_table(["Quantity", "Condition", *[cal.ORGANISMS[o].display_name for o in organisms]], measurement_rows(block, organisms)),
        "",
    ]


def to_markdown(report: dict[str, object]) -> str:
    return "\n".join([
        *reporting.run_metadata_section(report, provenance.markdown_rows(report["provenance"])),
        f"Pass rule: {report['pass_rule']}.",
        f"Primary pair rule: {PRIMARY_PAIR_RULE.value}.",
        "",
        *[line for block in report["blocks"] for line in block_markdown(block)],
    ])
