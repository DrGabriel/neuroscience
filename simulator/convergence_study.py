"""Numerical convergence of the phase-oscillator results on the human and Drosophila connectomes.

The species study integrates each concentration step for a fixed simulated time with a fixed
Euler-Maruyama step; Drosophila runs settle for fewer steps than the others (calibration.py).
This study repeats the GABAergic-like and sensory-stimulus conditions, starting from each
organism's own numerical settings, with twice the simulated time and with half the step over
the same simulated time, and reports how much the loss concentration and the broadcast ratios
change. Results that move by much less than their spread across seeds do not depend on the
numerical settings, and a hysteresis that survives twice the settling time is not an artefact
of changing the concentration too fast.

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

CONDITIONS = (ConditionName.GABAERGIC, ConditionName.SENSORY_STIMULUS)
# A Drosophila run takes about 25 minutes at the reference settings and twice that with either change.
FULL_SEEDS = {"human": 5, "drosophila": 2}
QUICK_SEEDS = {"human": 1}
REPORTED_PACKAGES = (*provenance.NUMERICAL_PACKAGES, "pyarrow")


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
    organism: str
    variant: str
    condition: species_study.Condition
    seed: int


@dataclass(frozen=True)
class ConvergenceRun:
    organism: str
    variant: str
    summary: RunSummary


def variant_design(task: ConvergenceTask) -> dynamics.SweepDesign:
    """The organism's own design, then the variant's change to its integration, so that no setting is capped back."""
    design = species_study.design_for(species_study.RunTask(task.organism, task.condition, task.seed))
    return replace(design, integration=VARIANTS[task.variant](design.integration))


def run(task: ConvergenceTask) -> ConvergenceRun:
    base = species_study.RunTask(task.organism, task.condition, task.seed)
    return ConvergenceRun(task.organism, task.variant, species_study.run_task(base, variant_design(task)))


def tasks_for(seeds: dict[str, int], integration: dynamics.IntegrationSettings) -> list[ConvergenceTask]:
    conditions = [c for c in species_study.build_conditions(integration) if c.name in CONDITIONS]
    return [
        ConvergenceTask(organism, variant, condition, cal.BASE_SEED + index)
        for organism, count in seeds.items()
        for variant in VARIANTS
        for condition in conditions
        for index in range(count)
    ]


QUANTITIES: tuple[tuple[str, str, str], ...] = (
    ("c_off", ConditionName.GABAERGIC, "loss_concentration"),
    ("Broadcast ratio, awake", ConditionName.SENSORY_STIMULUS, "awake_broadcast_ratio"),
    ("Broadcast ratio, first unconscious", ConditionName.SENSORY_STIMULUS, "unconscious_broadcast_ratio"),
    ("Hysteresis (c_off - c_on)", ConditionName.GABAERGIC, "hysteresis_width"),
)


def table(runs: Sequence[ConvergenceRun], organism: str) -> list[str]:
    def values(variant: str, condition: str, field: str) -> list[float | None]:
        return [getattr(r.summary, field) for r in runs if r.organism == organism and r.variant == variant and r.summary.condition == condition]

    rows = [[label, *[reporting.describe(values(variant, condition, field)) for variant in VARIANTS]] for label, condition, field in QUANTITIES]
    return reporting.markdown_table(["Quantity (mean ± SD across seeds)", *VARIANTS], rows)


def tables(runs: Sequence[ConvergenceRun], organisms: Sequence[str]) -> list[str]:
    lines = []
    for organism in organisms:
        lines += [f"### Phase model on the {cal.ORGANISMS[organism].display_name} connectome: reference settings against longer and finer integration", "", *table(runs, organism), ""]
    return lines


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true")
    quick = parser.parse_args(arguments).quick
    integration = cal.QUICK_INTEGRATION if quick else cal.FULL_INTEGRATION
    seeds = QUICK_SEEDS if quick else FULL_SEEDS
    started = datetime.now(timezone.utc)
    tasks = tasks_for(seeds, integration)
    runs: list[ConvergenceRun] = []
    for organism in seeds:
        live = reporting.ParallelRun(f"convergence: {cal.ORGANISMS[organism].display_name}", cal.ORGANISMS[organism].worker_processes, live_markdown=lambda done, o=organism: "\n".join(table(done, o)))
        runs.extend(reporting.run_in_parallel(run, [t for t in tasks if t.organism == organism], live))
    document = {
        "label": reporting.RunLabel.QUICK if quick else reporting.RunLabel.FULL,
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES),
        "reference_integration": asdict(integration),
        "seeds": seeds,
        "runs": [{"organism": r.organism, "variant": r.variant, "run": asdict(r.summary)} for r in runs],
    }
    markdown = "\n".join([*reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])), *tables(runs, list(seeds))])
    reporting.publish("convergence", document, markdown)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
