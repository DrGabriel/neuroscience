"""Tests for the glial regulation model (postulate P9) and its study."""

from __future__ import annotations

import contextlib
import io
import re
import tempfile
import unittest
import unittest.mock
from dataclasses import replace
from pathlib import Path

import dpc_simulator as dpc
import glial_regulation as glia
import glial_study
import paper_appendices
import provenance
import reporting
from validation_study import SeedTask, ThresholdSummary

SMALL_SCENARIO = replace(dpc.REFERENCE_SCENARIO, graph_builder=dpc.REFERENCE_SCENARIO.graph_builder.resized(1_000))
LOOP_GAIN = 0.5


class MyelinTests(unittest.TestCase):
    def test_intact_myelin_leaves_the_scenario_unchanged(self) -> None:
        self.assertEqual(glia.demyelinated(SMALL_SCENARIO, 1.0), SMALL_SCENARIO)

    def test_complete_loss_raises_baseline_jitter_by_the_gain(self) -> None:
        jitter = glia.demyelinated(SMALL_SCENARIO, 0.0).timing.baseline_jitter_ms
        expected = SMALL_SCENARIO.timing.baseline_jitter_ms * (1 + glia.DEMYELINATION_JITTER_GAIN)
        self.assertAlmostEqual(jitter, expected)


class MicroglialLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = glia.MicroglialCoherenceModel(SMALL_SCENARIO.timing, SMALL_SCENARIO.agent, SMALL_SCENARIO.state, LOOP_GAIN)
        self.plain = dpc.CoherenceModel(SMALL_SCENARIO.timing, SMALL_SCENARIO.agent, SMALL_SCENARIO.state)

    def test_loop_is_silent_in_a_fully_coherent_brain(self) -> None:
        self.assertAlmostEqual(self.model.arousal_at(1.0, 1.0), self.plain.arousal(1.0))

    def test_loop_weakens_arousal_in_a_collapsed_brain(self) -> None:
        self.assertAlmostEqual(self.model.arousal_at(1.0, 0.0), (1 - LOOP_GAIN) * self.plain.arousal(1.0))


class ModelVariantTests(unittest.TestCase):
    """Variants of one network must reproduce the reference model exactly when they change nothing."""

    def test_depleted_loop_reproduces_the_reference_sweep(self) -> None:
        depleted = dpc.run_scenario(SMALL_SCENARIO, glia.with_microglia(glia.MICROGLIAL_DEPLETED_GAIN))
        self.assertEqual(depleted, dpc.run_scenario(SMALL_SCENARIO))

    def test_shared_curve_reproduces_a_freshly_built_one(self) -> None:
        shared = dpc.run_on_curve(dpc.build_curve(SMALL_SCENARIO), SMALL_SCENARIO)
        self.assertEqual(shared, dpc.run_scenario(SMALL_SCENARIO))


class AstrocyteTests(unittest.TestCase):
    def test_silencing_removes_the_astrocytic_share_of_down_states(self) -> None:
        silenced = glia.astrocytes_silenced(glia.GLOBAL_SLEEP)
        expected = glia.GLOBAL_SLEEP.down_state_fraction * (1 - glia.ASTROCYTIC_DOWN_STATE_SHARE)
        self.assertAlmostEqual(silenced.down_state_fraction, expected)
        self.assertEqual(silenced.arousal_level, glia.GLOBAL_SLEEP.arousal_level)


def measurement_with_microglia(depleted: ThresholdSummary, strongest: ThresholdSummary) -> glial_study.GlialMeasurement:
    unused = dpc.StableStates(0.0, 1.0, 0.0, dpc.REFERENCE_QUORUM_FRACTION)
    return glial_study.GlialMeasurement(
        node_count=302,
        seed=dpc.REFERENCE_SEED,
        by_myelin_integrity=(),
        by_microglial_gain=((glia.MICROGLIAL_DEPLETED_GAIN, depleted), (glia.STRONGEST_MICROGLIAL_GAIN, strongest)),
        global_sleep=unused,
        global_sleep_astrocytes_silenced=unused,
        duration_seconds=0.0,
    )


class GlialStudyTests(unittest.TestCase):
    def test_consecutive_pairs_reject_ties_and_undefined_values(self) -> None:
        self.assertTrue(glial_study.consecutive_pairs_hold([3.0, 2.0, 1.0], lambda a, b: a > b))
        self.assertFalse(glial_study.consecutive_pairs_hold([3.0, 3.0, 1.0], lambda a, b: a > b))
        self.assertFalse(glial_study.consecutive_pairs_hold([3.0, None], lambda a, b: a > b))

    def test_strong_loop_that_never_recovers_counts_as_later_emergence(self) -> None:
        measurement = measurement_with_microglia(
            depleted=ThresholdSummary(1.0, 0.8, 0.2, None), strongest=ThresholdSummary(0.9, None, None, None)
        )
        self.assertTrue(glial_study.depletion_hastens_emergence(measurement))

    def test_consistency_checks_hold_and_every_test_is_decided(self) -> None:
        measurement = glial_study.measure_seed(SeedTask(1_000, dpc.REFERENCE_SEED))
        for test in glial_study.TESTS:
            with self.subTest(test=test.identifier):
                verdict = test.holds_for(measurement)
                self.assertIn(verdict, (True, False))
                if test.kind == reporting.CONSISTENCY_CHECK:
                    self.assertTrue(verdict)

    def test_quick_study_writes_both_reports(self) -> None:
        with tempfile.TemporaryDirectory() as directory, unittest.mock.patch.object(reporting, "RESULTS_DIRECTORY", Path(directory)):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                glial_study.main(["--quick"])
            written = sorted(path.suffix for path in Path(directory).iterdir())
        self.assertEqual(written, [".json", ".md"])


class PaperListingTests(unittest.TestCase):
    def test_glial_listing_matches_source(self) -> None:
        pattern = r"<!-- begin glial_regulation.py -->\n```python\n(.*?)```\n<!-- end"
        match = re.search(pattern, paper_appendices.PAPER.read_text(), re.DOTALL)
        self.assertIsNotNone(match, "glial_regulation.py is not embedded in the paper")
        self.assertEqual(match.group(1), (provenance.SIMULATOR_DIRECTORY / "glial_regulation.py").read_text())


if __name__ == "__main__":
    unittest.main()
