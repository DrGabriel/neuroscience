"""Choosing a value for one organism on calibration seeds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Calibrated:
    """A value chosen for one organism on calibration seeds, with the quantity that chose it; value None if none qualified."""

    organism: str
    value: float | None
    achieved: float | None


def closest(organism: str, candidates: Sequence[tuple[float, float]], target: float) -> Calibrated:
    """The candidate (value, achieved) whose achieved quantity lies closest to the target."""
    if not candidates:
        return Calibrated(organism, None, None)
    value, achieved = min(candidates, key=lambda candidate: abs(candidate[1] - target))
    return Calibrated(organism, value, achieved)
