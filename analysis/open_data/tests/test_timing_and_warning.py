"""Phase and lag measures, early-warning indicators and the effect-site model, on data whose answer is known."""

from __future__ import annotations

import unittest

import numpy as np

from analysis.open_data import early_warning, hysteresis, phase
from analysis.open_data.hysteresis import EffectSiteModel
from analysis.open_data.phase import PairedSignals
from analysis.open_data.settings import Band
from analysis.open_data.specs import FilterSpec, LineNoise

FS = 1000.0
F0 = 40.0


def oscillators(n_samples: int, lag_ms_per_window: np.ndarray, window: int, rng: np.random.Generator, noise: float = 0.0) -> np.ndarray:
    """Two 40 Hz analytic signals; the second lags the first by the given amount in each window."""
    t = np.arange(n_samples) / FS
    lag = np.repeat(lag_ms_per_window, window)[:n_samples] / 1000.0
    a = np.exp(2j * np.pi * F0 * t)
    b = np.exp(2j * np.pi * F0 * (t - lag))
    if noise:
        a = a + noise * (rng.standard_normal(n_samples) + 1j * rng.standard_normal(n_samples))
        b = b + noise * (rng.standard_normal(n_samples) + 1j * rng.standard_normal(n_samples))
    return np.stack([a, b])


class LagTests(unittest.TestCase):
    window = 1000

    def test_constant_lag_has_its_mean_and_no_variability(self) -> None:
        z = oscillators(20 * self.window, np.full(20, 5.0), self.window, np.random.default_rng(0))
        stats = phase.lag_statistics(phase.windowed_phase_differences(PairedSignals(z, [(0, 1)]), self.window), F0)
        self.assertAlmostEqual(stats["mean_lag_ms"][0], 5.0, places=6)
        self.assertAlmostEqual(stats["lag_variability_ms"][0], 0.0, places=4)

    def test_jittered_lag_returns_the_jitter_and_keeps_the_mean(self) -> None:
        rng = np.random.default_rng(1)
        jitter_ms = 2.0
        lags = 3.0 + rng.normal(0, jitter_ms, 400)
        z = oscillators(400 * self.window, lags, self.window, rng)
        stats = phase.lag_statistics(phase.windowed_phase_differences(PairedSignals(z, [(0, 1)]), self.window), F0)
        self.assertAlmostEqual(stats["lag_variability_ms"][0], jitter_ms, delta=0.15 * jitter_ms)
        self.assertAlmostEqual(stats["mean_lag_ms"][0], 3.0, delta=0.3)

    def test_wpli_is_blind_to_zero_lag_coupling_that_plv_sees(self) -> None:
        rng = np.random.default_rng(2)
        z = oscillators(20 * self.window, np.zeros(20), self.window, rng, noise=0.3)
        self.assertGreater(phase.plv(PairedSignals(z, [(0, 1)]))[0], 0.8)
        self.assertLess(phase.wpli(PairedSignals(z, [(0, 1)]))[0], 0.2)

    def test_wpli_detects_coupling_at_a_quarter_cycle(self) -> None:
        rng = np.random.default_rng(3)
        z = oscillators(20 * self.window, np.full(20, 1000.0 / F0 / 4), self.window, rng, noise=0.3)
        self.assertGreater(phase.wpli(PairedSignals(z, [(0, 1)]))[0], 0.9)


class MontageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.xy = np.array([[x, y] for y in range(3) for x in range(4)], float) * np.array([1.0, 1.5])

    def test_nearest_neighbours_on_a_grid_are_horizontal_and_unique(self) -> None:
        pairs = phase.nearest_neighbour_pairs(self.xy)
        self.assertEqual(len(pairs), len(set(pairs)))
        for a, b in pairs:
            self.assertAlmostEqual(np.linalg.norm(self.xy[a] - self.xy[b]), 1.0)

    def test_long_range_pairs_share_no_electrode_and_are_far(self) -> None:
        pairs = phase.nearest_neighbour_pairs(self.xy)
        _, mid = phase.bipolar(np.zeros((12, 1)), self.xy, pairs)
        far = phase.long_range_pairs(mid, pairs, 0.5)
        self.assertTrue(far)
        distances = [np.linalg.norm(mid[i] - mid[j]) for i, j in far]
        all_distances = [np.linalg.norm(mid[i] - mid[j]) for i in range(len(mid)) for j in range(i + 1, len(mid))]
        self.assertGreaterEqual(min(distances), np.quantile(all_distances, 0.5) * 0.99)
        for i, j in far:
            self.assertFalse(set(pairs[i]) & set(pairs[j]))


class FilterTests(unittest.TestCase):
    def test_band_pass_keeps_in_band_and_removes_out_of_band(self) -> None:
        t = np.arange(10000) / FS
        gamma = Band("gamma", 30.0, 45.0)
        inside = phase.bandpass(np.sin(2 * np.pi * 38 * t), gamma, FilterSpec(FS, 4))
        outside = phase.bandpass(np.sin(2 * np.pi * 10 * t), gamma, FilterSpec(FS, 4))
        self.assertAlmostEqual(inside[2000:-2000].std() * np.sqrt(2), 1.0, delta=0.05)
        self.assertLess(outside[2000:-2000].std(), 0.01)

    def test_line_noise_is_removed(self) -> None:
        t = np.arange(10000) / FS
        cleaned = phase.remove_line_noise(np.sin(2 * np.pi * 50 * t), FS, LineNoise((50.0,), 30.0))
        self.assertLess(cleaned[2000:-2000].std(), 0.05)


class EarlyWarningTests(unittest.TestCase):
    def ar1(self, coefficients: np.ndarray, rng: np.random.Generator) -> np.ndarray:
        x = np.zeros(coefficients.size)
        for t in range(1, x.size):
            x[t] = coefficients[t] * x[t - 1] + rng.standard_normal()
        return x

    def test_slowing_down_is_detected(self) -> None:
        rng = np.random.default_rng(4)
        series = self.ar1(np.linspace(0.1, 0.95, 600), rng)
        result = early_warning.critical_slowing_test(series, rng, n_surrogates=200)
        for name in ("variance", "autocorrelation"):
            self.assertGreater(result[name]["tau"], 0.5)
            self.assertLess(result[name]["p_value"], 0.05)

    def test_a_stationary_series_shows_no_significant_rise_in_both(self) -> None:
        rng = np.random.default_rng(5)
        series = self.ar1(np.full(600, 0.5), rng)
        result = early_warning.critical_slowing_test(series, rng, n_surrogates=200)
        self.assertTrue(result["variance"]["p_value"] > 0.05 or result["autocorrelation"]["p_value"] > 0.05)

    def test_too_short_a_series_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            early_warning.indicator_trends(np.arange(10.0))


class EffectSiteTests(unittest.TestCase):
    def test_step_in_plasma_gives_the_exponential_approach(self) -> None:
        ke0, dt = 0.456, 0.8
        effect = hysteresis.effect_site_from_plasma(np.full(500, 2.0), EffectSiteModel(ke0, dt))
        t_minutes = np.arange(500) * dt / 60
        np.testing.assert_allclose(effect, 2.0 * (1 - np.exp(-ke0 * t_minutes)), rtol=1e-12, atol=1e-12)

    def test_faster_equilibration_follows_plasma_more_closely(self) -> None:
        plasma = np.r_[np.full(200, 3.0), np.zeros(200)]
        slow = hysteresis.effect_site_from_plasma(plasma, EffectSiteModel(0.2, 0.8))
        fast = hysteresis.effect_site_from_plasma(plasma, EffectSiteModel(1.21, 0.8))
        self.assertLess(np.abs(fast - plasma).mean(), np.abs(slow - plasma).mean())

    def test_ratio_and_lookup(self) -> None:
        self.assertAlmostEqual(hysteresis.hysteresis_ratio(1.6, 1.0), 1.6)
        self.assertIsNone(hysteresis.concentration_at(np.arange(3.0), None))
        with self.assertRaises(IndexError):
            hysteresis.concentration_at(np.arange(3.0), 3)


if __name__ == "__main__":
    unittest.main()
