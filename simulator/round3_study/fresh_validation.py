"""Analysis D: the validation study of Appendix B.4, unchanged, on seeds that neither calibration nor B.4 used, with the
model's loss-to-recovery concentration ratio at every network size.

Standard library only.
"""

from __future__ import annotations

from typing import Sequence

import reporting
import validation_study as validation

# The range of published inertia ratios that the feedback was calibrated across (Appendix B.3), for context only.
PUBLISHED_RATIO_RANGE = (1.07, 1.63)


def inertia_ratio(measurement: validation.SeedMeasurement) -> float | None:
    """c_off / c_on of the reference sweep; None when quorum is never lost or never regained."""
    reference = measurement.reference
    if reference.loss_concentration is None or reference.recovery_concentration is None:
        return None
    return reference.loss_concentration / reference.recovery_concentration


def within_published_range(measurement: validation.SeedMeasurement) -> bool:
    ratio = inertia_ratio(measurement)
    low, high = PUBLISHED_RATIO_RANGE
    return ratio is not None and low <= ratio <= high


RATIO_OBSERVATION = reporting.Check(
    "R1", f"The loss-to-recovery ratio lies within the published range {PUBLISHED_RATIO_RANGE[0]} to {PUBLISHED_RATIO_RANGE[1]}",
    within_published_range,
)


def ratio_statistics(measurements: Sequence[validation.SeedMeasurement], node_counts: Sequence[int]) -> dict[int, reporting.Distribution]:
    return {n: reporting.Distribution.of([inertia_ratio(m) for m in measurements if m.node_count == n]) for n in node_counts}


def ratio_markdown(measurements: Sequence[validation.SeedMeasurement], node_counts: Sequence[int]) -> list[str]:
    sizes = [validation.size_label(n) for n in node_counts]
    statistics = ratio_statistics(measurements, node_counts)
    return [
        "### Loss-to-recovery concentration ratio c_off / c_on, GABAergic-like agent (no verdict)",
        "",
        *reporting.markdown_table(["Quantity", *sizes], [["c_off / c_on, mean ± SD", *[statistics[n].describe() for n in node_counts]]]),
        "",
        *reporting.outcome_table(validation.evaluate_claims([RATIO_OBSERVATION], measurements, node_counts), sizes),
        "",
    ]
