"""Where a swept curve first falls below a level, by linear interpolation between the two grid points around it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SweptPoint:
    """One value of the swept parameter and the mean giant-component share there."""

    parameter: float
    giant_share: float


def first_fall_below(points: Sequence[SweptPoint], level: float) -> float | None:
    """The parameter at which the curve, read in the given order, first falls below the level.

    Interpolated linearly between the last point at or above the level and the first point below it. None when the
    curve starts below the level or never falls below it.
    """
    for earlier, later in zip(points, points[1:]):
        if earlier.giant_share >= level > later.giant_share:
            share_drop = earlier.giant_share - later.giant_share
            fraction = (earlier.giant_share - level) / share_drop
            return earlier.parameter + fraction * (later.parameter - earlier.parameter)
        if earlier.giant_share < level:
            return None
    return None
