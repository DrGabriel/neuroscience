"""SP1, SP2: is the loss a percolation transition (a common share of counting connections) or a synchronisation
transition (a common effective coupling)? The two agents of the same seed are compared at their losses."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import dpc_readout as readout
import reporting
from readout_study.conditions import ConditionName
from readout_study.running import PairedTest, ReadoutRun, RunPair


def log_distance(first: float, second: float) -> float:
    return abs(math.log(first / second)) if first > 0 and second > 0 else math.inf


@dataclass(frozen=True)
class LossBudgets:
    """What the two agents leave the network at their losses: counting share and effective coupling."""

    gabaergic: readout.ConcentrationReadout
    nmda: readout.ConcentrationReadout

    def counting_distance(self) -> float:
        return log_distance(self.gabaergic.counting_share, self.nmda.counting_share)

    def coupling_distance(self) -> float:
        return log_distance(self.gabaergic.budget.effective_coupling, self.nmda.budget.effective_coupling)


def budgets_at(pair: RunPair, loss_of: Callable[[ReadoutRun], float | None]) -> LossBudgets | None:
    gabaergic, nmda = pair.first.readout_at(loss_of(pair.first)), pair.second.readout_at(loss_of(pair.second))
    return None if gabaergic is None or nmda is None else LossBudgets(gabaergic, nmda)


def coherence_loss(run: ReadoutRun) -> float | None:
    return run.coherence.loss_concentration


def dpc_loss(run: ReadoutRun) -> float | None:
    return run.dpc_loss_concentration


def percolation_like(pair: RunPair) -> bool | None:
    """SP1: at their DPC losses the two agents leave more similar shares of counting connections than effective
    couplings (ratios compared on a log scale). Undefined where either agent never loses DPC quorum."""
    budgets = budgets_at(pair, dpc_loss)
    return None if budgets is None else budgets.counting_distance() < budgets.coupling_distance()


def synchronisation_like(pair: RunPair) -> bool | None:
    """SP2: at their coherence-criterion losses the two agents leave more similar effective couplings than shares of
    counting connections. Undefined where either agent never loses coherence quorum."""
    budgets = budgets_at(pair, coherence_loss)
    return None if budgets is None else budgets.coupling_distance() < budgets.counting_distance()


AGENTS = (ConditionName.GABAERGIC, ConditionName.NMDA_ANTAGONIST)
TRANSITION_TESTS = (
    PairedTest(reporting.Check("SP1", "At DPC loss the two agents leave a more similar share of counting connections than effective coupling (percolation)", percolation_like), *AGENTS),
    PairedTest(reporting.Check("SP2", "At coherence loss the two agents leave a more similar effective coupling than share of counting connections (synchronisation)", synchronisation_like), *AGENTS),
)
