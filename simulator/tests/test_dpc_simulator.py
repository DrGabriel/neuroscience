"""Unit and integration tests for the DPC reference simulator and validation study.

Run from the simulator directory: python3 -m unittest discover -s tests -t .
"""

from __future__ import annotations

import random
import re
import unittest
from dataclasses import replace
from pathlib import Path

import dpc_simulator as dpc
import validation_study as study

SMALL_NODE_COUNT = 1_000
SIMULATOR_DIRECTORY = Path(__file__).resolve().parent.parent
PAPER_PATH = SIMULATOR_DIRECTORY.parent / "white_paper_anesthesia_consensus.md"


def small(scenario: dpc.Scenario) -> dpc.Scenario:
    return replace(scenario, graph_builder=scenario.graph_builder.resized(SMALL_NODE_COUNT))


def path_graph(node_count: int) -> dpc.Graph:
    return dpc.Graph(node_count, tuple((node, node + 1) for node in range(node_count - 1)))


class DisjointSetTests(unittest.TestCase):
    def test_tracks_largest_component_across_unions(self) -> None:
        components = dpc.DisjointSet(5)
        components.union(0, 1)
        components.union(2, 3)
        components.union(1, 3)
        self.assertEqual(components.largest_component_size, 4)

    def test_repeated_union_does_not_grow_component(self) -> None:
        components = dpc.DisjointSet(3)
        components.union(0, 1)
        components.union(1, 0)
        self.assertEqual(components.largest_component_size, 2)


class GraphTests(unittest.TestCase):
    def test_random_graph_has_requested_mean_degree(self) -> None:
        graph = dpc.RandomGraphBuilder(SMALL_NODE_COUNT, mean_degree=8.0).build(random.Random(1))
        self.assertAlmostEqual(sum(graph.degrees()) / graph.node_count, 8.0, places=6)

    def test_preferential_attachment_produces_hubs(self) -> None:
        graph = dpc.PreferentialAttachmentGraphBuilder(SMALL_NODE_COUNT, edges_per_new_node=4).build(random.Random(1))
        degrees = graph.degrees()
        self.assertGreater(max(degrees), 5 * sum(degrees) / len(degrees))

    def test_lesion_removes_every_edge_touching_removed_nodes(self) -> None:
        lesioned = path_graph(4).without_nodes({1})
        self.assertEqual(lesioned.edges, ((2, 3),))
        self.assertEqual(lesioned.node_count, 4)


class PercolationCurveTests(unittest.TestCase):
    def test_no_occupied_edges_leaves_isolated_nodes(self) -> None:
        curve = dpc.PercolationCurve.from_graph(path_graph(10), random.Random(1))
        self.assertAlmostEqual(curve.giant_fraction(0.0), 0.1)

    def test_all_edges_occupied_connects_whole_path(self) -> None:
        curve = dpc.PercolationCurve.from_graph(path_graph(10), random.Random(1))
        self.assertAlmostEqual(curve.giant_fraction(1.0), 1.0)

    def test_random_graph_percolates_near_inverse_mean_degree(self) -> None:
        mean_degree = 8.0
        graph = dpc.RandomGraphBuilder(20_000, mean_degree).build(random.Random(1))
        curve = dpc.PercolationCurve.from_graph(graph, random.Random(2))
        critical = 1 / mean_degree
        self.assertLess(curve.giant_fraction(0.5 * critical), 0.01)
        self.assertGreater(curve.giant_fraction(2.0 * critical), 0.5)


class AnaestheticAgentTests(unittest.TestCase):
    def test_half_effect_at_half_effect_concentration(self) -> None:
        self.assertAlmostEqual(dpc.GABAERGIC_LIKE_AGENT.effect_fraction(1.0), 0.5)

    def test_no_effect_without_agent(self) -> None:
        self.assertEqual(dpc.GABAERGIC_LIKE_AGENT.transmission_failure(0.0), 0.0)
        self.assertEqual(dpc.NMDA_ANTAGONIST_LIKE_AGENT.added_jitter_ms(0.0), 0.0)


def coherence_model(state: dpc.BrainState = dpc.REFERENCE_SCENARIO.state) -> dpc.CoherenceModel:
    return dpc.CoherenceModel(dpc.REFERENCE_SCENARIO.timing, dpc.GABAERGIC_LIKE_AGENT, state)


class CoherenceModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = coherence_model()

    def test_coherence_falls_with_concentration(self) -> None:
        self.assertGreater(self.model.coherence_probability(0.5, 1.0), self.model.coherence_probability(1.5, 1.0))

    def test_shrinking_core_increases_jitter(self) -> None:
        self.assertGreater(self.model.effective_jitter_ms(0.0, 0.0), self.model.effective_jitter_ms(0.0, 1.0))

    def test_arousal_reduces_the_reference_error_of_a_collapsed_core(self) -> None:
        drowsy, alert = coherence_model(dpc.BrainState(0.0)), coherence_model(dpc.BrainState(0.9))
        self.assertGreater(drowsy.reference_error_ms(0.0, 0.0), alert.reference_error_ms(0.0, 0.0))

    def test_agent_suppresses_arousal(self) -> None:
        self.assertLess(self.model.arousal(2.0), self.model.arousal(0.0))

    def test_connection_level_down_states_reduce_coherence_without_any_agent(self) -> None:
        sleeping = coherence_model(dpc.BrainState(0.0, 0.3, dpc.DownStates.CONNECTIONS))
        self.assertLess(sleeping.coherence_probability(0.0, 1.0), self.model.coherence_probability(0.0, 1.0))

    def test_population_level_down_states_leave_connection_coherence_alone(self) -> None:
        sleeping = coherence_model(dpc.BrainState(0.0, 0.3, dpc.DownStates.POPULATIONS))
        self.assertEqual(sleeping.coherence_probability(0.0, 1.0), coherence_model(dpc.BrainState(0.0)).coherence_probability(0.0, 1.0))

    def test_independent_timing_errors_combine_in_quadrature(self) -> None:
        awake_and_coherent = self.model.effective_jitter_ms(0.0, 1.0)
        self.assertAlmostEqual(awake_and_coherent, dpc.REFERENCE_BASELINE_JITTER_MS)
        collapsed = self.model.effective_jitter_ms(0.0, 0.0)
        reference_error = self.model.reference_error_ms(0.0, 0.0)
        self.assertAlmostEqual(collapsed, (dpc.REFERENCE_BASELINE_JITTER_MS**2 + reference_error**2) ** 0.5)


class SweepIntegrationTests(unittest.TestCase):
    def test_awake_at_zero_concentration(self) -> None:
        result = dpc.run_scenario(small(dpc.REFERENCE_SCENARIO))
        self.assertTrue(result.induction[0].is_conscious)

    def test_no_hysteresis_without_reference_feedback(self) -> None:
        scenario = small(dpc.REFERENCE_SCENARIO)
        no_feedback = replace(scenario, timing=replace(scenario.timing, feedback_jitter_ms=0.0))
        self.assertEqual(dpc.run_scenario(no_feedback).hysteresis_width, 0)

    def test_reference_feedback_produces_neural_inertia(self) -> None:
        result = dpc.run_scenario(small(dpc.REFERENCE_SCENARIO))
        self.assertGreater(result.hysteresis_width, 0)
        self.assertLess(result.recovery_concentration, result.loss_concentration)

    def test_both_agent_classes_lose_quorum(self) -> None:
        agents = (dpc.GABAERGIC_LIKE_AGENT, dpc.NMDA_ANTAGONIST_LIKE_AGENT)
        for agent, result in dpc.agent_comparison(small(dpc.REFERENCE_SCENARIO), agents):
            with self.subTest(agent=agent.name):
                self.assertIsNotNone(result.loss_concentration)

    def test_hub_lesion_lowers_threshold_more_than_random_lesion(self) -> None:
        lesions = dpc.lesion_comparison(small(dpc.HUB_SCENARIO), dpc.REFERENCE_LESION_FRACTION)
        self.assertLess(lesions["hub lesion"].loss_concentration, lesions["random lesion"].loss_concentration)

    def test_threshold_is_hysteresis_free_when_never_lost(self) -> None:
        never_lost = dpc.SweepResult(
            induction=(dpc.SweepPoint(0.0, 1.0, True),), emergence=(dpc.SweepPoint(0.0, 1.0, True),)
        )
        self.assertIsNone(never_lost.loss_concentration)
        self.assertIsNone(never_lost.hysteresis_width)


class SleepAndLossPointTests(unittest.TestCase):
    def test_silenced_populations_lower_the_coherent_fraction(self) -> None:
        sleeping = replace(small(dpc.REFERENCE_SCENARIO), state=dpc.BrainState(0.0, 0.3))
        self.assertLess(dpc.stable_states(sleeping, 0.0).from_awake, 1 - 0.3 + 1e-9)

    def test_silenced_share_for_sleep_is_where_quorum_is_first_lost(self) -> None:
        base = small(dpc.REFERENCE_SCENARIO)
        share = dpc.silenced_share_for_sleep(base, dpc.BrainState(0.0))
        just_below = replace(base, state=dpc.BrainState(0.0, share - 1 / 2**dpc.SILENCED_SHARE_BISECTION_STEPS))
        at_share = replace(base, state=dpc.BrainState(0.0, share))
        self.assertGreaterEqual(dpc.stable_states(just_below, 0.0).from_awake, base.quorum_fraction)
        self.assertLess(dpc.stable_states(at_share, 0.0).from_awake, base.quorum_fraction)

    def test_loss_point_reports_the_agent_effect_at_c_off(self) -> None:
        scenario = small(dpc.REFERENCE_SCENARIO)
        result = dpc.run_scenario(scenario)
        point = dpc.loss_point(scenario, result)
        self.assertEqual(point.concentration, result.loss_concentration)
        self.assertAlmostEqual(point.transmission_failure, scenario.agent.transmission_failure(result.loss_concentration))
        self.assertIsNone(dpc.loss_point(scenario, dpc.SweepResult((dpc.SweepPoint(0.0, 1.0, True),), ())))


class CalibrationTests(unittest.TestCase):
    def test_stored_feedback_still_reproduces_the_reference_inertia_ratio(self) -> None:
        import calibrate_feedback

        for arousal_level, feedback_ms in dpc.CALIBRATED_FEEDBACK_MS_BY_AROUSAL.items():
            with self.subTest(arousal_level=arousal_level):
                ratio = calibrate_feedback.mean_inertia_ratio(feedback_ms, arousal_level)
                self.assertAlmostEqual(ratio, calibrate_feedback.REFERENCE_TARGET.ratio, delta=calibrate_feedback.RATIO_TOLERANCE)


class ValidationStudyTests(unittest.TestCase):
    def test_trapped_state_counts_as_unbounded_inertia(self) -> None:
        trapped = study.ThresholdSummary(1.0, None, None, 0.1)
        self.assertEqual(study.inertia_width(trapped), float("inf"))
        self.assertTrue(study.is_trapped_unconscious(trapped))

    def test_distribution_reports_undefined_values(self) -> None:
        distribution = study.Distribution.of([1.0, None, 3.0])
        self.assertEqual((distribution.defined_count, distribution.total_count), (2, 3))
        self.assertAlmostEqual(distribution.mean, 2.0)

    def test_consistency_checks_hold_and_every_claim_is_decided(self) -> None:
        """Consistency checks follow from the equations; whether a test passes is a result, not a test of the code."""
        import reporting

        measurement = study.measure_seed(study.SeedTask(SMALL_NODE_COUNT, dpc.REFERENCE_SEED))
        for claim in study.CLAIMS + study.EXTENSION_TESTS + study.OBSERVATIONS:
            with self.subTest(claim=claim.identifier):
                verdict = claim.holds_for(measurement)
                self.assertIn(verdict, (True, False, None))
                if claim.kind == reporting.CONSISTENCY_CHECK:
                    self.assertTrue(verdict)


class ValidationEndToEndTests(unittest.TestCase):
    def test_quick_study_writes_both_reports(self) -> None:
        import contextlib
        import io
        import tempfile
        import unittest.mock

        import reporting

        with tempfile.TemporaryDirectory() as directory, unittest.mock.patch.object(reporting, "RESULTS_DIRECTORY", Path(directory)):
            with contextlib.redirect_stdout(io.StringIO()):
                exit_status = study.main(["--quick"])
            written = sorted(path.suffix for path in Path(directory).iterdir())
        self.assertIn(exit_status, (0, 1))
        self.assertEqual(written, [".json", ".md"])


class PaperAppendixTests(unittest.TestCase):
    """The code printed in the paper must be byte-identical to the code in the repository."""

    def embedded_block(self, file_name: str) -> str:
        paper = PAPER_PATH.read_text()
        match = re.search(rf"<!-- begin {re.escape(file_name)} -->\n```python\n(.*?)```\n<!-- end", paper, re.DOTALL)
        self.assertIsNotNone(match, f"{file_name} is not embedded in the paper")
        return match.group(1)

    def test_simulator_listing_matches_source(self) -> None:
        source = (SIMULATOR_DIRECTORY / "dpc_simulator.py").read_text()
        self.assertEqual(self.embedded_block("dpc_simulator.py"), source)

    def test_validation_listing_matches_source(self) -> None:
        source = (SIMULATOR_DIRECTORY / "validation_study.py").read_text()
        self.assertEqual(self.embedded_block("validation_study.py"), source)


if __name__ == "__main__":
    unittest.main()
