"""What the pair-rule study reads from each run of the DPC readout under each pair rule."""

from __future__ import annotations

import dpc_readout as readout
from connection_pairs import PRIMARY_PAIR_RULE, PairRule
from readout_study.running import ReadoutRun


def loss_under(run: ReadoutRun, rule: PairRule) -> float | None:
    """Last concentration of induction with DPC quorum under the pair rule; None if never lost or never held."""
    return readout.pair_rule_loss_concentration(run.induction, rule)


def primary_loss(run: ReadoutRun) -> float | None:
    return loss_under(run, PRIMARY_PAIR_RULE)


def at_primary_loss(run: ReadoutRun) -> readout.ConcentrationReadout | None:
    """The readout at the last concentration of induction with quorum under the primary rule."""
    return run.readout_at(primary_loss(run))


def primary_counting_share(point: readout.ConcentrationReadout) -> float:
    """Share of the anatomical connections counting under the primary rule, averaged over the cycles held."""
    return point.pair_rules[PRIMARY_PAIR_RULE].counting_share


def counting_share_at_primary_loss(run: ReadoutRun) -> float | None:
    point = at_primary_loss(run)
    return None if point is None else primary_counting_share(point)


def giant_share_at_highest_concentration(run: ReadoutRun, rule: PairRule) -> float:
    """Mean giant-component share under the pair rule at the highest concentration of induction (three times the EC50)."""
    return run.induction[-1].pair_rules[rule].component.mean_share
