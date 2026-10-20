"""Verdicts of the pre-specified P4b tests (Appendix C.10), including grid values that differ only by rounding."""

from __future__ import annotations

import unittest
from dataclasses import replace

import calibration as cal
import learned_timing_study as study
import species_study as species
from tests.test_prespecified_study import run


def pair(learned_loss: float | None, comparison_loss: float | None, awake: tuple[float, float] = (0.9, 0.9)) -> study.LearningPair:
    learned = run(species.ConditionName.GABAERGIC, loss_concentration=learned_loss, induction_coherence=(awake[0],))
    comparison = run(species.ConditionName.GABAERGIC, loss_concentration=comparison_loss, induction_coherence=(awake[1],))
    return study.LearningPair(learned, comparison)


class LearnedTimingVerdictTests(unittest.TestCase):
    def test_l1_holds_only_when_quorum_is_never_lost(self) -> None:
        self.assertTrue(study.quorum_never_lost(run(species.ConditionName.GABAERGIC, loss_concentration=None)))
        self.assertFalse(study.quorum_never_lost(run(species.ConditionName.GABAERGIC, loss_concentration=2.95)))

    def test_l2_allows_exactly_one_step_of_delay_and_needs_a_loss(self) -> None:
        self.assertTrue(study.loss_not_delayed_by_more_than_a_step(pair(0.7000000000000001, 0.65)))
        self.assertFalse(study.loss_not_delayed_by_more_than_a_step(pair(0.75, 0.65)))
        self.assertTrue(study.loss_not_delayed_by_more_than_a_step(pair(0.6, 0.65)))
        self.assertFalse(study.loss_not_delayed_by_more_than_a_step(pair(None, 0.65)))

    def test_l3_allows_exactly_one_step_lower_and_needs_a_loss(self) -> None:
        self.assertTrue(study.loss_not_lowered_by_more_than_a_step(pair(1.5, 1.55)))
        self.assertFalse(study.loss_not_lowered_by_more_than_a_step(pair(1.45, 1.55)))
        self.assertTrue(study.loss_not_lowered_by_more_than_a_step(pair(1.7, 1.55)))
        self.assertFalse(study.loss_not_lowered_by_more_than_a_step(pair(None, 1.55)))

    def test_l4_needs_the_awake_state_kept_and_the_loss_within_one_step_either_way(self) -> None:
        self.assertTrue(study.awake_state_and_loss_kept(pair(1.6, 1.55)))
        self.assertTrue(study.awake_state_and_loss_kept(pair(1.5, 1.55)))
        self.assertFalse(study.awake_state_and_loss_kept(pair(1.65, 1.55)))
        self.assertFalse(study.awake_state_and_loss_kept(pair(1.55, 1.55, awake=(0.8, 0.9))))
        self.assertTrue(study.awake_state_and_loss_kept(pair(1.55, 1.55, awake=(0.81, 0.9))))

    def test_every_condition_has_a_learned_twin_on_the_same_organisms(self) -> None:
        conditions = {c.name: c for c in study.build_conditions(cal.QUICK_INTEGRATION)}
        for name, condition in conditions.items():
            if name.endswith("learned arrival times"):
                continue
            twin = conditions[f"{name}, learned arrival times"]
            self.assertEqual(twin.organisms, condition.organisms)
            self.assertIsNone(condition.design.dynamics.arrival_learning_time)
            self.assertEqual(twin.design.dynamics.arrival_learning_time, cal.ARRIVAL_LEARNING_TIME)
            self.assertEqual(replace_learning(twin.design), condition.design)


def replace_learning(design: object) -> object:
    return replace(design, dynamics=replace(design.dynamics, arrival_learning_time=None))


if __name__ == "__main__":
    unittest.main()
