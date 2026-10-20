"""Classification, family-wise statistics, verdicts and evoked-response latency, on cases whose answer is known."""

from __future__ import annotations

import unittest

import numpy as np

from analysis.open_data import classification, evoked_latency, group, stats, verdicts
from analysis.open_data.classification import Grouping
from analysis.open_data.evoked_latency import LatencyWindow
from analysis.open_data.specs import Resampling
from analysis.open_data.stats import Evidence
from analysis.open_data.settings import HYSTERESIS


class AucTests(unittest.TestCase):
    def test_perfect_reversed_and_tied(self) -> None:
        self.assertEqual(classification.auc(np.array([3, 4]), np.array([1, 2])), 1.0)
        self.assertEqual(classification.auc(np.array([1, 2]), np.array([3, 4])), 0.0)
        self.assertEqual(classification.auc(np.array([1, 1]), np.array([1, 1])), 0.5)

    def test_direction_learned_elsewhere_fails_on_an_agent_that_moves_the_other_way(self) -> None:
        agents = np.repeat(["a", "b", "c"], 4)
        state = np.tile([False, False, True, True], 3)
        consistent = np.where(state, 2.0, 0.0) + np.tile([0, 0.1, 0, 0.1], 3)
        flipped = consistent.copy()
        flipped[agents == "c"] = np.where(state[agents == "c"], 0.0, 2.0)
        self.assertEqual(classification.leave_one_agent_out_auc(consistent, state, agents)["mean"], 1.0)
        result = classification.leave_one_agent_out_auc(flipped, state, agents)
        self.assertEqual(result["c"], 0.0)
        self.assertLess(result["mean"], 1.0)

    def test_session_bootstrap_resamples_within_agents(self) -> None:
        sessions = np.array(["s1", "s1", "s2", "s3"])
        agents = np.array(["a", "a", "a", "b"])
        draws = classification.session_bootstrap(lambda rows: float(np.sum(agents[rows] == "b")), Grouping(sessions, agents), Resampling(50, np.random.default_rng(0)))
        self.assertTrue(np.all(draws == 1.0))


class StatsTests(unittest.TestCase):
    def test_holm_matches_a_worked_example(self) -> None:
        adjusted = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertAlmostEqual(adjusted["a"], 0.03)
        self.assertAlmostEqual(adjusted["c"], 0.06)
        self.assertAlmostEqual(adjusted["b"], 0.06)

    def test_equivalence_is_shown_only_for_values_inside_the_bounds(self) -> None:
        rng = np.random.default_rng(1)
        self.assertLess(stats.tost_p(rng.normal(0, 0.1, 40), -0.2, 0.2), 0.05)
        self.assertGreater(stats.tost_p(rng.normal(0.5, 0.1, 40), -0.2, 0.2), 0.5)

    def test_verdicts(self) -> None:
        self.assertEqual(stats.verdict(Evidence(0.01, 0.3, 0.2, 0.9)), stats.Verdict.SUPPORTS)
        self.assertEqual(stats.verdict(Evidence(0.01, 0.1, 0.2, 0.9)), stats.Verdict.INCONCLUSIVE)
        self.assertEqual(stats.verdict(Evidence(0.6, 0.0, 0.2, 0.01)), stats.Verdict.AGAINST)
        self.assertEqual(stats.verdict(Evidence(0.9, -0.3, 0.2, 0.9)), stats.Verdict.AGAINST)


class GroupTests(unittest.TestCase):
    def test_h1_intact_giant_component_counts_against_whatever_the_steepness(self) -> None:
        subjects = [
            {"null_a_linear_decline": {"ratio_to_null_median": 3.0}, "post_lor_share_of_awake": 0.95, "observed": {"delta_bic": -20}, "coupling_deep_over_awake": 0.5}
            for _ in range(12)
        ]
        primary = {"H1": group.h1_threshold(subjects)}
        self.assertEqual(verdicts.family_verdicts(primary)["H1"]["verdict"], stats.Verdict.AGAINST.value)

    def test_h1_steep_at_the_primary_threshold_only_is_not_supported(self) -> None:
        rng = np.random.default_rng(6)
        subjects = []
        for _ in range(20):
            ratio = float(np.exp(rng.normal(1.0, 0.1)))
            subjects.append({
                "null_a_linear_decline": {"ratio_to_null_median": ratio},
                "post_lor_share_of_awake": 0.3,
                "observed": {"delta_bic": -20},
                "coupling_deep_over_awake": 0.5,
                "sensitivity": {
                    "alpha=0.001": {"null_a_linear_decline": {"ratio_to_null_median": ratio}},
                    "alpha=0.05": {"null_a_linear_decline": {"ratio_to_null_median": float(np.exp(rng.normal(-0.2, 0.1)))}},
                },
            })
        result = verdicts.family_verdicts({"H1": group.h1_threshold(subjects)})["H1"]
        self.assertEqual(result["verdict"], stats.Verdict.INCONCLUSIVE.value)
        for s in subjects:
            s["sensitivity"]["alpha=0.05"]["null_a_linear_decline"]["ratio_to_null_median"] = s["null_a_linear_decline"]["ratio_to_null_median"]
        self.assertEqual(verdicts.family_verdicts({"H1": group.h1_threshold(subjects)})["H1"]["verdict"], stats.Verdict.SUPPORTS.value)

    def test_h1_is_not_evaluable_when_bold_coupling_does_not_fall(self) -> None:
        subjects = [
            {"null_a_linear_decline": {"ratio_to_null_median": 0.5}, "post_lor_share_of_awake": 0.95, "observed": {"delta_bic": 5}, "coupling_deep_over_awake": 0.97}
            for _ in range(12)
        ]
        self.assertEqual(verdicts.family_verdicts({"H1": group.h1_threshold(subjects)})["H1"]["verdict"], verdicts.NOT_EVALUABLE)

    def test_h4_needs_every_ke0_to_hold(self) -> None:
        variants = ["provided", *(f"ke0={k}" for k in HYSTERESIS.ke0_per_minute)]
        rng = np.random.default_rng(2)
        subjects = []
        for _ in range(20):
            s = {v: {"network_ratio": float(np.exp(rng.normal(0.3, 0.05))), "behavioural_ratio": 1.2} for v in variants}
            s["ke0=1.21"]["network_ratio"] = float(np.exp(rng.normal(0.0, 0.05)))
            subjects.append(s)
        result = verdicts.family_verdicts({"H4": group.h4_hysteresis(subjects)})["H4"]
        self.assertNotEqual(result["verdict"], stats.Verdict.SUPPORTS.value)


class LagVariabilityGroupTests(unittest.TestCase):
    """H3 on blocks shaped like the Neurotycho output: variability rises with every agent, power flips with one."""

    def blocks(self, rng: np.random.Generator) -> list[dict]:
        rows = []
        for agent, power_sign in (("propofol", -1), ("ketamine", 1), ("medetomidine", -1), ("ketamine-medetomidine", -1)):
            for session in range(3):
                for state in ("awake", "anaesthetised"):
                    shift = 1.0 if state == "anaesthetised" else 0.0
                    for _ in range(10):
                        rows.append({
                            "agent": agent, "session_id": f"{agent}-{session}", "state": state,
                            "lag_variability_ms_z": 2 * shift + rng.normal(0, 0.5),
                            "mean_lag_ms_z": rng.normal(0, 0.5),
                            "log_power_z": power_sign * 2 * shift + rng.normal(0, 0.5),
                        })
        return rows

    def test_variability_that_generalises_across_agents_beats_power_that_does_not(self) -> None:
        result = group.h3_lag_variability(self.blocks(np.random.default_rng(5)), n_resamples=200)
        self.assertGreater(result["effect"], 0.1)
        self.assertLess(result["p_value"], 0.05)
        self.assertLess(result["per_feature_auc"]["log_power"]["ketamine"], 0.1)
        self.assertEqual(verdicts.family_verdicts({"H3": result})["H3"]["verdict"], stats.Verdict.SUPPORTS.value)


class LatencyTests(unittest.TestCase):
    fs = 2048.0

    def trials(self, jitter_ms: float, latency_ms: float, n: int, rng: np.random.Generator) -> np.ndarray:
        t = np.arange(int(0.3 * self.fs)) / self.fs * 1000.0
        rows = []
        for shift in rng.normal(0, jitter_ms, n):
            rows.append(-np.exp(-0.5 * ((t - latency_ms - shift) / 6.0) ** 2) + rng.normal(0, 0.02, t.size))
        return np.stack(rows)

    def test_single_trial_jitter_is_recovered(self) -> None:
        rng = np.random.default_rng(3)
        trials = self.trials(3.0, 120.0, 200, rng)
        start, end = int(0.06 * self.fs), int(0.2 * self.fs)
        result = evoked_latency.connection_latency(trials, LatencyWindow(self.fs, start, end, int(0.02 * self.fs)))
        self.assertAlmostEqual(result["latency_sd_ms"], 3.0, delta=0.5)
        self.assertAlmostEqual(result["mean_latency_ms"], 120.0, delta=1.0)

    def test_relative_change_is_positive_when_only_variability_rises(self) -> None:
        awake = {"latency_sd_ms": 2.0, "mean_latency_ms": 25.0}
        drugged = {"latency_sd_ms": 4.0, "mean_latency_ms": 25.0}
        self.assertAlmostEqual(evoked_latency.relative_change(awake, drugged), np.log(2.0))

    def test_first_spike_latency_and_missing_spikes(self) -> None:
        latencies = evoked_latency.first_spike_latencies(np.array([1.005, 1.010, 2.2]), np.array([1.0, 2.0]), (0.002, 0.05))
        self.assertAlmostEqual(latencies[0], 0.005)
        self.assertTrue(np.isnan(latencies[1]))

    def test_robust_sd_of_a_normal_sample(self) -> None:
        self.assertAlmostEqual(evoked_latency.robust_sd(np.random.default_rng(4).normal(0, 2.0, 20000)), 2.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
