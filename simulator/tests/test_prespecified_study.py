"""Tests for the pre-specified study's checks (K2a-c, P1c), pass rule and report.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest
from dataclasses import replace

import calibration as cal
import prespecified_study as prereg
import reporting
import species_study as species

AWAKE_BROADCAST = 0.6
LOSS = 1.0


def run(condition: str, seed: int = 1, **overrides: object) -> species.RunSummary:
    base = species.RunSummary(
        organism="celegans", condition=condition, seed=seed,
        loss_concentration=LOSS, recovery_concentration=LOSS, hysteresis_width=0.0, susceptibility_surge=20.0,
        susceptibility_peak_concentration=LOSS, local_global_dissociation=0.0, awake_broadcast_ratio=AWAKE_BROADCAST,
        unconscious_broadcast_ratio=AWAKE_BROADCAST, awake_sensory_entrainment=0.5, unconscious_sensory_entrainment=0.5,
        awake_susceptibility=0.1, loss_susceptibility=2.0, deepest_coherence_fraction=0.1, deepest_broadcast_ratio=None,
        concentrations=(0.0, LOSS), induction_coherence=(1.0, 0.1), emergence_coherence=(1.0, 0.1),
        induction_susceptibility=(0.1, 2.0), induction_broadcast_ratio=(AWAKE_BROADCAST, AWAKE_BROADCAST), seconds=1.0,
    )
    return replace(base, **overrides)


FEEDBACK = prereg.ConditionName.FEEDBACK_FAULTS
RANDOM = prereg.ConditionName.MATCHED_RANDOM_FAULTS


class ForwardSpreadTests(unittest.TestCase):
    def test_holds_at_exactly_half_the_awake_broadcast(self) -> None:
        self.assertTrue(prereg.forward_spread_survives(run(FEEDBACK, unconscious_broadcast_ratio=0.5 * AWAKE_BROADCAST)))

    def test_fails_below_half(self) -> None:
        self.assertFalse(prereg.forward_spread_survives(run(FEEDBACK, unconscious_broadcast_ratio=0.49 * AWAKE_BROADCAST)))

    def test_counts_as_failing_where_quorum_is_never_lost(self) -> None:
        self.assertFalse(prereg.forward_spread_survives(run(FEEDBACK, unconscious_broadcast_ratio=None)))


class MatchedControlTests(unittest.TestCase):
    def pair(self, feedback_loss: float | None, random_loss: float | None) -> prereg.FaultPlacementPair:
        return prereg.FaultPlacementPair(run(FEEDBACK, loss_concentration=feedback_loss), run(RANDOM, loss_concentration=random_loss))

    def test_holds_when_random_faults_need_a_higher_concentration(self) -> None:
        self.assertTrue(prereg.feedback_faults_act_at_a_lower_concentration(self.pair(1.0, 1.5)))

    def test_holds_when_random_faults_never_abolish_quorum(self) -> None:
        self.assertTrue(prereg.feedback_faults_act_at_a_lower_concentration(self.pair(1.0, None)))

    def test_fails_at_an_equal_concentration(self) -> None:
        self.assertFalse(prereg.feedback_faults_act_at_a_lower_concentration(self.pair(1.0, 1.0)))

    def test_fails_when_feedback_faults_never_abolish_quorum(self) -> None:
        self.assertFalse(prereg.feedback_faults_act_at_a_lower_concentration(self.pair(None, None)))

    def test_runs_are_paired_by_organism_and_seed(self) -> None:
        runs = [run(FEEDBACK, seed=1), run(RANDOM, seed=2), run(RANDOM, seed=1), run(FEEDBACK, seed=3)]
        pairs = prereg.fault_placement_pairs(runs)
        self.assertEqual([(p.feedback.seed, p.matched_random.seed) for p in pairs], [(1, 1)])


class PassRuleTests(unittest.TestCase):
    def outcome(self, holding: int, applicable: int) -> reporting.CheckOutcome:
        return reporting.CheckOutcome("K2a", "statement", "C. elegans", holding, applicable)

    def test_passes_at_exactly_the_pass_share(self) -> None:
        self.assertTrue(prereg.passes(self.outcome(16, 20)))

    def test_fails_just_below_the_pass_share(self) -> None:
        self.assertFalse(prereg.passes(self.outcome(15, 20)))

    def test_fails_when_no_run_applies(self) -> None:
        self.assertFalse(prereg.passes(self.outcome(0, 0)))


class DesignTests(unittest.TestCase):
    def test_seeds_are_fresh_and_feedback_conditions_skip_the_undirected_human_connectome(self) -> None:
        design = prereg.StudyDesign("test", cal.QUICK_INTEGRATION, {o: 1 for o in cal.ORGANISMS})
        tasks = prereg.tasks_for(design)
        self.assertTrue(all(t.seed == cal.BASE_SEED + prereg.SEED_OFFSET for t in tasks))
        human = {t.condition.name for t in tasks if t.organism == "human"}
        self.assertEqual(human, {species.ConditionName.GABAERGIC})

    def test_report_renders_from_synthetic_runs(self) -> None:
        runs = [run(FEEDBACK), run(RANDOM, loss_concentration=None), run(species.ConditionName.GABAERGIC)]
        outcomes = prereg.evaluate(runs, ["celegans"])
        self.assertEqual({o.identifier for o in outcomes}, {"K2a", "K2b", "K2c", "P1c"})
        self.assertTrue(all(prereg.passes(o) for o in outcomes))
        table = "\n".join(prereg.outcome_table(outcomes, ["celegans"]))
        self.assertIn("1/1", table)
        self.assertIn("passes", table)


if __name__ == "__main__":
    unittest.main()
