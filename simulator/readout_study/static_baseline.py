"""T0a-D, T0b-D: where the oscillator readout departs from static percolation on the same timing draws."""

from __future__ import annotations

import comparisons
import species_study as species
from readout_study.conditions import ConditionName
from readout_study.running import Reading, ReadoutRun


def dynamics_lower_the_loss(run: ReadoutRun) -> bool:
    """DPC quorum is lost at a lower concentration than static percolation on the same timing draws loses it (or the
    static reading never loses it): the populations' drift from the rhythm, not the draws alone, decides the loss."""
    loss, static_loss = run.dpc_loss_concentration, run.loss_under(Reading.JITTER_ONLY)
    if loss is None:
        return False
    return static_loss is None or comparisons.exceeds(static_loss, loss)


STATIC_TESTS = (
    species.Pillar("T0a-D", "GABAergic-like: DPC quorum is lost below the concentration at which static percolation on the same draws loses it", ConditionName.GABAERGIC, dynamics_lower_the_loss),
    species.Pillar("T0b-D", "NMDA-antagonist-like: DPC quorum is lost below the concentration at which static percolation on the same draws loses it", ConditionName.NMDA_ANTAGONIST, dynamics_lower_the_loss),
)
