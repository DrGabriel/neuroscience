"""Diagnostic, post hoc, no verdict: does the stimulus reach the rest of the network through the shared reference
under ketamine-like faults on the sensory pathways (condition K1)? (20 October 2026)

With the agent's maximum of 40 ms of added jitter, connections leaving the sensory populations are fully
scrambled at high doses, yet the broadcast of the stimulus stays at about half of its awake value. The shared
phase reference couples every population to the mean field, which the stimulated sensory populations help form,
so it is a route that bypasses the connections. Three variants: the reference as in the study (must reproduce the
species report seed for seed), no reference, and a reference formed by the non-sensory populations only.

Usage: ../.venv/bin/python diagnostics/reference_leak.py
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, replace
from enum import StrEnum
from datetime import datetime, timezone

import numpy as np

from diagnostic_run import SIMULATOR, write_report

import calibration as cal  # noqa: E402
import phase_dynamics as dynamics  # noqa: E402
import provenance  # noqa: E402
import reporting  # noqa: E402
import species_study as study  # noqa: E402

ORGANISMS = ("celegans", "human")
SPECIES_REPORT = SIMULATOR / "results" / "species_full_20261020T103719Z.json"
COMPARED_FIELDS = ("deepest_coherence_fraction", "awake_broadcast_ratio", "deepest_broadcast_ratio")


class Variant(StrEnum):
    AS_IN_STUDY = "reference as in the study"
    NO_REFERENCE = "no reference (feedback 0)"
    CORE_REFERENCE = "reference formed by non-sensory populations only"

ORIGINAL_DRIVES_AT = dynamics.PhaseNetwork._drives_at


class CoreReferenceDrive:
    """The study's reference drive, with its strength and phase taken from the non-sensory populations' mean field."""

    def __init__(self, study_drive: dynamics.PhaseReferenceDrive, is_core: np.ndarray) -> None:
        self._study_drive = study_drive
        self._is_core = is_core

    def __call__(self, phases: np.ndarray, mean_field: complex, time: float) -> np.ndarray:
        return self._study_drive(phases, np.exp(1j * phases[self._is_core]).mean(), time)


def drives_with_core_reference(self: dynamics.PhaseNetwork, concentration: float) -> list[dynamics.PhaseDrive]:
    drives = ORIGINAL_DRIVES_AT(self, concentration)
    return [CoreReferenceDrive(drive, ~self._is_sensory) if isinstance(drive, dynamics.PhaseReferenceDrive) else drive for drive in drives]


@dataclass(frozen=True)
class LeakTask:
    variant: Variant
    organism: str
    seed: int


def design_for_variant(task: LeakTask, design: dynamics.SweepDesign) -> dynamics.SweepDesign:
    if task.variant is Variant.NO_REFERENCE:
        return replace(design, dynamics=replace(design.dynamics, reference_feedback=0.0))
    return design


def run_leak_task(task: LeakTask) -> tuple[LeakTask, dict[str, float | None]]:
    dynamics.PhaseNetwork._drives_at = drives_with_core_reference if task.variant is Variant.CORE_REFERENCE else ORIGINAL_DRIVES_AT
    condition = next(c for c in study.build_conditions(cal.FULL_INTEGRATION) if c.name == study.ConditionName.KETAMINE_PATHWAYS)
    run = study.RunTask(task.organism, condition, task.seed)
    summary = study.run_task(run, design_for_variant(task, study.design_for(run)))
    return task, {field: getattr(summary, field) for field in COMPARED_FIELDS}


def stored_values() -> dict[tuple[str, int], dict[str, float | None]]:
    runs = json.loads(SPECIES_REPORT.read_text())["runs"]
    return {(r["organism"], r["seed"]): {f: r[f] for f in COMPARED_FIELDS} for r in runs if r["condition"] == study.ConditionName.KETAMINE_PATHWAYS}


def largest_difference(found: dict[tuple[str, int], dict[str, float | None]], expected: dict[tuple[str, int], dict[str, float | None]]) -> float:
    return max(abs(found[key][field] - expected[key][field]) for key in found for field in COMPARED_FIELDS)


def summary_of(values: list[dict[str, float | None]]) -> dict[str, object]:
    shares = [v["deepest_broadcast_ratio"] / v["awake_broadcast_ratio"] for v in values]
    return {
        "median_broadcast_share_of_awake": float(np.median(shares)),
        "range_broadcast_share_of_awake": [float(min(shares)), float(max(shares))],
        "quorum_held": sum(v["deepest_coherence_fraction"] >= cal.QUORUM_FRACTION for v in values),
        "k1_holds": sum(study.disconnected_but_internally_coherent(types.SimpleNamespace(**v)) for v in values),
        "runs": len(values),
    }


def to_markdown(document: dict[str, object]) -> str:
    rows = [
        (variant, cal.ORGANISMS[organism].display_name, f"{s['median_broadcast_share_of_awake']:.0%}",
         f"{s['range_broadcast_share_of_awake'][0]:.0%}–{s['range_broadcast_share_of_awake'][1]:.0%}",
         f"{s['quorum_held']}/{s['runs']}", f"{s['k1_holds']}/{s['runs']}")
        for variant, by_organism in document["summaries"].items() for organism, s in by_organism.items()
    ]
    return "\n".join([
        "# K1 diagnostic: does the stimulus leak through the shared reference?",
        "",
        "Post hoc diagnostic, no verdict. Script: `simulator/diagnostics/reference_leak.py`.",
        "",
        *reporting.markdown_table(["Check", "Result"], [[name, str(value)] for name, value in document["checks"].items()]),
        "",
        *reporting.markdown_table(["Variant", "Connectome", "Broadcast at deepest dose, median share of awake", "Range", "Quorum held", "K1 holds"], rows),
        "",
    ])


def main() -> int:
    provenance.record_launch()
    started = datetime.now(timezone.utc)
    seeds = {o: [cal.BASE_SEED + i for i in range(cal.ORGANISMS[o].full_study_seeds)] for o in ORGANISMS}
    tasks = [LeakTask(variant, organism, seed) for variant in Variant for organism in ORGANISMS for seed in seeds[organism]]
    values: dict[str, dict[tuple[str, int], dict[str, float | None]]] = {variant: {} for variant in Variant}
    for task, result in reporting.run_in_parallel(run_leak_task, tasks, reporting.ParallelRun("diagnostic: reference leak")):
        values[task.variant][(task.organism, task.seed)] = result
    body = {
        "species_report": SPECIES_REPORT.name,
        "checks": {"largest difference from the species report, reference as in the study": largest_difference(values[Variant.AS_IN_STUDY], stored_values())},
        "summaries": {
            variant: {organism: summary_of([v for (o, _), v in values[variant].items() if o == organism]) for organism in ORGANISMS}
            for variant in Variant
        },
        "runs": {variant: [{"organism": o, "seed": s, **v} for (o, s), v in sorted(values[variant].items())] for variant in Variant},
    }
    write_report("reference_leak", started, body, to_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
