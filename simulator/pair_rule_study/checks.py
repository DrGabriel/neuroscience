"""T2a-1, T2b-1 and SP1-1: C.12's agent tests and its percolation test, with one timing draw per anatomical connection."""

from __future__ import annotations

from typing import Sequence

import reporting
import species_study as species
from pair_rule_study.measures import at_primary_loss, primary_counting_share, primary_loss
from readout_study.conditions import ConditionName
from readout_study.running import PairedTest, ReadoutRun, RunPair, evaluate_paired
from readout_study.transitions import AGENTS, log_distance


def abolishes_quorum_under_primary_rule(run: ReadoutRun) -> bool:
    """Quorum, with one timing draw per anatomical connection, is lost within the concentration range; a seed in
    which it does not hold even at zero concentration counts as failing."""
    return primary_loss(run) is not None


AGENT_TESTS = (
    species.Pillar(
        "T2a-1", "GABAergic-like agent abolishes DPC quorum, one timing draw per anatomical connection",
        ConditionName.GABAERGIC, abolishes_quorum_under_primary_rule,
    ),
    species.Pillar(
        "T2b-1", "NMDA-antagonist-like agent abolishes DPC quorum, one timing draw per anatomical connection",
        ConditionName.NMDA_ANTAGONIST, abolishes_quorum_under_primary_rule,
    ),
)


def percolation_like_under_primary_rule(pair: RunPair) -> bool | None:
    """SP1-1: at their losses under the primary rule, the two agents leave more similar shares of counting anatomical
    connections than effective couplings (absolute log ratios). Undefined where either agent never loses quorum."""
    gabaergic, nmda = at_primary_loss(pair.first), at_primary_loss(pair.second)
    if gabaergic is None or nmda is None:
        return None
    counting = log_distance(primary_counting_share(gabaergic), primary_counting_share(nmda))
    return counting < log_distance(gabaergic.budget.effective_coupling, nmda.budget.effective_coupling)


TRANSITION_TESTS = (
    PairedTest(
        reporting.Check(
            "SP1-1",
            "At their losses the two agents leave a more similar share of counting anatomical connections than effective coupling (percolation)",
            percolation_like_under_primary_rule,
        ),
        *AGENTS,
    ),
)


def evaluate(runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    return species.evaluate(AGENT_TESTS, runs, organisms) + evaluate_paired(TRANSITION_TESTS, runs, organisms)
