"""The pre-specified pair-rule study (pair_rule_study package, Appendix C.13): seeds, conditions, the smoke mode,
the verdicts of T2a-1, T2b-1 and SP1-1, and the report.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest
from dataclasses import dataclass, replace

import calibration as cal
import congestion_study
import disconnection_study
import dpc_pair_rule_study
import dpc_readout as readout
import learned_timing_study
import phase_dynamics as dynamics
import prespecified_runs
import prespecified_study
from connection_pairs import PRIMARY_PAIR_RULE, PairRule
from pair_rule_study import checks, measures, plan, report, settings
from readout_study import plans as readout_plans
from readout_study import running
from readout_study import settings as readout_settings
from readout_study.conditions import ConditionName
from readout_study.plans import StudyMode
from tests.test_dpc_readout_study import BUDGET, NO_FLUCTUATIONS
from tests.test_prespecified_study import run as coherence_run

GRID = [round(0.05 * index, 2) for index in range(61)]
QUORUM, NO_QUORUM = 0.9, 0.1
CYCLES = 4
EARLIER_OFFSETS_AND_SEEDS = (
    (congestion_study.CONFIRMATORY_SEED_OFFSET, 20),
    (prespecified_study.SEED_OFFSET, 20),
    (learned_timing_study.SEED_OFFSET, 20),
    (disconnection_study.SEED_OFFSET, 20),
    (readout_settings.SEED_OFFSET, readout_settings.PERCOLATION_HELD_OUT_SEEDS),
    (readout_settings.CALIBRATION_SEED_OFFSET, readout_settings.PERCOLATION_CALIBRATION_SEEDS),
    (readout_settings.COUPLING_CALIBRATION_SEED_OFFSET, max(readout_settings.COUPLING_CALIBRATION_SEEDS.values())),
)
FIRST_BLOCK_SEEDS = 20
C12_SEEDS = {"celegans": 20, "human": 20, "drosophila": 6}
EARLY_LOSS, LATE_LOSS, HIGHEST_CONCENTRATION = 1.5, 2.0, 3.0
COUNTING = 0.3
SIMILAR_SHARES, DIFFERENT_SHARES = (0.2, 0.21), (0.1, 0.3)
COUPLINGS_APART, COUPLINGS_CLOSE = (1.0, 2.0), (1.0, 1.01)
NEVER_HELD = -1.0


@dataclass(frozen=True)
class SketchedRun:
    """Where a hand-built run loses quorum under the primary rule (and both directions) and under either direction."""

    primary_loss: float | None
    either_loss: float | None = HIGHEST_CONCENTRATION
    counting: float = COUNTING


def rule_summary(quorum: bool, counting: float) -> readout.PairRuleSummary:
    component = readout.ComponentSummary(QUORUM if quorum else NO_QUORUM, CYCLES if quorum else 0, CYCLES)
    return readout.PairRuleSummary(component, counting)


def point(concentration: float, quorum_until: dict[PairRule, float | None], counting: float) -> readout.ConcentrationReadout:
    """A concentration at which each pair rule holds quorum up to its own loss; C.12's reading follows either direction."""
    holds = {rule: until is not None and concentration <= until for rule, until in quorum_until.items()}
    rules = {rule: rule_summary(holds[rule], counting) for rule in PairRule}
    either = rules[PairRule.EITHER_DIRECTION].component
    return readout.ConcentrationReadout(concentration, either, either, either, either, counting, BUDGET, NO_FLUCTUATIONS, rules)


def pair_rule_run(condition: str, sketch: SketchedRun) -> running.ReadoutRun:
    primary = sketch.primary_loss
    losses = {PairRule.ONE_PER_CONNECTION: primary, PairRule.BOTH_DIRECTIONS: primary, PairRule.EITHER_DIRECTION: sketch.either_loss}
    induction = tuple(point(c, losses, sketch.counting) for c in GRID)
    return running.ReadoutRun(coherence_run(condition), induction, tuple(reversed(induction)))


def with_coupling(run: running.ReadoutRun, coupling: float) -> running.ReadoutRun:
    budget = replace(BUDGET, effective_coupling=coupling)
    return replace(run, induction=tuple(replace(p, budget=budget) for p in run.induction))


class SeedTests(unittest.TestCase):
    def test_no_seed_of_the_study_has_been_used_by_an_earlier_one(self) -> None:
        ours = set(range(settings.SEED_OFFSET, settings.SEED_OFFSET + max(settings.SEEDS.values())))
        for offset, count in EARLIER_OFFSETS_AND_SEEDS:
            self.assertFalse(ours & set(range(offset, offset + max(count, FIRST_BLOCK_SEEDS))), offset)
        self.assertFalse(ours & set(range(FIRST_BLOCK_SEEDS)))

    def test_the_first_seed_is_the_base_seed_plus_the_offset(self) -> None:
        self.assertEqual(prespecified_runs.first_seed(plan.AGENT_PLAN), cal.BASE_SEED + settings.SEED_OFFSET)

    def test_seeds_and_organisms_are_those_of_c12(self) -> None:
        self.assertEqual(settings.SEEDS, C12_SEEDS)


class ConditionTests(unittest.TestCase):
    def test_only_the_two_agents_with_the_global_reference_at_reference_values(self) -> None:
        conditions = plan.agent_conditions(cal.FULL_INTEGRATION)
        self.assertEqual([c.name for c in conditions], [ConditionName.GABAERGIC, ConditionName.NMDA_ANTAGONIST])
        reference = cal.base_sweep_design(cal.FULL_INTEGRATION)
        self.assertEqual(conditions[0].design, reference)
        self.assertEqual(conditions[1].design, replace(reference, agent=cal.NMDA_ANTAGONIST_AGENT))
        for condition in conditions:
            self.assertEqual(condition.design.reference_wiring, dynamics.ReferenceWiring.GLOBAL_MEAN_FIELD)
            self.assertEqual(condition.design.grid, cal.CONCENTRATION_GRID)
            self.assertFalse(condition.rewired)
            self.assertEqual(condition.organisms, settings.ORGANISMS)

    def test_the_full_study_uses_the_full_integration_and_every_seed(self) -> None:
        design = readout_plans.study_design(plan.AGENT_PLAN, StudyMode.FULL)
        self.assertEqual((design.integration, design.seeds_per_organism), (cal.FULL_INTEGRATION, settings.SEEDS))


class SmokeModeTests(unittest.TestCase):
    def test_the_smoke_mode_keeps_only_c_elegans_one_seed_and_two_concentrations(self) -> None:
        smoke = readout_plans.smoke_plan(plan.AGENT_PLAN)
        self.assertEqual(smoke.organisms, ("celegans",))
        for condition in smoke.conditions(readout_settings.SMOKE_INTEGRATION):
            self.assertEqual(condition.design.grid.ascending(), [0.0, cal.CONCENTRATION_GRID.maximum])
        self.assertEqual(readout_plans.study_design(smoke, StudyMode.SMOKE).seeds_per_organism, {"celegans": 1})

    def test_only_the_full_study_and_the_smoke_mode_can_be_asked_for(self) -> None:
        self.assertIs(dpc_pair_rule_study.parse_mode([]), StudyMode.FULL)
        self.assertIs(dpc_pair_rule_study.parse_mode(["--smoke"]), StudyMode.SMOKE)
        with self.assertRaises(SystemExit):
            dpc_pair_rule_study.parse_mode(["--quick"])


class AgentTestTests(unittest.TestCase):
    def test_a_loss_under_the_primary_rule_holds_whatever_c12s_reading_shows(self) -> None:
        self.assertTrue(checks.abolishes_quorum_under_primary_rule(pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(EARLY_LOSS, either_loss=None))))

    def test_no_loss_under_the_primary_rule_fails_even_when_c12s_reading_loses_quorum(self) -> None:
        self.assertFalse(checks.abolishes_quorum_under_primary_rule(pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(None, either_loss=EARLY_LOSS))))

    def test_no_quorum_even_awake_counts_as_failing(self) -> None:
        run = pair_rule_run(ConditionName.GABAERGIC, SketchedRun(NEVER_HELD))
        self.assertIsNone(measures.primary_loss(run))
        self.assertFalse(checks.abolishes_quorum_under_primary_rule(run))

    def test_each_test_is_judged_on_its_own_agent_and_sp1_1_is_not_run_without_a_pair_of_losses(self) -> None:
        runs = [pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS)), pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(None))]
        outcomes = {o.identifier: (o.runs_holding, o.runs_applicable) for o in checks.evaluate(runs, ["celegans"])}
        self.assertEqual(outcomes, {"T2a-1": (1, 1), "T2b-1": (0, 1)})


class PercolationTestTests(unittest.TestCase):
    def test_a_common_counting_share_with_different_couplings_is_percolation_like(self) -> None:
        gabaergic = with_coupling(pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS, counting=SIMILAR_SHARES[0])), COUPLINGS_APART[0])
        nmda = with_coupling(pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(LATE_LOSS, counting=SIMILAR_SHARES[1])), COUPLINGS_APART[1])
        self.assertTrue(checks.percolation_like_under_primary_rule(running.RunPair(gabaergic, nmda)))

    def test_a_common_coupling_with_different_counting_shares_is_not(self) -> None:
        gabaergic = with_coupling(pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS, counting=DIFFERENT_SHARES[0])), COUPLINGS_CLOSE[0])
        nmda = with_coupling(pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(LATE_LOSS, counting=DIFFERENT_SHARES[1])), COUPLINGS_CLOSE[1])
        self.assertFalse(checks.percolation_like_under_primary_rule(running.RunPair(gabaergic, nmda)))

    def test_it_reads_the_share_of_anatomical_connections_under_the_primary_rule_at_its_loss(self) -> None:
        run = pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS, counting=SIMILAR_SHARES[0]))
        self.assertEqual(measures.at_primary_loss(run).concentration, EARLY_LOSS)
        self.assertEqual(measures.counting_share_at_primary_loss(run), run.induction[0].pair_rules[PRIMARY_PAIR_RULE].counting_share)

    def test_undefined_where_either_agent_keeps_quorum(self) -> None:
        pair = running.RunPair(pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS)), pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(None)))
        self.assertIsNone(checks.percolation_like_under_primary_rule(pair))


class ReportTests(unittest.TestCase):
    def test_every_run_records_its_loss_under_every_rule_and_the_markdown_reports_them(self) -> None:
        runs = [pair_rule_run(ConditionName.GABAERGIC, SketchedRun(EARLY_LOSS)), pair_rule_run(ConditionName.NMDA_ANTAGONIST, SketchedRun(LATE_LOSS, either_loss=None))]
        design = prespecified_runs.StudyDesign("quick", readout_settings.SMOKE_INTEGRATION, {"celegans": 1})
        results = plan.PairRuleResults("2026-10-21T00:00:00+00:00", readout_plans.BlockResult(plan.AGENT_PLAN, design, runs))
        record = report.run_record(runs[1])
        self.assertEqual(record[report.LOSS_FIELD], {"one_per_connection": LATE_LOSS, "both_directions": LATE_LOSS, "either_direction": None})
        block = report.block_record(results)
        markdown = "\n".join(report.block_markdown(block))
        for rule in PairRule:
            self.assertIn(f"DPC loss concentration, {rule.value}", markdown)
        self.assertIn("T2b-1", markdown)
        self.assertFalse(report.every_evaluated_test_passes({"blocks": [block]}))


if __name__ == "__main__":
    unittest.main()
