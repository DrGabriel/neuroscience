"""Comparisons of grid-derived values, with the exact values that exposed rounding errors on 19 October 2026."""

from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

import comparisons
import prespecified_study
import reporting
import species_study as species
from tests.test_prespecified_study import run


class ComparisonTests(unittest.TestCase):
    def test_equal_values_that_differ_by_rounding_count_as_equal(self) -> None:
        self.assertTrue(comparisons.equals(0.09999999999999987, 0.09999999999999998))
        self.assertFalse(comparisons.exceeds(0.09999999999999998, 0.09999999999999987))
        self.assertTrue(comparisons.at_most(0.15000000000000013, 0.15000000000000002))

    def test_a_difference_of_one_grid_step_is_never_mistaken_for_rounding(self) -> None:
        self.assertTrue(comparisons.exceeds(1.45, 1.4))
        self.assertFalse(comparisons.at_most(1.46, 1.45))

    def test_shares_are_compared_exactly_and_need_something_to_count(self) -> None:
        self.assertTrue(comparisons.at_least_share(16, 20, Fraction(4, 5)))
        self.assertFalse(comparisons.at_least_share(15, 20, Fraction(4, 5)))
        self.assertFalse(comparisons.at_least_share(4, 6, Fraction(4, 5)))
        self.assertTrue(comparisons.at_least_share(5, 6, Fraction(4, 5)))
        self.assertFalse(comparisons.at_least_share(0, 0, Fraction(4, 5)))


class VerdictRoundingRegressionTests(unittest.TestCase):
    def test_equal_one_step_gains_do_not_favour_the_jitter_agent_Regression(self) -> None:
        # Drosophila, every seed of species_full_20261019T123532Z: both agents gain exactly one 0.1 grid step.
        comparison = species.FallbackComparison("drosophila", 20261017, 1.4000000000000001, 1.5, 0.6000000000000001, 0.7000000000000001)
        self.assertFalse(species.larger_gain_against_jitter(comparison))

    def test_a_surge_exactly_three_steps_from_the_collapse_is_within_the_window_Regression(self) -> None:
        # C. elegans seed 20261020 of the same report: peak at 1.45, loss at 1.3, stored distance 0.15000000000000013.
        boundary = run(species.ConditionName.GABAERGIC, loss_concentration=1.3, susceptibility_peak_concentration=1.4500000000000002, susceptibility_surge=46.6)
        self.assertTrue(species.fluctuation_surge_at_collapse(boundary))

    def test_a_surge_four_steps_from_the_collapse_is_outside_the_window(self) -> None:
        outside = run(species.ConditionName.GABAERGIC, loss_concentration=1.3, susceptibility_peak_concentration=1.5, susceptibility_surge=46.6)
        self.assertFalse(species.fluctuation_surge_at_collapse(outside))

    def test_hysteresis_of_rounding_size_counts_as_none(self) -> None:
        tiny = run(species.ConditionName.GABAERGIC, hysteresis_width=1e-16)
        self.assertTrue(species.no_hysteresis(tiny))
        strictly_positive = next(pillar for pillar in species.SECONDARY_ANALYSES if pillar.identifier == "S3")
        self.assertFalse(strictly_positive.holds_for(tiny))
        self.assertTrue(species.non_negative_hysteresis(run(species.ConditionName.GABAERGIC, hysteresis_width=-1e-16)))

    def test_pass_rule_is_exact_at_the_threshold(self) -> None:
        def outcome(holding: int, applicable: int) -> reporting.CheckOutcome:
            return reporting.CheckOutcome("T1c", "s", "C. elegans", holding, applicable)
        self.assertTrue(prespecified_study.passes(outcome(16, 20)))
        self.assertFalse(prespecified_study.passes(outcome(4, 6)))
        self.assertFalse(prespecified_study.passes(outcome(0, 0)))

    def test_a_check_defined_in_no_run_does_not_hold_Regression(self) -> None:
        self.assertFalse(reporting.CheckOutcome("N1", "s", "Drosophila", 0, 0).holds)
        self.assertTrue(reporting.CheckOutcome("N1", "s", "Human", 20, 20).holds)



class ReevaluationTests(unittest.TestCase):
    def test_stored_runs_come_back_unchanged_under_a_new_start_time(self) -> None:
        runs = [run(species.ConditionName.GABAERGIC, seed=seed) for seed in (1, 2)]
        plants = [species.PlantSummary(0.5, 1, 0.83)]
        stored = json.loads(json.dumps({
            "label": "full", "started_utc": "2026-10-19T12:35:32+00:00", "finished_utc": "2026-10-19T20:24:41+00:00",
            "design": {"plant_seeds": 1}, "provenance": {"git_commit": "abc"},
            "runs": [asdict(r) for r in runs], "plant_runs": [asdict(p) for p in plants],
        }))
        results = species.results_from_report(stored)
        self.assertEqual(results.runs, runs)
        self.assertEqual(results.plants, plants)
        self.assertNotEqual(results.started_utc, stored["started_utc"])
        record = species.reevaluation_record(Path("species_full_20261019T123532Z.json"), stored)
        self.assertEqual(record["reevaluated_from"], "species_full_20261019T123532Z.json")
        self.assertEqual(record["run_started_utc"], stored["started_utc"])


if __name__ == "__main__":
    unittest.main()
