"""Percolation-model inertia on the connectome graphs (connectome_inertia.py): calibration, held-out tests and a run
of the real model on a small fixed graph."""

from __future__ import annotations

import math
import random
import unittest
from unittest import mock

import connectome_inertia as inertia
import dpc_simulator as dpc

SERIES = (0.0, 8.0, 9.0)


def profile(loss: tuple[float | None, ...], recovery: tuple[float | None, ...], feedback: tuple[float, ...] = SERIES, seed: int = 1) -> inertia.InertiaProfile:
    return inertia.InertiaProfile("celegans", seed, feedback, loss, recovery)


class CalibrationTests(unittest.TestCase):
    def test_the_feedback_whose_mean_ratio_is_closest_is_chosen_among_those_where_every_seed_recovers(self) -> None:
        profiles = [profile((1.0, 1.08, 1.3), (1.0, 1.0, None)), profile((1.0, 1.08, 1.2), (1.0, 1.0, 1.0), seed=2)]
        chosen = inertia.calibrate(profiles, 1.08)
        self.assertEqual((chosen.feedback_ms, chosen.reproduced), (8.0, True))
        self.assertAlmostEqual(chosen.mean_ratio, 1.08)

    def test_a_target_further_than_the_tolerance_is_not_reproduced(self) -> None:
        chosen = inertia.calibrate([profile((1.0, 1.2, 1.3), (1.0, 1.0, 1.0))], 1.08)
        self.assertFalse(chosen.reproduced)

    def test_the_series_starts_without_feedback_and_keeps_only_reproduced_targets(self) -> None:
        calibrations = [inertia.ConnectomeCalibration("celegans", 1.11, 9.0, 1.11), inertia.ConnectomeCalibration("celegans", 1.08, 8.0, 1.08),
                        inertia.ConnectomeCalibration("celegans", 1.63, 20.0, 1.40)]
        self.assertEqual(inertia.calibrated_series(calibrations), (0.0, 8.0, 9.0))
        self.assertEqual(inertia.reference_feedback(calibrations), 8.0)

    def test_halothanes_ratio_is_not_a_target(self) -> None:
        self.assertEqual([t.ratio for t in inertia.TARGETS], [1.07, 1.08, 1.11, 1.63])


class HeldOutTests(unittest.TestCase):
    def seed(self, loss: tuple[float | None, ...], recovery: tuple[float | None, ...]) -> inertia.HeldOutSeed:
        return inertia.HeldOutSeed(profile(loss, recovery), 8.0)

    def test_pi1_needs_recovery_strictly_below_the_loss_at_the_reference_feedback(self) -> None:
        self.assertTrue(inertia.inertia_at_reference(self.seed((1.0, 1.1, 1.2), (1.0, 1.0, 1.0))))
        self.assertFalse(inertia.inertia_at_reference(self.seed((1.0, 1.0, 1.2), (1.0, 1.0, 1.0))))
        self.assertIsNone(inertia.inertia_at_reference(inertia.HeldOutSeed(profile((1.0,), (1.0,), (0.0,)), None)))

    def test_pi2_counts_never_recovering_as_unbounded_and_needs_growth(self) -> None:
        self.assertTrue(inertia.inertia_grows_with_feedback(self.seed((1.0, 1.1, 1.2), (1.0, 1.0, None))))
        self.assertFalse(inertia.inertia_grows_with_feedback(self.seed((1.0, 1.2, 1.1), (1.0, 1.0, 1.0))))
        self.assertFalse(inertia.inertia_grows_with_feedback(self.seed((1.0, 1.0, 1.0), (1.0, 1.0, 1.0))))
        self.assertIsNone(inertia.inertia_grows_with_feedback(inertia.HeldOutSeed(profile((1.0,), (1.0,), (0.0,)), None)))

    def test_pi3_and_pi4(self) -> None:
        self.assertTrue(inertia.no_inertia_without_feedback(self.seed((1.0, 1.1, 1.2), (1.0, 1.0, 1.0))))
        self.assertTrue(inertia.measured_inertia_reproduced(self.seed((1.0, 1.1, 1.2), (1.0, 1.0, 1.0))))
        self.assertFalse(inertia.measured_inertia_reproduced(self.seed((1.0, 1.05, 1.2), (1.0, 1.0, 1.0))))
        self.assertFalse(inertia.measured_inertia_reproduced(self.seed((1.0, 1.1, 1.2), (1.0, 0.0, 1.0))))


class ModelOnAFixedGraphTests(unittest.TestCase):
    def test_the_model_runs_on_a_fixed_graph_with_the_seed_varying_only_the_percolation_draws(self) -> None:
        graph = dpc.RandomGraphBuilder(300, 8.0).build(random.Random(0))
        with mock.patch.object(inertia, "connectome_graph", return_value=graph):
            dpc.built_graph.cache_clear()
            dpc.percolation_curve.cache_clear()
            task = inertia.InertiaTask("celegans", 7, (0.0, 12.0), 0.05)
            result = inertia.run_inertia_task(task)
            self.assertIs(inertia.ConnectomeGraphBuilder("celegans").build(random.Random(1)), graph)
            dpc.built_graph.cache_clear()
            dpc.percolation_curve.cache_clear()
        loss, recovery = result.at(0.0)
        self.assertIsNotNone(loss)
        self.assertEqual(loss, recovery)
        self.assertTrue(inertia.no_inertia_without_feedback(inertia.HeldOutSeed(result, None)))
        self.assertFalse(math.isnan(result.loss[1] or 0.0))


if __name__ == "__main__":
    unittest.main()
