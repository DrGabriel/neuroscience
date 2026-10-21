"""Analyses B, C and D of Appendix C.14 and their seeds: the directed generating-function estimate on a graph computed
by hand, the reciprocity construction, the crossing of the quorum, the validation study on fresh seeds, and proof that
no seed of these analyses was used by calibration, by Appendix B.4 or by any earlier study.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import json
import unittest
from fractions import Fraction

import numpy as np

import calibrate_feedback
import calibration as cal
import congestion_study
import directed_threshold_estimate as directed_command
import disconnection_study
import dpc_simulator as dpc
import fresh_seed_validation
import learned_timing_study
import prediction15_study
import prespecified_study
import reciprocity_estimate
import reporting
import validation_study as validation
from connection_pairs import AnatomicalConnections
from pair_rule_diagnostic import StaticDraw
from pair_rule_study import settings as pair_rule_settings
from readout_study import settings as readout_settings
from round3_study import directed_estimate, fresh_validation, reciprocity, seeds
from round3_study.crossings import SweptPoint, first_fall_below
from tests.test_connection_pairs import two_way_ring, wired

PLACES = 9
# 0 -> 1 -> 2 -> 0 and 0 -> 2: in-degrees (1, 1, 2), out-degrees (2, 1, 1), so <k> = 4/3 and <j k> = 5/3.
HAND_GRAPH = [(0, 1), (1, 2), (2, 0), (0, 2)]
HAND_MEAN_DEGREE, HAND_MEAN_IN_OUT_PRODUCT = Fraction(4, 3), Fraction(5, 3)
HAND_ONSET = Fraction(4, 5)
# One more arc 0 -> 1 raises the mean degree to 5/3.
REPEATED_MEAN_DEGREE = Fraction(5, 3)
# At pi = 0.9 both fixed points solve 0.9 z^2 - 1.3 z + 0.4 = 0, so x = y = 4/9 and
# S = [(1 - 16/81)(5/9) + (5/9)^2 + (5/9)(1 - 16/81)] / 3 = 875/2187.
HAND_OCCUPATION = 0.9
HAND_STRONG_SHARE = Fraction(875, 2187)
RING = 10
TWO_WAY_ONSET = Fraction(1, 2)
QUORUM = cal.QUORUM_FRACTION
RESOLUTION = 1e-6
QUOTED_ON_TIME, ON_TIME_PLACES = 0.024, 3
SHARES = (0.0, 0.3, 1.0)
EVERY_ARC, NO_ARC = 1.0, 0.0
ONE_ASSIGNMENT = reciprocity.SweepSize(1, 2)
SEED = 0
HUMAN_DIRECTED_THRESHOLD = 0.0495
MEASURED_PLACES = 4
RATIO_LOSS, RATIO_RECOVERY = 0.88, 0.8
# Falls from 0.8 to 0.4 between parameters 1 and 0.5, so it crosses 0.5 three quarters of the way, at 0.625.
FALLING = [SweptPoint(1.0, 0.8), SweptPoint(0.5, 0.4), SweptPoint(0.0, 0.1)]
FALLING_CROSSING = 0.625
STARTS_BELOW = [SweptPoint(1.0, 0.4), SweptPoint(0.5, 0.3)]
STAYS_ABOVE = [SweptPoint(1.0, 0.9), SweptPoint(0.5, 0.6)]
SHARE_GRID_POINTS = 21
TIMING_ERROR_RANGE_MS = (20.0, 80.0)


def hand_joint() -> directed_estimate.JointDegrees:
    return directed_estimate.JointDegrees.of(wired(HAND_GRAPH))


def ring_fibres() -> AnatomicalConnections:
    return AnatomicalConnections.of(wired(two_way_ring(RING)))


def reference_summary(loss: float | None, recovery: float | None) -> validation.SeedMeasurement:
    summary = validation.ThresholdSummary(loss, recovery, None, None)
    fields = dict.fromkeys(validation.SeedMeasurement.__dataclass_fields__)
    return validation.SeedMeasurement(**(fields | {"reference": summary, "node_count": RING, "seed": SEED}))


class SeedBlockTests(unittest.TestCase):
    def test_the_registry_of_earlier_blocks_matches_the_offsets_the_studies_use(self) -> None:
        used = {
            0, congestion_study.CONFIRMATORY_SEED_OFFSET, prespecified_study.SEED_OFFSET, learned_timing_study.SEED_OFFSET,
            disconnection_study.SEED_OFFSET, readout_settings.SEED_OFFSET, readout_settings.CALIBRATION_SEED_OFFSET,
            readout_settings.COUPLING_CALIBRATION_SEED_OFFSET, pair_rule_settings.SEED_OFFSET,
        }
        self.assertEqual({block.offset for block in seeds.EARLIER_BLOCKS}, used)

    def test_no_round_three_seed_was_used_by_an_earlier_study_or_by_another_round_three_analysis(self) -> None:
        for block in seeds.ROUND_THREE_BLOCKS:
            for earlier in seeds.EARLIER_BLOCKS:
                self.assertFalse(block.overlaps(earlier), (block.name, earlier.name))
            for other in seeds.ROUND_THREE_BLOCKS:
                self.assertEqual(block.overlaps(other), block is other, (block.name, other.name))

    def test_the_fresh_validation_seeds_are_disjoint_from_calibration_and_from_b4(self) -> None:
        b4 = validation.StudyDesign(reporting.RunLabel.FULL, validation.FULL_NODE_COUNTS, validation.FULL_SEEDS_PER_SIZE)
        fresh = {task.seed for task in fresh_seed_validation.FULL_DESIGN.tasks()}
        self.assertFalse(fresh & set(calibrate_feedback.CALIBRATION_SEEDS))
        self.assertFalse(fresh & {task.seed for task in b4.tasks()})
        self.assertEqual(fresh, set(seeds.FRESH_VALIDATION_BLOCK.seeds()))

    def test_no_analysis_uses_a_seed_whose_outcome_was_seen_while_the_code_was_checked(self) -> None:
        for block in seeds.ROUND_THREE_BLOCKS:
            for seen in (*seeds.SEEN_WHILE_CHECKING, seeds.SMOKE_BLOCK):
                self.assertFalse(block.overlaps(seen), (block.name, seen.name))
        for earlier in seeds.EARLIER_BLOCKS:
            self.assertFalse(seeds.SMOKE_BLOCK.overlaps(earlier), earlier.name)

    def test_every_smoke_run_uses_the_smoke_block(self) -> None:
        smoke = set(seeds.SMOKE_BLOCK.seeds())
        self.assertLessEqual({task.seed for task in fresh_seed_validation.SMOKE_DESIGN.tasks()}, smoke)
        self.assertLessEqual({task.seed for task in prediction15_study.SMOKE_DESIGN.tasks()}, smoke)
        self.assertIs(reciprocity_estimate.SMOKE_DESIGN.seeds, seeds.SMOKE_BLOCK)
        self.assertIs(reciprocity_estimate.FULL_DESIGN.seeds, seeds.RECIPROCITY_BLOCK)

    def test_block_overlap_is_symmetric_and_touching_blocks_do_not_overlap(self) -> None:
        first, touching, inside = seeds.SeedBlock("a", 0, RING), seeds.SeedBlock("b", RING, RING), seeds.SeedBlock("c", RING - 1, 1)
        self.assertFalse(first.overlaps(touching) or touching.overlaps(first))
        self.assertTrue(first.overlaps(inside) and inside.overlaps(first))


class CrossingTests(unittest.TestCase):
    def test_the_crossing_is_interpolated_between_the_points_around_it(self) -> None:
        self.assertAlmostEqual(first_fall_below(FALLING, QUORUM), FALLING_CROSSING, places=PLACES)

    def test_no_crossing_when_the_curve_starts_below_or_never_falls_below(self) -> None:
        self.assertIsNone(first_fall_below(STARTS_BELOW, QUORUM))
        self.assertIsNone(first_fall_below(STAYS_ABOVE, QUORUM))
        self.assertIsNone(first_fall_below(STAYS_ABOVE[:1], QUORUM))


class DirectedEstimateTests(unittest.TestCase):
    def test_the_onset_on_a_hand_computed_graph_is_mean_degree_over_mean_in_out_product(self) -> None:
        joint = hand_joint()
        self.assertAlmostEqual(joint.mean_degree(), float(HAND_MEAN_DEGREE), places=PLACES)
        self.assertAlmostEqual(joint.mean_in_out_product(), float(HAND_MEAN_IN_OUT_PRODUCT), places=PLACES)
        self.assertAlmostEqual(joint.onset_threshold(), float(HAND_ONSET), places=PLACES)

    def test_the_strong_component_share_on_the_hand_computed_graph(self) -> None:
        self.assertAlmostEqual(hand_joint().strong_component_share(HAND_OCCUPATION), float(HAND_STRONG_SHARE), places=PLACES)
        self.assertAlmostEqual(hand_joint().strong_component_share(EVERY_ARC), EVERY_ARC, places=PLACES)

    def test_a_two_way_ring_has_its_onset_at_one_half(self) -> None:
        self.assertAlmostEqual(directed_estimate.JointDegrees.of(wired(two_way_ring(RING))).onset_threshold(), float(TWO_WAY_ONSET), places=PLACES)

    def test_self_connections_are_left_out_and_repeated_arcs_count(self) -> None:
        with_loop = directed_estimate.JointDegrees.of(wired([*HAND_GRAPH, (1, 1)]))
        self.assertAlmostEqual(with_loop.onset_threshold(), float(HAND_ONSET), places=PLACES)
        repeated = directed_estimate.JointDegrees.of(wired([*HAND_GRAPH, (0, 1)]))
        self.assertAlmostEqual(repeated.mean_degree(), float(REPEATED_MEAN_DEGREE), places=PLACES)

    def test_the_quorum_threshold_is_where_the_estimated_share_first_reaches_the_quorum(self) -> None:
        joint = hand_joint()
        threshold = joint.quorum_threshold(QUORUM)
        self.assertGreaterEqual(joint.strong_component_share(threshold), QUORUM)
        self.assertLess(joint.strong_component_share(threshold - RESOLUTION), QUORUM)
        self.assertGreater(threshold, joint.onset_threshold())

    def test_the_measured_directed_thresholds_are_read_from_the_b5_report(self) -> None:
        report = json.loads((reporting.RESULTS_DIRECTORY / directed_command.MEASURED_REPORT).read_text())
        mean, _ = directed_command.measured_directed_thresholds(report)[cal.ORGANISMS["human"].display_name]
        self.assertAlmostEqual(mean, HUMAN_DIRECTED_THRESHOLD, places=MEASURED_PLACES)


class ReciprocityTests(unittest.TestCase):
    def test_reassigning_directions_keeps_every_anatomical_connection_and_makes_the_chosen_share_two_way(self) -> None:
        fibres = ring_fibres()
        for share in SHARES:
            reassigned = reciprocity.with_reciprocal_share(fibres, share, np.random.default_rng(SEED))
            two_way = round(share * fibres.count)
            self.assertEqual(reassigned.count, fibres.count)
            self.assertEqual((reassigned.lower.tolist(), reassigned.higher.tolist()), (fibres.lower.tolist(), fibres.higher.tolist()))
            self.assertEqual(reassigned.connection_of_arc.size, fibres.count + two_way)
            both_ways = (reassigned.ascending_arc >= 0) & (reassigned.descending_arc >= 0)
            self.assertEqual(int(both_ways.sum()), two_way)

    def test_the_on_time_probability_at_the_reference_error_is_the_one_quoted_in_c13_and_falls_with_the_error(self) -> None:
        self.assertAlmostEqual(reciprocity.on_time_probability(reciprocity.REFERENCE_TIMING_ERROR_MS), QUOTED_ON_TIME, places=ON_TIME_PLACES)
        reference = StaticDraw(cal.NMDA_ANTAGONIST_AGENT, reciprocity.CONCENTRATION_OVER_EC50).on_time_probability()
        self.assertEqual(reciprocity.on_time_probability(reciprocity.REFERENCE_TIMING_ERROR_MS), reference)
        values = [reciprocity.on_time_probability(error) for error in reciprocity.MAXIMAL_TIMING_ERRORS_MS]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_every_arc_on_time_joins_the_ring_and_none_leaves_each_population_alone(self) -> None:
        estimator = reciprocity.StaticEstimator(ring_fibres(), ONE_ASSIGNMENT, np.random.default_rng(SEED))
        for share in SHARES:
            self.assertEqual(estimator.giant_share(reciprocity.StaticSetting(share, EVERY_ARC)), EVERY_ARC)
            self.assertEqual(estimator.giant_share(reciprocity.StaticSetting(share, NO_ARC)), 1 / RING)

    def test_the_sweeps_cover_the_pre_specified_ranges(self) -> None:
        shares = reciprocity.RECIPROCAL_SHARES
        self.assertEqual((shares[0], shares[-1], len(shares)), (NO_ARC, EVERY_ARC, SHARE_GRID_POINTS))
        self.assertEqual((reciprocity.MAXIMAL_TIMING_ERRORS_MS[0], reciprocity.MAXIMAL_TIMING_ERRORS_MS[-1]), TIMING_ERROR_RANGE_MS)
        self.assertIn(reciprocity.REFERENCE_TIMING_ERROR_MS, reciprocity.MAXIMAL_TIMING_ERRORS_MS)
        self.assertIs(reciprocity_estimate.parse_design([]), reciprocity_estimate.FULL_DESIGN)
        self.assertIs(reciprocity_estimate.parse_design(["--smoke"]), reciprocity_estimate.SMOKE_DESIGN)


class FreshValidationTests(unittest.TestCase):
    def test_the_design_is_b4s_on_fresh_seeds(self) -> None:
        design = fresh_seed_validation.FULL_DESIGN
        self.assertEqual((design.node_counts, design.seeds_per_size), (validation.FULL_NODE_COUNTS, validation.FULL_SEEDS_PER_SIZE))
        self.assertEqual(design.base_seed, dpc.REFERENCE_SEED + seeds.FRESH_VALIDATION_BLOCK.offset)
        self.assertIs(fresh_seed_validation.parse_design(["--smoke"]), fresh_seed_validation.SMOKE_DESIGN)

    def test_the_ratio_is_loss_over_recovery_and_undefined_without_either(self) -> None:
        self.assertAlmostEqual(fresh_validation.inertia_ratio(reference_summary(RATIO_LOSS, RATIO_RECOVERY)), RATIO_LOSS / RATIO_RECOVERY, places=PLACES)
        self.assertIsNone(fresh_validation.inertia_ratio(reference_summary(RATIO_LOSS, None)))
        self.assertIsNone(fresh_validation.inertia_ratio(reference_summary(None, RATIO_RECOVERY)))

    def test_the_published_range_includes_its_ends(self) -> None:
        low, high = fresh_validation.PUBLISHED_RATIO_RANGE
        self.assertTrue(fresh_validation.within_published_range(reference_summary(low, 1.0)))
        self.assertTrue(fresh_validation.within_published_range(reference_summary(high, 1.0)))
        self.assertFalse(fresh_validation.within_published_range(reference_summary(RATIO_LOSS, RATIO_LOSS)))


if __name__ == "__main__":
    unittest.main()
