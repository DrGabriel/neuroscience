"""Calibrates the reference feedback λ of the phase-oscillator model against measured neural inertia.

The oscillator counterpart of calibrate_feedback.py, run on the human connectome. For each
candidate λ the mean loss-to-recovery concentration ratio across seeds is printed, so the
value matching the published target can be read off and its neighbourhood inspected.

Target: 1.11, propofol in humans (Iwakiri et al., 2005).
Usage: ../.venv/bin/python calibrate_phase_feedback.py [λ ...]
"""

from __future__ import annotations

import statistics
import sys
from dataclasses import replace
from datetime import datetime, timezone
from typing import Sequence

import calibration as cal
import connectomes
import phase_dynamics as dynamics
import provenance
import reporting

CALIBRATION_ORGANISM = "human"
CALIBRATION_SEEDS = tuple(cal.BASE_SEED + offset for offset in range(4))
DEFAULT_CANDIDATES = (0.0, 0.3, 0.45, 0.6, 0.75)


def inertia_ratio(feedback_and_seed: tuple[float, int]) -> tuple[float, float | None]:
    feedback, seed = feedback_and_seed
    connectome = connectomes.LOADERS[CALIBRATION_ORGANISM](cal.CONNECTOME_SEED)
    base = cal.base_sweep_design(cal.FULL_INTEGRATION, seed)
    design = replace(base, dynamics=replace(base.dynamics, reference_feedback=feedback))
    record = dynamics.run_induction_emergence(connectome, design)
    loss, recovery = dynamics.loss_concentration(record), dynamics.recovery_concentration(record)
    return feedback, None if not loss or not recovery else loss / recovery


def main(arguments: Sequence[str]) -> None:
    started = datetime.now(timezone.utc).isoformat()
    candidates = tuple(float(value) for value in arguments) or DEFAULT_CANDIDATES
    jobs = [(feedback, seed) for feedback in candidates for seed in CALIBRATION_SEEDS]
    results = reporting.run_in_parallel(inertia_ratio, jobs, reporting.ParallelRun("oscillator feedback calibration"))
    rows = []
    for feedback in candidates:
        ratios = [ratio for value, ratio in results if value == feedback]
        defined = [ratio for ratio in ratios if ratio is not None]
        mean = f"{statistics.fmean(defined):.3f}" if defined else "n/a"
        rows.append([f"{feedback:g}", mean, ", ".join("n/a" if r is None else f"{r:.3f}" for r in ratios)])
    document = {
        "label": "full",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), ("numpy", "scipy")),
        "design": {"organism": CALIBRATION_ORGANISM, "seeds": list(CALIBRATION_SEEDS), "target_ratio": cal.INERTIA_TARGET_RATIO},
        "ratios": [{"feedback": f, "ratio": r} for f, r in results],
    }
    markdown = "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"### Oscillator feedback λ against the inertia ratio ({CALIBRATION_ORGANISM} connectome, target {cal.INERTIA_TARGET_RATIO})",
        "",
        *reporting.markdown_table(["λ", "Mean ratio", "Ratio per seed"], rows),
        "",
    ])
    reporting.publish("calibration_phase_feedback", document, markdown)


if __name__ == "__main__":
    main(sys.argv[1:])
