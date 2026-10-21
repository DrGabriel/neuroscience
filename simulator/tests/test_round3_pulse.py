"""Analysis A of Appendix C.14 (prediction 15): the arousal pulse, the bistable window and the tests P15a and P15b, on
hand-built maps whose answers are known.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest

import comparisons
import dpc_simulator as dpc
import prediction15_study
import validation_study as validation
from round3_study import arousal_pulse as pulse
from round3_study import pulse_checks, pulse_report
from round3_study.seeds import PULSE_BLOCK

SCENARIO = dpc.REFERENCE_SCENARIO
QUORUM = SCENARIO.quorum_fraction
CONCENTRATION = 0.85
COLLAPSED, AWAKE = 0.0, 1.0
PARTIAL_GIANT = 0.6
LOSS, RECOVERY = 0.88, 0.82
WINDOW = pulse.BistableWindow(RECOVERY, LOSS)
PLACES = 12


GRID = dpc.ConcentrationGrid(1.0, dpc.REFERENCE_CONCENTRATION_STEP).ascending()


def sweep(loss: float | None, recovery: float | None) -> dpc.SweepResult:
    """Quorum held on induction up to loss and regained on emergence at recovery; None for never."""
    induction = tuple(dpc.SweepPoint(c, AWAKE, loss is not None and comparisons.at_most(c, loss)) for c in GRID)
    emergence = tuple(dpc.SweepPoint(c, AWAKE, recovery is not None and comparisons.at_most(c, recovery)) for c in reversed(GRID))
    return dpc.SweepResult(induction, emergence)


class StubCoherence:
    """pi = S + boost: a map with two stable states (0.1 and 0.9) on STEP_CURVE when the boost is zero."""

    def __init__(self, boost: float) -> None:
        self._boost = boost

    def coherence_probability(self, concentration: float, coherent_fraction: float) -> float:
        return coherent_fraction + self._boost


LOW_STATE, MIDDLE_STATE, HIGH_STATE = 0.1, 0.5, 0.9
STEP_CURVE = dpc.PercolationCurve([0.3, 0.6], [LOW_STATE, MIDDLE_STATE, HIGH_STATE])
STUB_PULSE_BOOST = 0.5


def probability(model: dpc.CoherenceModel, fraction: float) -> float:
    return model.coherence_probability(CONCENTRATION, fraction)


def threshold_curve(threshold: float, giant: float) -> dpc.PercolationCurve:
    """F(pi) = 0 up to the threshold and giant above it."""
    return dpc.PercolationCurve([threshold], [COLLAPSED, giant])


def baseline_model() -> dpc.CoherenceModel:
    return dpc.CoherenceModel(SCENARIO.timing, SCENARIO.agent, SCENARIO.state)


def outcome(before: float, end: float, after: float) -> pulse.PulseOutcome:
    return pulse.PulseOutcome(CONCENTRATION, before, end, 1, after, QUORUM)


class PulsedModelTests(unittest.TestCase):
    def test_the_full_pulse_takes_the_arousal_drive_to_its_maximum_so_the_reference_does_not_weaken(self) -> None:
        model = pulse.PulsedCoherenceModel(SCENARIO, pulse.FULL_PULSE_INCREASE)
        self.assertEqual(model.arousal_at(CONCENTRATION, COLLAPSED), pulse.MAXIMUM_AROUSAL)
        self.assertEqual(model.reference_error_ms(CONCENTRATION, COLLAPSED), 0.0)

    def test_the_awake_drive_pulse_adds_a0_to_the_suppressed_drive(self) -> None:
        increase = pulse.AWAKE_DRIVE_PULSE_INCREASE
        model = pulse.PulsedCoherenceModel(SCENARIO, increase)
        self.assertAlmostEqual(model.arousal_at(CONCENTRATION, COLLAPSED), baseline_model().arousal(CONCENTRATION) + increase, places=PLACES)
        self.assertGreaterEqual(model.arousal_at(CONCENTRATION, COLLAPSED), SCENARIO.state.arousal_level)

    def test_a_pulse_of_zero_is_the_reference_model(self) -> None:
        model = pulse.PulsedCoherenceModel(SCENARIO, 0.0)
        self.assertEqual(probability(model, PARTIAL_GIANT), probability(baseline_model(), PARTIAL_GIANT))


class WindowTests(unittest.TestCase):
    def test_the_window_runs_from_recovery_to_loss_and_the_test_points_follow_from_it(self) -> None:
        self.assertAlmostEqual(WINDOW.width, LOSS - RECOVERY, places=PLACES)
        self.assertAlmostEqual(WINDOW.concentration_at(pulse.TestPoint.INSIDE_WINDOW), (LOSS + RECOVERY) / 2, places=PLACES)
        self.assertAlmostEqual(WINDOW.concentration_at(pulse.TestPoint.ABOVE_LOSS), LOSS + pulse.ABOVE_LOSS_OFFSET, places=PLACES)
        self.assertAlmostEqual(WINDOW.relative_half_width, (LOSS - RECOVERY) / 2 / ((LOSS + RECOVERY) / 2), places=PLACES)

    def test_no_window_without_a_loss_a_recovery_or_a_gap_between_them(self) -> None:
        window = pulse.window_of(sweep(LOSS, RECOVERY))
        self.assertAlmostEqual(window.loss, LOSS, places=PLACES)
        self.assertAlmostEqual(window.recovery, RECOVERY, places=PLACES)
        self.assertIsNone(pulse.window_of(sweep(None, RECOVERY)))
        self.assertIsNone(pulse.window_of(sweep(LOSS, None)))
        self.assertIsNone(pulse.window_of(sweep(LOSS, LOSS)))


class PulseLogicTests(unittest.TestCase):
    def test_on_a_bistable_map_the_pulse_lifts_the_low_state_and_the_high_state_then_holds(self) -> None:
        pulsed = pulse.FixedPointMap(STEP_CURVE, StubCoherence(STUB_PULSE_BOOST), CONCENTRATION)
        trace = pulse.apply_pulse(pulsed, LOW_STATE, QUORUM)
        self.assertEqual(trace, pulse.PulseTrace(HIGH_STATE, 1))
        self.assertEqual(pulse.FixedPointMap(STEP_CURVE, StubCoherence(0.0), CONCENTRATION).settle(trace.final_fraction), HIGH_STATE)
        self.assertEqual(pulse.FixedPointMap(STEP_CURVE, StubCoherence(0.0), CONCENTRATION).settle(LOW_STATE), LOW_STATE)

    def test_a_pulse_too_weak_to_reach_quorum_records_no_quorum_step(self) -> None:
        trace = pulse.apply_pulse(pulse.FixedPointMap(STEP_CURVE, StubCoherence(0.0), CONCENTRATION), LOW_STATE, QUORUM)
        self.assertEqual(trace, pulse.PulseTrace(LOW_STATE, None))

    def test_where_both_states_exist_quorum_restored_by_the_pulse_persists(self) -> None:
        threshold = (probability(baseline_model(), COLLAPSED) + probability(baseline_model(), AWAKE)) / 2
        result = pulse.pulse_outcome(threshold_curve(threshold, AWAKE), SCENARIO, pulse.PulseSetting(CONCENTRATION, pulse.FULL_PULSE_INCREASE, COLLAPSED))
        self.assertEqual((result.before, result.end_of_pulse, result.first_quorum_step, result.after), (COLLAPSED, AWAKE, 1, AWAKE))
        self.assertTrue(pulse_checks.woken_and_persists(result))
        self.assertFalse(pulse_checks.woken_and_lost_again(result))

    def test_where_only_the_low_state_exists_quorum_restored_by_the_pulse_is_lost_again(self) -> None:
        held = probability(pulse.PulsedCoherenceModel(SCENARIO, pulse.FULL_PULSE_INCREASE), PARTIAL_GIANT)
        threshold = (probability(baseline_model(), PARTIAL_GIANT) + held) / 2
        result = pulse.pulse_outcome(threshold_curve(threshold, PARTIAL_GIANT), SCENARIO, pulse.PulseSetting(CONCENTRATION, pulse.FULL_PULSE_INCREASE, COLLAPSED))
        self.assertEqual((result.before, result.end_of_pulse, result.after), (COLLAPSED, PARTIAL_GIANT, COLLAPSED))
        self.assertTrue(pulse_checks.woken_and_lost_again(result))
        self.assertFalse(pulse_checks.woken_and_persists(result))


class SmallestIncreaseTests(unittest.TestCase):
    def bistable_curve(self) -> dpc.PercolationCurve:
        return threshold_curve((probability(baseline_model(), COLLAPSED) + probability(baseline_model(), AWAKE)) / 2, AWAKE)

    def achieves(self, curve: dpc.PercolationCurve, increase: float) -> bool:
        return pulse_checks.woken_and_persists(pulse.pulse_outcome(curve, SCENARIO, pulse.PulseSetting(CONCENTRATION, increase, COLLAPSED)))

    def test_the_smallest_increase_works_and_one_bisection_step_less_does_not(self) -> None:
        curve = self.bistable_curve()
        smallest = pulse.smallest_increase(curve, SCENARIO, pulse.IncreaseProbe(CONCENTRATION, COLLAPSED, pulse_checks.woken_and_persists))
        resolution = 1 / 2**pulse.SMALLEST_INCREASE_BISECTION_STEPS
        self.assertTrue(self.achieves(curve, smallest))
        self.assertFalse(self.achieves(curve, smallest - resolution))

    def test_none_when_even_the_full_pulse_does_not_achieve_it(self) -> None:
        unreachable = threshold_curve(AWAKE, AWAKE)
        probe = pulse.IncreaseProbe(CONCENTRATION, COLLAPSED, pulse_checks.woken_and_persists)
        self.assertIsNone(pulse.smallest_increase(unreachable, SCENARIO, probe))


class CheckTests(unittest.TestCase):
    def test_a_seed_that_starts_with_quorum_fails_both_tests(self) -> None:
        self.assertFalse(pulse_checks.woken_and_persists(outcome(AWAKE, AWAKE, AWAKE)))
        self.assertFalse(pulse_checks.woken_and_lost_again(outcome(AWAKE, AWAKE, COLLAPSED)))

    def test_a_seed_the_pulse_does_not_wake_fails_both_tests(self) -> None:
        self.assertFalse(pulse_checks.woken_and_persists(outcome(COLLAPSED, COLLAPSED, AWAKE)))
        self.assertFalse(pulse_checks.woken_and_lost_again(outcome(COLLAPSED, COLLAPSED, COLLAPSED)))

    def test_a_seed_without_a_window_fails_both_tests_and_is_counted(self) -> None:
        measurement = pulse_checks.PulseMeasurement(validation.QUICK_NODE_COUNTS[0], PULSE_BLOCK.seeds().start, None, {}, {}, 0.0)
        verdicts = [check.holds_for(measurement) for check in pulse_checks.TESTS]
        self.assertEqual(verdicts, [False, False])

    def test_the_tests_read_the_full_pulse_and_the_observations_the_awake_drive_pulse(self) -> None:
        full = {pulse_checks.condition_key(c): outcome(COLLAPSED, AWAKE, AWAKE) for c in pulse_checks.CONDITIONS if c[1] is pulse.Pulse.FULL}
        measurement = pulse_checks.PulseMeasurement(validation.QUICK_NODE_COUNTS[0], PULSE_BLOCK.seeds().start, WINDOW, full, {}, 0.0)
        self.assertEqual([check.holds_for(measurement) for check in pulse_checks.TESTS], [True, False])
        self.assertEqual([check.holds_for(measurement) for check in pulse_checks.OBSERVATIONS], [False, False, True])


class DesignTests(unittest.TestCase):
    def test_the_full_study_has_b4s_sizes_and_seed_count_on_its_own_seeds(self) -> None:
        design = prediction15_study.FULL_DESIGN
        self.assertEqual((design.node_counts, design.seeds_per_size), (validation.FULL_NODE_COUNTS, validation.FULL_SEEDS_PER_SIZE))
        self.assertEqual({task.seed for task in design.tasks()}, set(PULSE_BLOCK.seeds()))

    def test_only_the_full_study_and_the_smoke_mode_can_be_asked_for(self) -> None:
        self.assertIs(prediction15_study.parse_design([]), prediction15_study.FULL_DESIGN)
        self.assertIs(prediction15_study.parse_design(["--smoke"]), prediction15_study.SMOKE_DESIGN)
        with self.assertRaises(SystemExit):
            prediction15_study.parse_design(["--quick"])

    def test_the_report_gives_a_verdict_per_size_and_fails_on_one_seed(self) -> None:
        full = {pulse_checks.condition_key(c): outcome(COLLAPSED, AWAKE, AWAKE) for c in pulse_checks.CONDITIONS}
        task = prediction15_study.SMOKE_DESIGN
        measurement = pulse_checks.PulseMeasurement(task.node_counts[0], PULSE_BLOCK.seeds().start, WINDOW, full, {}, 0.0)
        study = pulse_report.PulseStudy(task, "2026-10-21T00:00:00+00:00", "2026-10-21T00:00:01+00:00", 1, [measurement])
        report = pulse_report.assemble_report(study)
        self.assertEqual([t["verdict"] for t in report["tests"]], ["fails", "fails"])
        self.assertFalse(pulse_report.every_test_passes(report))
        self.assertIn("P15a", pulse_report.to_markdown(report))


if __name__ == "__main__":
    unittest.main()
