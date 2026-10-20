"""Comparisons for verdicts on values derived from the concentration grid.

Concentrations are grid points stored as floats (1.4 is 1.4000000000000001), so differences of grid points such as
gains, shifts, widths and distances can differ in the last bits when they are equal: two one-step gains were stored as
0.09999999999999987 and 0.09999999999999998, and a plain ">" called the second larger. Every verdict that compares
such values uses these functions, so equal values count as equal. Shares of runs are compared in exact arithmetic.
"""

from __future__ import annotations

from fractions import Fraction

# Far below the finest grid step used anywhere (0.01) and far above floating-point rounding (about 1e-15).
TOLERANCE = 1e-9


def exceeds(value: float, reference: float) -> bool:
    """value is greater than reference by more than rounding."""
    return value > reference + TOLERANCE


def at_most(value: float, reference: float) -> bool:
    """value is less than or equal to reference, allowing for rounding."""
    return value <= reference + TOLERANCE


def equals(value: float, reference: float) -> bool:
    return abs(value - reference) <= TOLERANCE


def at_least_share(count: int, total: int, share: Fraction) -> bool:
    """count out of total reaches share, in exact arithmetic; never true when there is nothing to count."""
    return total > 0 and Fraction(count, total) >= share
