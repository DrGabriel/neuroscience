"""Diagnostic, post hoc, no verdict: what can a Wilson-Cowan region do once quorum is lost? (20 October 2026)

P6 proposes that, when quorum is lost, cortex falls into its own locally generated dynamics, such as the slow
oscillation. In the congestion model each region's inhibition is balanced in the awake state, while it receives
long-range excitation. This diagnostic balances the awake state exactly as the congestion study does, for each global
coupling and seed, then removes the long-range input and finds every region's resting states and their stability.
Up and down states need two states to alternate between; a single unstable state makes the region oscillate
around it instead.

Usage: ../.venv/bin/python diagnostics/deafferented_states.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, replace
from datetime import datetime, timezone

import numpy as np

from diagnostic_run import write_report

import congestion_study as congestion  # noqa: E402
import excitatory_inhibitory as ei  # noqa: E402
import provenance  # noqa: E402
import reporting  # noqa: E402


@dataclass(frozen=True)
class BalancingTask:
    global_coupling: float
    seed: int


def deafferented_states(task: BalancingTask) -> dict[str, object]:
    design = replace(congestion.FULL_DESIGN, global_coupling=task.global_coupling, seed=task.seed)
    network = ei.WilsonCowanNetwork(congestion.human_connectome(), design)
    network.balance_awake_state()
    couplings = network.inhibitory_coupling
    states = [ei.resting_states(design.circuit, float(w), design.circuit.constant_input) for w in couplings]
    single = [s[0] for s in states if len(s) == 1]
    unstable = [s for s in single if not s.stable]
    return {
        "global_coupling": task.global_coupling,
        "seed": task.seed,
        "regions": len(states),
        "median_inhibitory_coupling": float(np.median(couplings)),
        "regions_with_one_resting_state": len(single),
        "regions_resting_stably": len(single) - len(unstable),
        "regions_oscillating": len(unstable),
        "oscillation_hz": [s.oscillation_hz for s in unstable],
        "highest_resting_activity": max(s.excitatory_activity for region in states for s in region),
    }


def group_summary(runs: list[dict[str, object]]) -> list[str]:
    frequencies = [f for r in runs for f in r["oscillation_hz"]]
    return [
        f"{runs[0]['global_coupling']:g}",
        f"{len(runs)}",
        f"{min(r['regions_with_one_resting_state'] for r in runs)}–{max(r['regions_with_one_resting_state'] for r in runs)} of {runs[0]['regions']}",
        f"{min(r['regions_resting_stably'] for r in runs)}–{max(r['regions_resting_stably'] for r in runs)}",
        f"{min(r['regions_oscillating'] for r in runs)}–{max(r['regions_oscillating'] for r in runs)}",
        "none" if not frequencies else f"{min(frequencies):.0f}–{max(frequencies):.0f} Hz",
        f"{max(r['highest_resting_activity'] for r in runs):.3f}",
        f"{np.median([r['median_inhibitory_coupling'] for r in runs]):.2f}",
    ]


def to_markdown(document: dict[str, object]) -> str:
    rows = [group_summary([r for r in document["runs"] if r["global_coupling"] == coupling]) for coupling in congestion.GLOBAL_COUPLINGS]
    return "\n".join([
        "# What a Wilson-Cowan region can do once long-range input is gone",
        "",
        "Post hoc diagnostic, no verdict. Awake state balanced as in the congestion study, then long-range input removed. "
        "Script: `simulator/diagnostics/deafferented_states.py`.",
        "",
        *reporting.markdown_table(
            ["Global coupling", "Seeds", "Regions with one resting state", "Resting stably", "Oscillating instead",
             "Oscillation frequency", "Highest resting activity", "Median inhibitory weight"],
            rows,
        ),
        "",
    ])


def main() -> int:
    provenance.record_launch()
    started = datetime.now(timezone.utc)
    seeds = [congestion.FULL_DESIGN.seed + index for index in range(congestion.FULL_SEEDS)]
    tasks = [BalancingTask(coupling, seed) for coupling in congestion.GLOBAL_COUPLINGS for seed in seeds]
    runs = reporting.run_in_parallel(deafferented_states, tasks, reporting.ParallelRun("diagnostic: deafferented states"))
    write_report("deafferented_states", started, {"runs": runs}, to_markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
