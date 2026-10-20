"""Exploratory, post hoc, no verdict: does the phase model show neural inertia at settings the calibration did not try?
(20 October 2026)

The calibration of the oscillator feedback (calibrate_phase_feedback.py) tried λ = 0, 0.3, 0.45, 0.6 and 0.75 on the
human connectome at the reference arousal level only. Every ratio stayed within run-to-run noise except one run at
0.75 that never recovered, so bistability, if present, appears abruptly between 0.6 and 0.75. This scan fills that
interval and adds arousal level 0, at which the reference depends on coherence alone, on the C. elegans connectome.
The GABAergic-like agent and every other setting are those of the species study.

Usage: ../.venv/bin/python diagnostics/phase_inertia_scan.py
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from diagnostic_run import write_report

import calibration as cal  # noqa: E402
import comparisons  # noqa: E402
import phase_dynamics as dynamics  # noqa: E402
import provenance  # noqa: E402
import reporting  # noqa: E402
import species_study as study  # noqa: E402

ORGANISM = "celegans"
SEEDS = tuple(cal.BASE_SEED + offset for offset in range(10))
FEEDBACK_VALUES = (cal.PHASE_REFERENCE_FEEDBACK, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725, 0.75)
AROUSAL_LEVELS = (0.0, cal.POPULATION_DYNAMICS.arousal_level)


@dataclass(frozen=True)
class ScanTask:
    arousal_level: float
    feedback: float
    seed: int


@dataclass(frozen=True)
class ScanResult:
    task: ScanTask
    loss_concentration: float | None
    recovery_concentration: float | None

    @property
    def ratio(self) -> float | None:
        return None if not self.loss_concentration or not self.recovery_concentration else self.loss_concentration / self.recovery_concentration


def run_scan_task(task: ScanTask) -> ScanResult:
    connectome = study.load_connectome(ORGANISM)
    condition = next(c for c in study.build_conditions(cal.FULL_INTEGRATION) if c.name == study.ConditionName.GABAERGIC)
    base = study.design_for(study.RunTask(ORGANISM, condition, task.seed))
    design = replace(base, dynamics=replace(base.dynamics, reference_feedback=task.feedback, arousal_level=task.arousal_level))
    record = dynamics.run_induction_emergence(connectome, design)
    return ScanResult(task, dynamics.loss_concentration(record), dynamics.recovery_concentration(record))


def cell_summary(results: list[ScanResult]) -> dict[str, object]:
    ratios = [r.ratio for r in results if r.ratio is not None]
    return {
        "mean_ratio": statistics.fmean(ratios) if ratios else None,
        "ratios_above_one_step": sum(
            comparisons.exceeds(r.loss_concentration - r.recovery_concentration, cal.CONCENTRATION_GRID.step) for r in results if r.ratio is not None
        ),
        "never_lost": sum(r.loss_concentration is None for r in results),
        "never_recovered": sum(r.loss_concentration is not None and r.recovery_concentration is None for r in results),
        "runs": len(results),
    }


def to_markdown(document: dict[str, object]) -> str:
    rows = [
        [f"{cell['arousal_level']:g}", f"{cell['feedback']:g}", "n/a" if cell["mean_ratio"] is None else f"{cell['mean_ratio']:.3f}",
         f"{cell['ratios_above_one_step']}/{cell['runs']}", f"{cell['never_recovered']}/{cell['runs']}", f"{cell['never_lost']}/{cell['runs']}"]
        for cell in document["cells"]
    ]
    return "\n".join([
        "# Exploratory scan: neural inertia in the phase model",
        "",
        f"Post hoc, exploratory, no verdict. *C. elegans* connectome, GABAergic-like agent, {len(SEEDS)} seeds per cell. "
        "Script: `simulator/diagnostics/phase_inertia_scan.py`.",
        "",
        *reporting.markdown_table(
            ["Arousal level", "Feedback λ", "Mean loss/recovery ratio", "Hysteresis wider than one step", "Never recovered", "Never lost"], rows
        ),
        "",
    ])


def main() -> int:
    provenance.record_launch()
    started = datetime.now(timezone.utc)
    tasks = [ScanTask(arousal, feedback, seed) for arousal in AROUSAL_LEVELS for feedback in FEEDBACK_VALUES for seed in SEEDS]
    results = reporting.run_in_parallel(run_scan_task, tasks, reporting.ParallelRun("diagnostic: phase inertia scan"))
    cells = [
        {"arousal_level": arousal, "feedback": feedback,
         **cell_summary([r for r in results if r.task.arousal_level == arousal and r.task.feedback == feedback])}
        for arousal in AROUSAL_LEVELS for feedback in FEEDBACK_VALUES
    ]
    body = {
        "design": {"organism": ORGANISM, "seeds": list(SEEDS), "feedback_values": list(FEEDBACK_VALUES), "arousal_levels": list(AROUSAL_LEVELS)},
        "cells": cells,
        "runs": [{"arousal_level": r.task.arousal_level, "feedback": r.task.feedback, "seed": r.task.seed,
                  "loss_concentration": r.loss_concentration, "recovery_concentration": r.recovery_concentration} for r in results],
    }
    write_report("phase_inertia_scan", started, body, to_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
