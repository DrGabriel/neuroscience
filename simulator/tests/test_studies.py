"""Tests for the reporting helpers, percolation formulas, Wilson-Cowan model and study checks.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
Tests that need a downloaded dataset are skipped when it is absent.
"""

from __future__ import annotations

import math
import random
import unittest
from dataclasses import replace

import numpy as np

import calibration as cal
import congestion_study
import connectomes
import dpc_simulator as dpc
import excitatory_inhibitory as ei
import percolation_thresholds as thresholds
import reporting
import sensitivity_study
import validation_study

MEAN_DEGREE = 10.0
RANDOM_GRAPH = dpc.RandomGraphBuilder(20_000, MEAN_DEGREE).build(random.Random(1))


class ReportingTests(unittest.TestCase):
    def test_describe_reports_mean_spread_and_undefined_share(self) -> None:
        self.assertEqual(reporting.describe([1.0, 3.0]), "2.000 ± 1.414")
        self.assertEqual(reporting.describe([1.0, None]), "1.000 ± 0.000 (1/2)")
        self.assertEqual(reporting.describe([None]), "not reached (0/1)")

    def test_outcome_table_marks_groups_without_runs(self) -> None:
        check = reporting.Check("X", "always true", lambda run: True)
        outcomes = reporting.evaluate([check], {"A": [1, 2], "B": []})
        table = reporting.outcome_table(outcomes, ["A", "B"])
        self.assertIn("| X | always true | test | 2/2 (34–100%) | not run |", table)

    def test_consistency_checks_are_labelled(self) -> None:
        check = reporting.Check("Y", "follows from the equations", lambda run: True, reporting.CONSISTENCY_CHECK)
        outcome = reporting.evaluate([check], {"A": [1]})[0]
        self.assertEqual(outcome.kind, reporting.CONSISTENCY_CHECK)

    def test_wilson_interval_matches_published_values(self) -> None:
        low, high = reporting.wilson_interval(0, 20)
        self.assertAlmostEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.1611, places=3)
        low, high = reporting.wilson_interval(20, 20)
        self.assertAlmostEqual(low, 0.8389, places=3)


class DirectedAndNullModelTests(unittest.TestCase):
    def test_a_one_way_cycle_is_strongly_connected_but_a_chain_is_not(self) -> None:
        cycle = replace(_tiny_connectome(), sources=np.array([0, 1, 2]), targets=np.array([1, 2, 0]), weights=np.ones(3, dtype=np.float32))
        chain = replace(cycle, sources=np.array([0, 1]), targets=np.array([1, 2]), weights=np.ones(2, dtype=np.float32))
        self.assertEqual(thresholds.largest_strong_component_share(cycle, np.ones(3, dtype=bool)), 1.0)
        self.assertAlmostEqual(thresholds.largest_strong_component_share(chain, np.ones(2, dtype=bool)), 1 / 3)

    def test_rewiring_keeps_out_degrees_and_removes_self_connections(self) -> None:
        connectome = replace(_tiny_connectome(), sources=np.array([0, 0, 1, 2]), targets=np.array([1, 2, 2, 0]), weights=np.ones(4, dtype=np.float32))
        rewired = connectome.rewired(seed=3)
        self.assertFalse(np.any(rewired.sources == rewired.targets))
        self.assertTrue(np.all(np.bincount(rewired.sources, minlength=3) <= np.bincount(connectome.sources, minlength=3)))


def _tiny_connectome() -> connectomes.Connectome:
    return connectomes.Connectome(
        name="tiny", organism="test", node_count=3, sources=np.array([0]), targets=np.array([1]), weights=np.ones(1, dtype=np.float32),
        modules=np.zeros(3, dtype=int), module_basis="none", sensory_nodes=np.array([0]), sensory_description="node 0",
    )


class PercolationFormulaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.degrees = np.asarray(RANDOM_GRAPH.degrees(), dtype=float)

    def test_onset_threshold_of_a_random_graph_is_the_inverse_mean_degree(self) -> None:
        _, _, onset = thresholds.onset_threshold(self.degrees)
        self.assertAlmostEqual(onset, 1 / MEAN_DEGREE, delta=0.005)

    def test_giant_fraction_matches_the_poisson_self_consistency(self) -> None:
        occupation = 0.3
        expected = 0.5
        for _ in range(500):
            expected = 1 - math.exp(-MEAN_DEGREE * occupation * expected)
        self.assertAlmostEqual(thresholds.DegreeDistribution.of(self.degrees).giant_fraction(occupation), expected, delta=0.01)

    def test_quorum_formula_predicts_the_measured_threshold(self) -> None:
        formula = thresholds.DegreeDistribution.of(self.degrees).quorum_threshold(cal.QUORUM_FRACTION)
        measured = thresholds.quorum_threshold_measured(RANDOM_GRAPH, cal.QUORUM_FRACTION, seed=1)
        self.assertAlmostEqual(formula, measured, delta=0.01)

    def test_critical_jitter_reproduces_the_threshold_occupation(self) -> None:
        threshold = 0.04
        jitter = thresholds.critical_jitter_ms(threshold)
        occupation = math.erf(dpc.REFERENCE_INTEGRATION_WINDOW_MS / (2 * math.sqrt(2) * jitter))
        self.assertAlmostEqual(occupation, threshold, places=6)


def tiny_connectome(node_count: int = 12) -> connectomes.Connectome:
    sources, targets = np.nonzero(~np.eye(node_count, dtype=bool))
    return connectomes.Connectome(
        name="tiny",
        organism="synthetic",
        node_count=node_count,
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=np.ones(sources.size, dtype=np.float32),
        modules=np.zeros(node_count, dtype=np.int32),
        module_basis="synthetic",
        sensory_nodes=np.arange(2, dtype=np.int32),
        sensory_description="first two nodes",
        lengths_mm=np.full(sources.size, 20.0, dtype=np.float32),
    )


class WilsonCowanTests(unittest.TestCase):
    def design(self, **overrides: object) -> ei.CongestionDesign:
        base = replace(congestion_study.QUICK_DESIGN, grid=dpc.ConcentrationGrid(2.0, 1.0), hold_s=0.5, balancing_s=1.0)
        return replace(base, **overrides)

    def test_balancing_moves_excitatory_activity_towards_its_target(self) -> None:
        target = ei.LocalCircuit().target_excitatory_activity
        unbalanced = ei.WilsonCowanNetwork(tiny_connectome(), self.design(global_coupling=0.2)).hold_at(0.0)
        balanced_network = ei.WilsonCowanNetwork(tiny_connectome(), self.design(global_coupling=0.2, balancing_s=5.0))
        balanced_network.balance_awake_state()
        balanced = balanced_network.hold_at(0.0)
        self.assertLess(abs(balanced.mean_activity - target), abs(unbalanced.mean_activity - target))

    def test_failing_every_connection_lowers_hub_activity(self) -> None:
        sealed_agent = replace(cal.GABAERGIC_AGENT, max_transmission_failure=1.0)
        record = ei.run_induction(tiny_connectome(), self.design(agent=sealed_agent, global_coupling=2.0), 0.5)
        self.assertLess(record.measurements[-1].hub_activity, record.awake.hub_activity)

    def test_missing_tract_lengths_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ei.WilsonCowanNetwork(replace(tiny_connectome(), lengths_mm=None), self.design())


def measurement(concentration: float, synchrony: float, burstiness: float, interval: float | None) -> ei.CongestionMeasurement:
    return ei.CongestionMeasurement(concentration, 0.1, 0.1, synchrony, burstiness, interval)


class GracefulDegradationTests(unittest.TestCase):
    def test_coefficient_of_variation_of_a_constant_signal_is_zero(self) -> None:
        self.assertEqual(ei.coefficient_of_variation(np.full(10, 0.2)), 0.0)

    def test_burstiness_rise_and_lengthening_gaps_are_measured_from_the_surge(self) -> None:
        record = ei.InductionRecord(
            (measurement(0.0, 0.2, 0.1, 0.5), measurement(1.0, 0.6, 0.3, 0.4), measurement(2.0, 0.05, 0.2, 0.9)),
            collapse_fraction=0.5,
        )
        self.assertEqual(record.surge.concentration, 1.0)
        self.assertAlmostEqual(record.burstiness_rise_after_surge, 3.0)
        self.assertTrue(record.burst_gaps_lengthen)

    def test_gap_comparison_is_undefined_without_deeper_bursts(self) -> None:
        record = ei.InductionRecord(
            (measurement(0.0, 0.2, 0.1, 0.5), measurement(1.0, 0.6, 0.3, 0.4), measurement(2.0, 0.05, 0.0, None)),
            collapse_fraction=0.5,
        )
        self.assertIsNone(record.burst_gaps_lengthen)


class CongestionCheckTests(unittest.TestCase):
    def run_with(self, low: float, high: float) -> congestion_study.PairedRun:
        return congestion_study.PairedRun(
            compensation="none", global_coupling=1.0, seed=1,
            low_load_activity_ratio=low, high_load_activity_ratio=high,
            low_load_synchrony_surge=low, high_load_synchrony_surge=high,
            low_load_collapse=1.0, high_load_collapse=1.0, low_load_burstiness_rise=1.0, low_load_burst_gaps_lengthen=None,
            concentrations=(), low_load_burstiness=(), low_load_hub_activity=(), high_load_hub_activity=(), low_load_synchrony=(), high_load_synchrony=(),
        )

    def test_activity_rise_needs_ten_percent(self) -> None:
        self.assertFalse(congestion_study.activity_rises(self.run_with(1.05, 1.05)))
        self.assertTrue(congestion_study.activity_rises(self.run_with(1.12, 1.12)))

    def test_load_dependence_requires_a_larger_rise_at_high_load(self) -> None:
        self.assertTrue(congestion_study.rise_grows_with_load(self.run_with(1.1, 1.2)))
        self.assertFalse(congestion_study.rise_grows_with_load(self.run_with(1.2, 1.1)))


class SensitivityRuleTests(unittest.TestCase):
    def test_arousal_claims_are_undefined_without_arousal(self) -> None:
        without_arousal = sensitivity_study.with_arousal_level(0.0)
        measurement = validation_study.measure_seed(validation_study.SeedTask(302, cal.BASE_SEED), transform=without_arousal)
        verdicts = {claim.identifier: claim.holds_for(measurement) for claim in validation_study.CLAIMS}
        self.assertIsNone(verdicts["C6"])
        self.assertIsNone(verdicts["C7"])
        self.assertIsNotNone(verdicts["C1"])

    def test_mean_degree_change_keeps_the_graph_type(self) -> None:
        changed = sensitivity_study.with_mean_degree(16.0)(dpc.HUB_SCENARIO)
        self.assertIsInstance(changed.graph_builder, dpc.PreferentialAttachmentGraphBuilder)
        self.assertEqual(changed.graph_builder.edges_per_new_node, 8)


class ReportAssemblyTests(unittest.TestCase):
    """Builds each study's report from synthetic results, so reporting errors fail fast, not after a long run."""

    def test_species_report_renders_from_synthetic_runs(self) -> None:
        import species_study

        run = species_study.RunSummary(
            organism="celegans", condition=species_study.ConditionName.GABAERGIC, seed=1,
            loss_concentration=1.0, recovery_concentration=0.9, hysteresis_width=0.1, susceptibility_surge=20.0,
            susceptibility_peak_concentration=1.0, local_global_dissociation=0.0, awake_broadcast_ratio=None,
            unconscious_broadcast_ratio=None, awake_sensory_entrainment=None, unconscious_sensory_entrainment=None,
            awake_susceptibility=0.1, loss_susceptibility=2.0, deepest_coherence_fraction=0.1, deepest_broadcast_ratio=None,
            concentrations=(0.0, 1.0), induction_coherence=(1.0, 0.1), emergence_coherence=(1.0, 0.1),
            induction_susceptibility=(0.1, 2.0), induction_broadcast_ratio=(None, None), seconds=1.0,
        )
        plant = species_study.PlantSummary(junction_conductance=cal.PLANT_JUNCTION_CONDUCTANCES[0], seed=1, block_open_fraction=0.8)
        results = species_study.SpeciesResults("smoke", "2026-01-01T00:00:00+00:00", {}, [run], [plant])
        report = species_study.assemble_report(results)
        markdown = species_study.to_markdown(report)
        self.assertIn("### Pillars", markdown)
        self.assertIn("Dataset", markdown)


class FallbackComparisonTests(unittest.TestCase):
    def test_gains_and_the_jitter_comparison(self) -> None:
        import species_study

        comparison = species_study.FallbackComparison("human", 1, 1.0, 1.1, 0.6, 0.8)
        self.assertAlmostEqual(comparison.gabaergic_gain, 0.1)
        self.assertAlmostEqual(comparison.nmda_gain, 0.2)
        self.assertTrue(species_study.larger_gain_against_jitter(comparison))

    def test_comparison_is_undefined_when_a_loss_is_missing(self) -> None:
        import species_study

        comparison = species_study.FallbackComparison("human", 1, None, 1.1, 0.6, 0.8)
        self.assertIsNone(species_study.larger_gain_against_jitter(comparison))


class FlyWireTests(unittest.TestCase):
    @unittest.skipUnless(connectomes.DROSOPHILA.path.exists(), "FlyWire data not downloaded")
    def test_flywire_matches_the_published_connection_count(self) -> None:
        fly = connectomes.load_drosophila(cal.CONNECTOME_SEED)
        self.assertEqual(fly.node_count, 138_639)
        self.assertEqual(fly.edge_count, 2_700_513)
        self.assertGreater(fly.sensory_nodes.size, 0)


if __name__ == "__main__":
    unittest.main()
