"""Numerical convergence of the phase-oscillator results on the human connectome.

The species study integrates each concentration step for a fixed simulated time with a fixed
Euler-Maruyama step. This study repeats its GABAergic-like and sensory-stimulus conditions with
twice the simulated time, and with half the step over the same simulated time, and reports how
much the loss concentration and the broadcast ratios change. Results that move by much less
than their spread across seeds do not depend on the numerical settings.

Usage: ../.venv/bin/python convergence_study.py [--quick]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Callable, Sequence

import calibration as cal
import phase_dynamics as dynamics
import provenance
import reporting
import species_study
from species_study import ConditionName, RunSummary

ORGANISM = "human"
CONDITIONS = (ConditionName.GABAERGIC, ConditionName.SENSORY_STIMULUS)
FULL_SEEDS, QUICK_SEEDS = 5, 1
REPORTED_PACKAGES = ("numpy", "scipy")


def longer(settings: dynamics.IntegrationSettings) -> dynamics.IntegrationSettings:
    return replace(settings, relaxation_steps=2 * settings.relaxation_steps, measurement_steps=2 * settings.measurement_steps)


def finer(settings: dynamics.IntegrationSettings) -> dynamics.IntegrationSettings:
    """Half the step over the same simulated time."""
    return replace(
        settings, time_step=settings.time_step / 2, relaxation_steps=2 * settings.relaxation_steps, measurement_steps=2 * settings.measurement_steps
    )


VARIANTS: dict[str, Callable[[dynamics.IntegrationSettings], dynamics.IntegrationSettings]] = {
    "reference": lambda settings: settings,
    "twice the simulated time": longer,
    "half the time step": finer,
}


@dataclass(frozen=True)
class ConvergenceTask:
    variant: str
    condition: species_study.Condition
    seed: int


def run(task: ConvergenceTask) -> tuple[str, RunSummary]:
    return task.variant, species_study.run_task(species_study.RunTask(ORGANISM, task.condition, task.seed))


def tasks_for(seeds: int, integration: dynamics.IntegrationSettings) -> list[ConvergenceTask]:
    tasks = []
    for variant, change in VARIANTS.items():
        for condition in species_study.build_conditions(change(integration)):
            if condition.name in CONDITIONS:
                tasks.extend(ConvergenceTask(variant, condition, cal.BASE_SEED + index) for index in range(seeds))
    return tasks


QUANTITIES: tuple[tuple[str, str, str], ...] = (
    ("c_off", ConditionName.GABAERGIC, "loss_concentration"),
    ("Broadcast ratio, awake", ConditionName.SENSORY_STIMULUS, "awake_broadcast_ratio"),
    ("Broadcast ratio, first unconscious", ConditionName.SENSORY_STIMULUS, "unconscious_broadcast_ratio"),
)


def table(results: Sequence[tuple[str, RunSummary]]) -> list[str]:
    rows = [
        [label, *[reporting.describe([getattr(r, field) for v, r in results if v == variant and r.condition == condition]) for variant in VARIANTS]]
        for label, condition, field in QUANTITIES
    ]
    return reporting.markdown_table(["Quantity (mean ± SD across seeds)", *VARIANTS], rows)


def main(arguments: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true")
    quick = parser.parse_args(arguments).quick
    integration = cal.QUICK_INTEGRATION if quick else cal.FULL_INTEGRATION
    started = datetime.now(timezone.utc)
    live = reporting.ParallelRun("convergence", cal.ORGANISMS[ORGANISM].worker_processes, live_markdown=lambda done: "\n".join(table(done)))
    results = reporting.run_in_parallel(run, tasks_for(QUICK_SEEDS if quick else FULL_SEEDS, integration), live)
    document = {
        "label": "quick" if quick else "full",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES),
        "reference_integration": asdict(integration),
        "runs": [{"variant": variant, "run": asdict(summary)} for variant, summary in results],
    }
    markdown = "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"### Phase model on the {cal.ORGANISMS[ORGANISM].display_name} connectome: reference settings against longer and finer integration",
        "",
        *table(results),
        "",
    ])
    reporting.publish("convergence", document, markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
