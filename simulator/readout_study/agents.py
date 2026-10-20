"""T2a-D, T2b-D, their null model, the wired reference (W2a, W2b) and whether the wiring matters (WNa, WNb, GNa, GNb)."""

from __future__ import annotations

import comparisons
import reporting
import species_study as species
from readout_study.conditions import ConditionName
from readout_study.running import PairedTest, ReadoutRun, RunPair, concentration_step


def abolishes_dpc_quorum(run: ReadoutRun) -> bool:
    return run.dpc_loss_concentration is not None


AGENT_TESTS = (
    species.Pillar("T2a-D", "GABAergic-like agent abolishes DPC quorum within the concentration range", ConditionName.GABAERGIC, abolishes_dpc_quorum),
    species.Pillar("T2b-D", "NMDA-antagonist-like agent abolishes DPC quorum within the concentration range", ConditionName.NMDA_ANTAGONIST, abolishes_dpc_quorum),
    species.Pillar("T2a-DN", "Null model: on a rewired connectome, the GABAergic-like agent abolishes DPC quorum", ConditionName.GABAERGIC_REWIRED, abolishes_dpc_quorum),
    species.Pillar("T2b-DN", "Null model: on a rewired connectome, the NMDA-antagonist-like agent abolishes DPC quorum", ConditionName.NMDA_ANTAGONIST_REWIRED, abolishes_dpc_quorum),
    species.Pillar("W2a", "With the reference carried by the connections, the GABAergic-like agent abolishes DPC quorum", ConditionName.GABAERGIC_WIRED, abolishes_dpc_quorum),
    species.Pillar("W2b", "With the reference carried by the connections, the NMDA-antagonist-like agent abolishes DPC quorum", ConditionName.NMDA_ANTAGONIST_WIRED, abolishes_dpc_quorum),
)


def wiring_matters(pair: RunPair) -> bool:
    """The DPC loss on the connectome and on its rewired copy differ by more than one concentration step; a seed in
    which only one of them loses quorum counts as differing."""
    loss, null_loss = pair.first.dpc_loss_concentration, pair.second.dpc_loss_concentration
    if loss is None or null_loss is None:
        return (loss is None) != (null_loss is None)
    return comparisons.exceeds(abs(loss - null_loss), concentration_step(pair.first.organism))


def wiring_test(identifier: str, statement: str, conditions: tuple[str, str]) -> PairedTest:
    return PairedTest(reporting.Check(identifier, statement, wiring_matters), *conditions)


WIRING_TESTS = (
    wiring_test("WNa", "Reference carried by the connections: the GABAergic-like DPC loss differs from the rewired copy's by more than a step", (ConditionName.GABAERGIC_WIRED, ConditionName.GABAERGIC_WIRED_REWIRED)),
    wiring_test("WNb", "Reference carried by the connections: the NMDA-antagonist-like DPC loss differs from the rewired copy's by more than a step", (ConditionName.NMDA_ANTAGONIST_WIRED, ConditionName.NMDA_ANTAGONIST_WIRED_REWIRED)),
    wiring_test("GNa", "Global reference (comparison): the GABAergic-like DPC loss differs from the rewired copy's by more than a step", (ConditionName.GABAERGIC, ConditionName.GABAERGIC_REWIRED)),
    wiring_test("GNb", "Global reference (comparison): the NMDA-antagonist-like DPC loss differs from the rewired copy's by more than a step", (ConditionName.NMDA_ANTAGONIST, ConditionName.NMDA_ANTAGONIST_REWIRED)),
)
