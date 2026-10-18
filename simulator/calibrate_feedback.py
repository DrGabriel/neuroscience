"""Calibrates the reference feedback λ of the percolation model, at each of several arousal levels.

Neural inertia is expressed as the ratio of the concentration at which responsiveness is
lost to the concentration at which it returns. For each arousal level, λ is found by
bisection so that the mean ratio across seeds matches each published ratio. A level is
usable only if every target is reproduced with every seed recovering at zero concentration.

The inertia ratios do not determine the arousal level: on the first run (2026-10-17) the
level 0 already reproduced every target. Arousal is therefore a free parameter, and the
studies report results across the levels listed here.

The published targets and their sources are listed in PUBLISHED_TARGETS below; the
concentrations they derive from are given in Section 2.2 of the paper.

Usage: python3 calibrate_feedback.py
Standard library only.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone

import dpc_simulator as dpc
import provenance
import reporting

CALIBRATION_NODE_COUNT = 10_000
CALIBRATION_SEEDS = tuple(dpc.REFERENCE_SEED + offset for offset in range(10))
AROUSAL_LEVELS = (0.0, 0.3, 0.5, 0.7)
LOWEST_FEEDBACK_MS = 0.0
HIGHEST_FEEDBACK_MS = 30.0
BISECTION_STEPS = 12
# A target is reproduced when the model's mean ratio lies within this distance of it.
RATIO_TOLERANCE = 0.01


@dataclass(frozen=True)
class InertiaTarget:
    ratio: float
    source: str


REFERENCE_TARGET = InertiaTarget(dpc.REFERENCE_INERTIA_RATIO, "Friedman et al. (2010), isoflurane, mice")
PUBLISHED_TARGETS = (
    InertiaTarget(1.07, "Warnaby et al. (2017), propofol, humans"),
    REFERENCE_TARGET,
    InertiaTarget(1.11, "Iwakiri et al. (2005), propofol, humans"),
    InertiaTarget(1.63, "Sepúlveda et al. (2018), propofol, humans"),
    InertiaTarget(2.85, "Friedman et al. (2010), halothane, mice"),
)

CALIBRATION_SCENARIO = replace(
    dpc.REFERENCE_SCENARIO,
    graph_builder=dpc.REFERENCE_SCENARIO.graph_builder.resized(CALIBRATION_NODE_COUNT),
)


@dataclass(frozen=True)
class Calibration:
    arousal_level: float
    feedback_ms: float
    model_ratio: float | None


def mean_inertia_ratio(feedback_ms: float, arousal_level: float) -> float | None:
    """Mean c_off / c_on across seeds; None if any seed never recovers."""
    ratios = []
    for seed in CALIBRATION_SEEDS:
        timing = replace(CALIBRATION_SCENARIO.timing, feedback_jitter_ms=feedback_ms)
        scenario = dpc.with_arousal(replace(CALIBRATION_SCENARIO, timing=timing, seed=seed), arousal_level)
        result = dpc.run_scenario(scenario)
        if result.loss_concentration is None or result.recovery_concentration is None:
            return None
        ratios.append(result.loss_concentration / result.recovery_concentration)
    return statistics.fmean(ratios)


def calibrate(target: InertiaTarget, arousal_level: float) -> Calibration:
    """Bisection on λ: the ratio rises with λ, and an unrecovered run counts as above any target."""
    low, high = LOWEST_FEEDBACK_MS, HIGHEST_FEEDBACK_MS
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2
        ratio = mean_inertia_ratio(middle, arousal_level)
        if ratio is not None and ratio < target.ratio:
            low = middle
        else:
            high = middle
    return Calibration(arousal_level, low, mean_inertia_ratio(low, arousal_level))


def reproduces(calibration: Calibration, target: InertiaTarget) -> bool:
    return calibration.model_ratio is not None and abs(calibration.model_ratio - target.ratio) <= RATIO_TOLERANCE


def main() -> None:
    started = datetime.now(timezone.utc).isoformat()
    rows, records = [], []
    total = len(AROUSAL_LEVELS) * len(PUBLISHED_TARGETS)
    for arousal_level in AROUSAL_LEVELS:
        for target in PUBLISHED_TARGETS:
            result = calibrate(target, arousal_level)
            elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(started)).total_seconds()
            reporting.report_progress("feedback calibration", len(records) + 1, total, elapsed)
            records.append({"target": asdict(target), "calibration": asdict(result), "reproduced": reproduces(result, target)})
            model_ratio = "n/a" if result.model_ratio is None else f"{result.model_ratio:.3f}"
            source = f"{target.source}{' (reference target)' if target is REFERENCE_TARGET else ''}"
            rows.append([f"{arousal_level:g}", f"{target.ratio:.2f}", f"{result.feedback_ms:.2f}", model_ratio, "yes" if reproduces(result, target) else "no", source])
    document = {
        "label": "full",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources()),
        "design": {"node_count": CALIBRATION_NODE_COUNT, "seeds": list(CALIBRATION_SEEDS), "grid_step": CALIBRATION_SCENARIO.grid.step},
        "calibrations": records,
    }
    markdown = "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"### Feedback λ calibrated to published inertia ratios (N = {CALIBRATION_NODE_COUNT:,}, {len(CALIBRATION_SEEDS)} seeds)",
        "",
        *reporting.markdown_table(["Arousal level", "Target ratio", "λ (ms)", "Model ratio", "Reproduced", "Source"], rows),
        "",
    ])
    reporting.publish("calibration_feedback", document, markdown)


if __name__ == "__main__":
    main()
