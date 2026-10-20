"""Diagnostic, post hoc, no verdict: how much of K1's remaining broadcast is real entrainment? (20 October 2026)

Broadcast is the locking of the non-sensory populations' mean phase to the stimulus, averaged over a window of two
stimulus cycles. Under ketamine-like faults on the sensory pathways (K1) those populations stay coherent, and a
coherent population rotating at its own frequency shows some locking to any rhythm over a short window, entrained or
not. Here the same runs are repeated with a phantom stimulus: same rhythm, zero strength, so nothing drives the
network but locking is measured exactly as before. Real entrainment should exceed phantom locking; spurious locking
should shrink with a longer window, which is run on C. elegans at four times the study's window.

Usage: ../.venv/bin/python diagnostics/phantom_stimulus.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum

import numpy as np

from diagnostic_run import SIMULATOR, write_report

import calibration as cal  # noqa: E402
import phase_dynamics as dynamics  # noqa: E402
import provenance  # noqa: E402
import reporting  # noqa: E402
import species_study as study  # noqa: E402

SPECIES_REPORT = SIMULATOR / "results" / "species_full_20261020T103719Z.json"
STUDY_WINDOW = 1
LONG_WINDOW = 4
WINDOWS_BY_ORGANISM = {"celegans": (STUDY_WINDOW, LONG_WINDOW), "human": (STUDY_WINDOW,)}
REPRODUCED_FIELDS = ("deepest_coherence_fraction", "deepest_broadcast_ratio")


class Stimulus(StrEnum):
    APPLIED = "applied"
    PHANTOM = "phantom (zero strength)"


@dataclass(frozen=True)
class PhantomTask:
    stimulus: Stimulus
    window_multiple: int
    organism: str
    seed: int


def design_for(task: PhantomTask) -> dynamics.SweepDesign:
    condition = next(c for c in study.build_conditions(cal.FULL_INTEGRATION) if c.name == study.ConditionName.KETAMINE_PATHWAYS)
    design = study.design_for(study.RunTask(task.organism, condition, task.seed))
    strength = design.stimulus.strength if task.stimulus is Stimulus.APPLIED else 0.0
    integration = replace(design.integration, measurement_steps=design.integration.measurement_steps * task.window_multiple)
    return replace(design, stimulus=replace(design.stimulus, strength=strength), integration=integration)


def locking(point: dynamics.StateMeasurement) -> dict[str, float | None]:
    return {"sensory": point.sensory_entrainment, "broadcast": point.broadcast_entrainment, "ratio": dynamics.broadcast_ratio(point)}


def run_phantom_task(task: PhantomTask) -> tuple[PhantomTask, dict[str, object]]:
    record = dynamics.run_induction_emergence(study.load_connectome(task.organism), design_for(task))
    deepest = record.induction[-1]
    return task, {
        "awake": locking(record.induction[0]),
        "deepest": locking(deepest),
        "deepest_coherence_fraction": deepest.global_coherence / record.awake_coherence,
    }


def reproduction_check(results: list[tuple[PhantomTask, dict[str, object]]]) -> float:
    """Largest difference from the species report for the applied stimulus with the study's window."""
    stored = {
        (r["organism"], r["seed"]): r
        for r in json.loads(SPECIES_REPORT.read_text())["runs"]
        if r["condition"] == study.ConditionName.KETAMINE_PATHWAYS
    }
    found = [
        (stored[(task.organism, task.seed)], {"deepest_coherence_fraction": v["deepest_coherence_fraction"], "deepest_broadcast_ratio": v["deepest"]["ratio"]})
        for task, v in results
        if task.stimulus is Stimulus.APPLIED and task.window_multiple == STUDY_WINDOW
    ]
    return max(abs(reference[field] - value[field]) for reference, value in found for field in REPRODUCED_FIELDS)


def median_of(values: list[float | None]) -> str:
    defined = [v for v in values if v is not None]
    return "n/a" if not defined else f"{np.median(defined):.3f}"


def summary_rows(results: list[tuple[PhantomTask, dict[str, object]]]) -> list[list[str]]:
    rows = []
    for organism, windows in WINDOWS_BY_ORGANISM.items():
        for window in windows:
            for stimulus in Stimulus:
                group = [v for t, v in results if (t.organism, t.window_multiple, t.stimulus) == (organism, window, stimulus)]
                rows.append([
                    cal.ORGANISMS[organism].display_name, f"{window}×", stimulus,
                    median_of([v["awake"]["broadcast"] for v in group]), median_of([v["deepest"]["broadcast"] for v in group]),
                    median_of([v["deepest"]["sensory"] for v in group]), str(len(group)),
                ])
    return rows


def to_markdown(document: dict[str, object]) -> str:
    return "\n".join([
        "# K1 diagnostic: real entrainment against locking to a phantom stimulus",
        "",
        "Post hoc diagnostic, no verdict. Script: `simulator/diagnostics/phantom_stimulus.py`. Medians across seeds of the "
        "locking value (0: none, 1: complete) of the non-sensory populations (broadcast) and of the sensory populations.",
        "",
        *reporting.markdown_table(["Check", "Result"], [[name, str(value)] for name, value in document["checks"].items()]),
        "",
        *reporting.markdown_table(
            ["Connectome", "Window (multiple of the study's)", "Stimulus", "Broadcast, awake", "Broadcast, deepest dose", "Sensory, deepest dose", "Seeds"],
            document["summary"],
        ),
        "",
    ])


def main() -> int:
    provenance.record_launch()
    started = datetime.now(timezone.utc)
    tasks = [
        PhantomTask(stimulus, window, organism, cal.BASE_SEED + index)
        for organism, windows in WINDOWS_BY_ORGANISM.items()
        for window in windows
        for stimulus in Stimulus
        for index in range(cal.ORGANISMS[organism].full_study_seeds)
    ]
    results = reporting.run_in_parallel(run_phantom_task, tasks, reporting.ParallelRun("diagnostic: phantom stimulus"))
    body = {
        "species_report": SPECIES_REPORT.name,
        "checks": {"largest difference from the species report, applied stimulus, study window": reproduction_check(results)},
        "summary": summary_rows(results),
        "runs": [{"stimulus": t.stimulus, "window_multiple": t.window_multiple, "organism": t.organism, "seed": t.seed, **v} for t, v in results],
    }
    write_report("phantom_stimulus", started, body, to_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
