"""K1c (Appendix C.11): conditions, the awake gate, the floor-corrected criterion and the evaluability rule."""

from __future__ import annotations

import unittest
from dataclasses import replace

import calibration as cal
import disconnection_study as study
import reporting
import species_study as species
from tests.test_prespecified_study import run

K1 = species.ConditionName.KETAMINE_PATHWAYS


def pair(awake: tuple[float, float], deepest: tuple[float, float], coherence: float = 0.95) -> study.StimulusPair:
    """(applied, phantom) locking awake and at the highest concentration."""
    applied = run(study.APPLIED, awake_broadcast_entrainment=awake[0], deepest_broadcast_entrainment=deepest[0], deepest_coherence_fraction=coherence)
    phantom = run(study.PHANTOM, awake_broadcast_entrainment=awake[1], deepest_broadcast_entrainment=deepest[1])
    return study.StimulusPair(applied, phantom)


class ConditionTests(unittest.TestCase):
    def test_applied_is_k1_with_an_eight_cycle_window_and_the_phantom_differs_only_in_strength(self) -> None:
        k1 = next(c for c in species.build_conditions(cal.FULL_INTEGRATION) if c.name == K1).design
        applied, phantom = (c.design for c in study.build_conditions(cal.FULL_INTEGRATION))
        self.assertEqual(applied.integration.measurement_steps, cal.measurement_steps_for(8))
        self.assertEqual(replace(applied, integration=k1.integration), k1)
        self.assertEqual(phantom.stimulus.strength, 0.0)
        self.assertEqual(replace(phantom, stimulus=applied.stimulus), applied)

    def test_the_smoke_run_keeps_its_short_window(self) -> None:
        applied, _ = (c.design for c in study.build_conditions(cal.QUICK_INTEGRATION))
        self.assertEqual(applied.integration, cal.QUICK_INTEGRATION)


class CriterionTests(unittest.TestCase):
    def test_a_seed_without_awake_broadcast_above_twice_the_floor_is_not_applicable(self) -> None:
        self.assertIsNone(study.disconnected_above_the_floor(pair((0.039, 0.02), (0.02, 0.02))))
        self.assertIsNotNone(study.disconnected_above_the_floor(pair((0.04, 0.02), (0.02, 0.02))))

    def test_broadcast_above_the_floor_must_fall_to_half_or_less(self) -> None:
        # Awake excess 0.10; at the highest dose an excess of exactly 0.05 passes, 0.06 does not.
        self.assertTrue(study.disconnected_above_the_floor(pair((0.13, 0.03), (0.08, 0.03))))
        self.assertFalse(study.disconnected_above_the_floor(pair((0.13, 0.03), (0.09, 0.03))))

    def test_quorum_must_hold_at_the_highest_dose(self) -> None:
        self.assertFalse(study.disconnected_above_the_floor(pair((0.13, 0.03), (0.03, 0.03), coherence=0.49)))
        self.assertTrue(study.disconnected_above_the_floor(pair((0.13, 0.03), (0.03, 0.03), coherence=0.5)))

    def test_pairs_match_by_organism_and_seed(self) -> None:
        runs = [run(study.APPLIED, seed=1), run(study.PHANTOM, seed=1), run(study.APPLIED, seed=2)]
        self.assertEqual([(p.applied.seed, p.phantom.seed) for p in study.stimulus_pairs(runs)], [(1, 1)])


class EvaluabilityTests(unittest.TestCase):
    def test_k1c_is_not_judged_when_fewer_than_half_the_seeds_pass_the_gate(self) -> None:
        runs = [run(study.APPLIED, seed=s) for s in range(4)]
        verdict = study.verdict_for(runs)
        self.assertEqual(verdict(reporting.CheckOutcome("K1c", "s", "C. elegans", 1, 1)), study.NOT_EVALUABLE)
        self.assertEqual(verdict(reporting.CheckOutcome("K1c", "s", "C. elegans", 2, 2)), "passes")
        self.assertEqual(verdict(reporting.CheckOutcome("K1c", "s", "C. elegans", 1, 2)), "fails")


if __name__ == "__main__":
    unittest.main()
