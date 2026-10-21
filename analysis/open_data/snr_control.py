"""H5a with a signal-to-noise control (round 3, exploratory; Appendix E.15): per-patient runs, simulation, group step.

Per patient, the committed H5a analysis runs unchanged (same connections, same equalised trials, same seed, with
deviation D4 for the patient with two awake runs), and each connection also gets the SNR control of snr_matching.py.
The group step reports, without verdict and with the H5a test (one-sided Wilcoxon over patients, SESOI log 1.2): the
H5a statistic as run, the SNR-matched statistic, and the statistic restricted to connections whose propofol SNR is at
least the awake SNR divided by the restriction ratio; and, from the simulation, the r that the observed change in SNR
alone would produce.

Usage, from the repository root:
    .venv/bin/python -E -s -m analysis.open_data.snr_control prios --session-dir <ds004370/sub-*/ses-1> --out <folder>
    .venv/bin/python -E -s -m analysis.open_data.snr_control simulate --out <simulation.json>
    .venv/bin/python -E -s -m analysis.open_data.snr_control group --inputs <folder> --simulation <simulation.json> --out <json>
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path

import numpy as np

from . import deviations, group, outputs, pipeline_prios, run, snr_matching, snr_simulation
from .constants import Dataset, Hypothesis
from .outputs import Output
from .pipeline_prios import PROPOFOL, PriosSession
from .round3_settings import SNR
from .settings import EVOKED, SEED

AWAKE = snr_matching.AWAKE
RESULT_FIELD = f"{Hypothesis.H5a}_snr_control"
NO_VERDICT = "reported without verdict"
GROUP_FIELDS = {
    "as_run": "median_relative_change",
    "snr_matched": "median_matched_relative_change",
    "snr_restricted": "median_restricted_relative_change",
}


def _median(values: list) -> float | None:
    kept = [v for v in values if v is not None]
    return float(np.median(kept)) if kept else None


def restricted(rows: list[dict]) -> list[dict]:
    """Connections whose propofol SNR is at least the awake SNR divided by the restriction ratio."""
    return [r for r in rows if r["log_snr_ratio"] >= -np.log(SNR.restriction_ratio)]


def patient_summary(rows: list[dict]) -> dict:
    kept = restricted(rows)
    return {
        "median_matched_relative_change": _median([r["matched_relative_change"] for r in rows]),
        "median_restricted_relative_change": _median([r["relative_change"] for r in kept]),
        "restricted_connections": len(kept),
        "median_log_snr_ratio": _median([r["log_snr_ratio"] for r in rows]),
        "median_matched_snr": _median([min(r["snr"][s]["snr"] for s in snr_matching.STATES) for r in rows]),
        "median_snr": {s: _median([r["snr"][s]["snr"] for r in rows]) for s in snr_matching.STATES},
    }


def subject_snr_control(session: PriosSession, rng: np.random.Generator) -> dict:
    """The committed subject_changes() with each connection compared by matched_connection(), then restored."""
    committed = pipeline_prios.compare_connection
    pipeline_prios.compare_connection = snr_matching.matched_connection
    try:
        result = pipeline_prios.subject_changes(session, rng)
    finally:
        pipeline_prios.compare_connection = committed
    return {**result, **patient_summary(result["connections"])}


def _test(values: list) -> dict:
    kept = [v for v in values if v is not None]
    return dataclasses.asdict(group.one_sample_summary(np.array(kept), EVOKED.smallest_log_ratio)) if kept else {"n": 0}


def group_median(patients: list[dict], field: str) -> float | None:
    return _median([p[field] for p in patients])


def group_summary(patients: list[dict], simulation: dict | None) -> dict:
    snr_pair = tuple(_median([p["median_snr"][s] for p in patients]) for s in snr_matching.STATES)
    out = {
        "verdict": NO_VERDICT,
        "tests": {name: _test([p[field] for p in patients]) for name, field in GROUP_FIELDS.items()},
        "median_log_snr_ratio": group_median(patients, "median_log_snr_ratio"),
        "group_median_snr": dict(zip(snr_matching.STATES, snr_pair, strict=True)),
    }
    if simulation is not None and None not in snr_pair:
        out.update(simulation_readings(simulation["cells"], snr_pair, group_median(patients, "median_matched_snr")))
    return out


def simulation_readings(cells: list[dict], snr_pair: tuple, matched_snr: float) -> dict:
    """The simulation read at the data's group median SNRs: r from the SNR change alone, and the matched sensitivity."""
    return {"snr_only_relative_change": snr_simulation.snr_only_change(cells, snr_pair), "matched_sensitivity": matched_sensitivity(cells, matched_snr)}


def matched_sensitivity(cells: list[dict], matched_snr: float) -> dict:
    """Can the matched comparison see a true jitter at the matched SNR? Simulated spread of a 2 ms jitter at 10 trials."""
    jitter, trials = SNR.sensitivity_jitter_ms, SNR.sensitivity_trials
    spreads = {c: snr_simulation.spread_at(cells, (c, jitter, trials), matched_snr) for c in SNR.colours}
    floor = SNR.sensitivity_floor_share * jitter
    informative = all(s is not None and s >= floor for s in spreads.values())
    return {"matched_snr": matched_snr, "simulated_spread_ms": spreads, "floor_ms": floor, "informative": informative}


def prios_command(arguments: argparse.Namespace) -> None:
    deviations.apply_deviations()
    started, session_dir = time.time(), Path(arguments.session_dir)
    session = run.prios_session(session_dir)
    result = run.attempt(subject_snr_control, session, np.random.default_rng(SEED))
    runs = {run.AWAKE_TASK: session.awake_stem, run.PROPOFOL_TASK: session.propofol_stem}
    outputs.write(Output(Path(arguments.out) / f"{Dataset.PRIOS}_{session_dir.parent.name}.json", arguments, started), {"runs": runs, RESULT_FIELD: result})


def simulate_command(arguments: argparse.Namespace) -> None:
    started, spec = time.time(), dataclasses.replace(SNR, connections=arguments.connections)
    rng = np.random.default_rng(SEED)
    cells = snr_simulation.simulate(spec, rng)
    payload = {
        "settings_round3": dataclasses.asdict(spec),
        "cells": cells,
        "amplitude_drop": snr_simulation.amplitude_drop_table(cells),
        "null_check": snr_simulation.null_check(spec, rng),
    }
    outputs.write(Output(Path(arguments.out), arguments, started), payload)


def group_command(arguments: argparse.Namespace) -> None:
    started = time.time()
    patients = outputs.included([r[RESULT_FIELD] for r in run.load_all(Path(arguments.inputs), Dataset.PRIOS)])
    simulation = json.loads(Path(arguments.simulation).read_text()) if arguments.simulation else None
    payload = {"patients": len(patients), "secondary_H5a_snr_control": group_summary(patients, simulation)}
    outputs.write(Output(Path(arguments.out), arguments, started), payload)


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = top.add_subparsers(required=True)
    p = commands.add_parser(Dataset.PRIOS, help="H5a and its SNR control for one PRIOS patient")
    p.add_argument("--session-dir", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(handler=prios_command)
    s = commands.add_parser("simulate", help="latency spread against SNR on synthetic responses, and the null check")
    s.add_argument("--out", required=True)
    s.add_argument("--connections", type=int, default=SNR.connections)
    s.set_defaults(handler=simulate_command)
    g = commands.add_parser("group", help="the three H5a statistics over patients, without verdict")
    g.add_argument("--inputs", required=True)
    g.add_argument("--simulation")
    g.add_argument("--out", required=True)
    g.set_defaults(handler=group_command)
    return top


def main(argv: list[str] | None = None) -> None:
    arguments = parser().parse_args(argv)
    arguments.handler(arguments)


if __name__ == "__main__":
    main()
