"""The pair-rule study's one block: the two agents with the global reference, on fresh seeds."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import phase_dynamics as dynamics
import prespecified_runs
import species_study as species
from pair_rule_study.checks import evaluate
from pair_rule_study.settings import ORGANISMS, SEED_OFFSET, SEEDS
from readout_study.conditions import ConditionName, agent_designs
from readout_study.pass_rule import reliable_or_not
from readout_study.plans import BlockResult, StudyMode, run_block
from readout_study.running import run_readout_task


def agent_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    """C.12's two agent conditions with the global reference, every other parameter at its reference value."""
    gabaergic, nmda = agent_designs(integration)
    return (
        species.Condition(ConditionName.GABAERGIC, gabaergic, ORGANISMS),
        species.Condition(ConditionName.NMDA_ANTAGONIST, nmda, ORGANISMS),
    )


AGENT_PLAN = prespecified_runs.StudyPlan(
    name="dpc pair rule: agents", conditions=agent_conditions, organisms=ORGANISMS, seed_offset=SEED_OFFSET,
    full_seeds=SEEDS, outcomes=evaluate, work=run_readout_task, verdict=reliable_or_not,
)


@dataclass(frozen=True)
class PairRuleResults:
    started_utc: str
    block: BlockResult


def run_study(mode: StudyMode) -> PairRuleResults:
    """FULL: the pre-specified study. SMOKE: C. elegans only, one seed, two concentrations, shortest integration."""
    started = datetime.now(timezone.utc).isoformat()
    return PairRuleResults(started, run_block(AGENT_PLAN, mode))
