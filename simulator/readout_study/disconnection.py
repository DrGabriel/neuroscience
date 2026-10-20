"""K1d, K1e: sensory disconnection read with DPC quorum, with the control of as many randomly placed faults."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import calibration as cal
import comparisons
import disconnection_study
import prespecified_runs
import reporting
from readout_study.conditions import ConditionName
from readout_study.pass_rule import reliable_or_not
from readout_study.running import ReadoutRun

NOT_EVALUABLE = disconnection_study.NOT_EVALUABLE


@dataclass(frozen=True)
class ReadoutStimulusPair:
    """The same organism and seed with the stimulus applied and with the phantom."""

    applied: ReadoutRun
    phantom: ReadoutRun

    @property
    def floor(self) -> disconnection_study.StimulusPair:
        return disconnection_study.StimulusPair(self.applied.coherence, self.phantom.coherence)


def disconnected_with_dpc_quorum(pair: ReadoutStimulusPair) -> bool | None:
    """K1c's criterion with DPC quorum: quorum holds at the highest concentration while the broadcast above the floor
    falls to half its awake value or less. Undefined (None) for a seed whose awake broadcast does not clear the floor."""
    floor = pair.floor
    if not floor.has_awake_broadcast:
        return None
    keeps_quorum = pair.applied.induction[-1].holds_quorum
    return keeps_quorum and comparisons.at_most(floor.deepest_excess, cal.BROADCAST_COLLAPSE_FRACTION * floor.awake_excess)


@dataclass(frozen=True)
class PlacementControl:
    """The same seed with the timing error on the sensory pathways and on as many randomly chosen connections."""

    sensory: ReadoutStimulusPair
    random: ReadoutStimulusPair


def specific_to_sensory_pathways(control: PlacementControl) -> bool | None:
    """K1e: K1d holds with the error on the sensory pathways and not with it on as many random connections."""
    on_sensory, on_random = disconnected_with_dpc_quorum(control.sensory), disconnected_with_dpc_quorum(control.random)
    if on_sensory is None or on_random is None:
        return None
    return on_sensory and not on_random


K1D = reporting.Check("K1d", "Ketamine-like faults on the sensory pathways keep DPC quorum while the broadcast above the floor falls to half or less", disconnected_with_dpc_quorum)
K1E = reporting.Check("K1e", "Control: with as many random connections faulted, K1d does not hold, while it holds for the sensory pathways", specific_to_sensory_pathways)


def stimulus_pairs(runs: Sequence[ReadoutRun], applied: str, phantom: str) -> list[ReadoutStimulusPair]:
    by_key = {(r.organism, r.condition, r.seed): r for r in runs}
    return [
        ReadoutStimulusPair(run, by_key[(run.organism, phantom, run.seed)])
        for run in runs
        if run.condition == applied and (run.organism, phantom, run.seed) in by_key
    ]


def placement_controls(runs: Sequence[ReadoutRun]) -> list[PlacementControl]:
    random = {(p.applied.organism, p.applied.seed): p for p in stimulus_pairs(runs, ConditionName.RANDOM_APPLIED, ConditionName.RANDOM_PHANTOM)}
    sensory = stimulus_pairs(runs, ConditionName.SENSORY_APPLIED, ConditionName.SENSORY_PHANTOM)
    return [PlacementControl(p, random[(p.applied.organism, p.applied.seed)]) for p in sensory if (p.applied.organism, p.applied.seed) in random]


def evaluate_disconnection(runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    sensory = stimulus_pairs(runs, ConditionName.SENSORY_APPLIED, ConditionName.SENSORY_PHANTOM)
    controls = placement_controls(runs)
    names = {o: cal.ORGANISMS[o].display_name for o in organisms}
    return reporting.evaluate((K1D,), {names[o]: [p for p in sensory if p.applied.organism == o] for o in organisms}) + reporting.evaluate(
        (K1E,), {names[o]: [c for c in controls if c.sensory.applied.organism == o] for o in organisms}
    )


def disconnection_verdict(runs: Sequence[ReadoutRun]) -> prespecified_runs.Verdict:
    """As K1c: a test is judged only where at least half the organism's seeds are applicable."""
    def verdict(outcome: reporting.CheckOutcome) -> str:
        seeds = sum(r.condition == ConditionName.SENSORY_APPLIED and cal.ORGANISMS[r.organism].display_name == outcome.group for r in runs)
        evaluable = comparisons.at_least_share(outcome.runs_applicable, seeds, disconnection_study.MIN_EVALUABLE_SHARE)
        return reliable_or_not(outcome) if evaluable else NOT_EVALUABLE
    return verdict
