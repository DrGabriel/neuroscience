"""Networks, surrogates and the threshold-shape test, on data whose answer is known."""

from __future__ import annotations

import unittest

import numpy as np

from analysis.open_data import network, threshold_shape
from analysis.open_data.specs import EdgeTest, SurrogateSpec
from analysis.open_data.threshold_shape import Logistic, ShapeFit

WHITE_NOISE_Z99 = 2.3263478740408408


def factor_windows(coupling: np.ndarray, n_nodes: int, n_samples: int, rng: np.random.Generator) -> list[np.ndarray]:
    """Windows in which every pair of nodes has correlation equal to the given coupling (one shared factor)."""
    windows = []
    for a in coupling:
        shared = rng.standard_normal(n_samples)
        windows.append(np.sqrt(a) * shared + np.sqrt(1 - a) * rng.standard_normal((n_nodes, n_samples)))
    return windows


class GiantComponentTests(unittest.TestCase):
    def test_two_components_of_three_and_two_nodes(self) -> None:
        adjacency = np.zeros((5, 5), bool)
        for i, j in ((0, 1), (1, 2), (3, 4)):
            adjacency[i, j] = adjacency[j, i] = True
        self.assertAlmostEqual(network.giant_component_fraction(adjacency), 0.6)

    def test_no_edges_leaves_single_nodes_and_a_complete_graph_is_whole(self) -> None:
        self.assertAlmostEqual(network.giant_component_fraction(np.zeros((4, 4), bool)), 0.25)
        self.assertAlmostEqual(network.giant_component_fraction(~np.eye(4, dtype=bool)), 1.0)

    def test_a_directed_edge_still_joins_its_nodes(self) -> None:
        adjacency = np.zeros((2, 2), bool)
        adjacency[0, 1] = True
        self.assertAlmostEqual(network.giant_component_fraction(adjacency), 1.0)


class SurrogateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = np.random.default_rng(1)

    def test_phase_randomisation_keeps_each_power_spectrum(self) -> None:
        x = self.rng.standard_normal((3, 256))
        s = network.phase_randomise(x, self.rng)
        np.testing.assert_allclose(np.abs(np.fft.rfft(s)), np.abs(np.fft.rfft(x)), rtol=1e-9, atol=1e-9)

    def test_common_phases_keep_the_correlations_exactly(self) -> None:
        x = factor_windows(np.array([0.6]), 4, 300, self.rng)[0]
        s = network.phase_randomise(x, self.rng, common=True)
        np.testing.assert_allclose(np.corrcoef(s), np.corrcoef(x), atol=1e-9)

    def test_independent_surrogates_give_the_white_noise_quantile(self) -> None:
        n = 400
        x = self.rng.standard_normal((30, n))
        threshold = network.surrogate_correlation_threshold(x, EdgeTest(SurrogateSpec(0.01, 20), self.rng))
        self.assertAlmostEqual(threshold, WHITE_NOISE_Z99 / np.sqrt(n), delta=0.15 * WHITE_NOISE_Z99 / np.sqrt(n))


class ShapeFitTests(unittest.TestCase):
    def test_noiseless_sigmoid_returns_its_midpoint_and_width(self) -> None:
        c = np.linspace(0, 3, 60)
        s = Logistic(0.1, 0.95, 1.6, threshold_shape.width_to_steepness(0.4))(c)
        fit = threshold_shape.fit_shape(c, s)
        self.assertAlmostEqual(fit.c50, 1.6, places=3)
        self.assertAlmostEqual(fit.width, 0.4, places=3)
        self.assertTrue(fit.sigmoid_preferred)

    def test_a_straight_line_is_not_called_a_threshold(self) -> None:
        rng = np.random.default_rng(2)
        c = np.linspace(0, 3, 60)
        s = 0.9 - 0.2 * c + rng.normal(0, 0.02, c.size)
        self.assertFalse(threshold_shape.fit_shape(c, s).sigmoid_preferred)

    def test_steepness_and_width_are_inverse(self) -> None:
        self.assertAlmostEqual(threshold_shape.steepness_to_width(threshold_shape.width_to_steepness(0.7)), 0.7)

    def test_null_p_value_counts_the_observed_value_itself(self) -> None:
        result = threshold_shape.steepness_against_null(10.0, np.array([1.0, 2.0, 3.0, 11.0]))
        self.assertAlmostEqual(result["p_value"], 2 / 5)
        self.assertAlmostEqual(result["ratio_to_null_median"], 10.0 / 2.5)

    def test_shape_fit_needs_enough_windows(self) -> None:
        with self.assertRaises(ValueError):
            threshold_shape.fit_shape(np.arange(4.0), np.arange(4.0))

    def test_sigmoid_preference_uses_the_bic_margin(self) -> None:
        self.assertTrue(ShapeFit(1, 1, 1, 0, 1, -10.0).sigmoid_preferred)
        self.assertFalse(ShapeFit(1, 1, 1, 0, 1, -9.9).sigmoid_preferred)


class SmoothDeclineNullTests(unittest.TestCase):
    """The control asked for by the clinical reviewer: thresholding a smooth decline must not pass as a threshold."""

    n_nodes, n_samples, n_windows, realisations = 24, 75, 36, 40

    def run_pipeline(self, coupling: np.ndarray, seed: int) -> dict:
        rng = np.random.default_rng(seed)
        c = np.linspace(0, 3, self.n_windows)
        windows = factor_windows(coupling, self.n_nodes, self.n_samples, rng)
        observed = np.array([network.correlation_network(w, EdgeTest(SurrogateSpec(0.01, 10), rng))["giant_component"] for w in windows])
        awake = [network.zscore_rows(w) for w, ci in zip(windows, c) if ci < 0.5]
        targets = threshold_shape.linear_decline(c, coupling[0], coupling[-1])
        fractions = threshold_shape.mixing_fractions(targets, coupling[0])
        null = [
            threshold_shape.fit_shape(c, threshold_shape.null_giant_components(awake, fractions, EdgeTest(SurrogateSpec(0.01, 10), rng))).steepness
            for _ in range(self.realisations)
        ]
        return threshold_shape.steepness_against_null(threshold_shape.fit_shape(c, observed).steepness, np.array(null))

    def test_declining_surrogate_scales_the_reference_correlation(self) -> None:
        rng = np.random.default_rng(3)
        reference = factor_windows(np.array([0.8]), 2, 4000, rng)[0]
        surrogate = threshold_shape.declining_surrogate(reference, 0.5, rng)
        self.assertAlmostEqual(np.corrcoef(surrogate)[0, 1], 0.5 * np.corrcoef(reference)[0, 1], delta=0.05)

    def test_a_linear_decline_in_coupling_does_not_beat_its_own_null(self) -> None:
        coupling = np.linspace(0.30, 0.0, self.n_windows)
        self.assertGreater(self.run_pipeline(coupling, 4)["p_value"], 0.05)

    def test_an_abrupt_collapse_in_coupling_beats_the_linear_null(self) -> None:
        coupling = np.where(np.linspace(0, 3, self.n_windows) < 1.5, 0.30, 0.0)
        self.assertLess(self.run_pipeline(coupling, 5)["p_value"], 0.05)


if __name__ == "__main__":
    unittest.main()
