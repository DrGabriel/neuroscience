"""Seed blocks of the round-three analyses and of every earlier study, so that disjointness can be checked.

A block is a run of consecutive offsets from the base seed (calibration.BASE_SEED, the same value as
dpc_simulator.REFERENCE_SEED). Earlier studies used offsets 0 to 19 (validation, sensitivity, species, convergence,
calibrations, percolation thresholds, diagnostics), 1000 (congestion confirmatory), 2000, 3000 and 4000 (pre-specified
studies), 5000, 5500 and 5600 (Appendix C.12) and 6000 (Appendix C.13). While the round-three code was checked, smoke
runs used the base seed plus 7000, 7200, 7201 and 7500, whose outcomes were therefore seen; no analysis uses them. The
analyses use 7100, 7300 and 7600, which no run has used, and every smoke run now uses 7900 and 7901.
"""

from __future__ import annotations

from dataclasses import dataclass

import calibration as cal


@dataclass(frozen=True)
class SeedBlock:
    """Seeds base seed + offset to base seed + offset + count - 1."""

    name: str
    offset: int
    count: int

    def seeds(self) -> range:
        return range(cal.BASE_SEED + self.offset, cal.BASE_SEED + self.offset + self.count)

    def overlaps(self, other: SeedBlock) -> bool:
        mine, theirs = self.seeds(), other.seeds()
        return mine.start < theirs.stop and theirs.start < mine.stop


# The largest block any earlier study drew from each offset: 20 seeds per organism or network size.
EARLIER_BLOCK_SIZE = 20
EARLIER_BLOCKS = tuple(
    SeedBlock(name, offset, EARLIER_BLOCK_SIZE)
    for name, offset in (
        ("validation (B.4), calibration (B.3) and the other first studies", 0),
        ("congestion, confirmatory (C.6)", 1000),
        ("pre-specified tests (C.7)", 2000),
        ("learned arrival times (C.10)", 3000),
        ("sensory disconnection (C.11)", 4000),
        ("DPC readout tests (C.12)", 5000),
        ("DPC readout calibrations (C.12)", 5500),
        ("weaker-coupling calibration (C.12)", 5600),
        ("pair rule (C.13)", 6000),
    )
)

# Seeds whose outcomes were seen in smoke runs while the code was checked, before smoke runs had a block of their own.
SEEN_WHILE_CHECKING = (
    SeedBlock("smoke run of A, first seed at 302 nodes", 7000, 1),
    SeedBlock("smoke run of C, both generators", 7200, 2),
    SeedBlock("smoke run of D, first seed at 302 nodes", 7500, 1),
)

# Analysis A: as many seeds per network size as Appendix B.4.
PULSE_BLOCK = SeedBlock("prediction 15 (A)", 7100, 20)
# Analysis C: one generator for the reciprocity sweep and one for the timing-error sweep.
RECIPROCITY_BLOCK = SeedBlock("reciprocity and timing-error estimates (C)", 7300, 2)
# Analysis D: as many seeds per network size as Appendix B.4.
FRESH_VALIDATION_BLOCK = SeedBlock("validation on fresh seeds (D)", 7600, 20)
ROUND_THREE_BLOCKS = (PULSE_BLOCK, RECIPROCITY_BLOCK, FRESH_VALIDATION_BLOCK)
# Every smoke run: one seed for A and D, and one generator per sweep for C. Never part of a result.
SMOKE_BLOCK = SeedBlock("smoke runs of A, C and D", 7900, 2)
