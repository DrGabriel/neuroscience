"""T1d, T1e, T1f: fluctuations at the threshold, at matched coherence, over time and across network sizes."""

from __future__ import annotations

from typing import Sequence

import calibration as cal
import comparisons
import reporting
import species_study as species
from readout_study.conditions import ConditionName
from readout_study.running import ReadoutRun, RunPair, pairs_by_seed, runs_of
from readout_study.settings import MATCHED_COHERENCE_EXCESS, ORGANISMS_BY_SIZE


def threshold_excess(run: ReadoutRun) -> float | None:
    point = run.last_conscious
    return None if point is None else point.fluctuations.susceptibility_excess


def collective_fluctuations_at_threshold(run: ReadoutRun) -> bool:
    """T1d: at the last concentration with DPC quorum, fluctuations are at least twice those of independent phases."""
    excess = threshold_excess(run)
    return excess is not None and comparisons.at_most(MATCHED_COHERENCE_EXCESS, excess)


def slower_fluctuations_at_threshold(run: ReadoutRun) -> bool:
    """T1e: at the last concentration with DPC quorum, coherence is more autocorrelated than awake."""
    point, awake = run.last_conscious, run.induction[0].fluctuations.coherence_autocorrelation
    if point is None or awake is None or point.fluctuations.coherence_autocorrelation is None:
        return False
    return comparisons.exceeds(point.fluctuations.coherence_autocorrelation, awake)


FLUCTUATION_TESTS = (
    species.Pillar(
        "T1d", f"At the threshold, coherence fluctuates at least {MATCHED_COHERENCE_EXCESS:g} times as much as independent phases of the same mean coherence",
        ConditionName.GABAERGIC, collective_fluctuations_at_threshold,
    ),
    species.Pillar("T1e", "At the threshold, coherence is more autocorrelated over one cycle than awake", ConditionName.GABAERGIC, slower_fluctuations_at_threshold),
)


def excess_grows_with_size(pair: RunPair) -> bool:
    """T1f: the fluctuation excess at the threshold is larger on the larger connectome (first); undefined excess fails."""
    larger, smaller = threshold_excess(pair.first), threshold_excess(pair.second)
    return larger is not None and smaller is not None and comparisons.exceeds(larger, smaller)


T1F = reporting.Check("T1f", "The fluctuation excess at the threshold is larger than on the next smaller connectome, same seed", excess_grows_with_size)


def evaluate_size(runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    ladder = [o for o in ORGANISMS_BY_SIZE if o in organisms]
    groups = {
        cal.ORGANISMS[larger].display_name: pairs_by_seed(runs_of(runs, larger, ConditionName.GABAERGIC), runs_of(runs, smaller, ConditionName.GABAERGIC))
        for smaller, larger in zip(ladder, ladder[1:])
    }
    return [o for o in reporting.evaluate((T1F,), groups) if o.runs_applicable > 0]
