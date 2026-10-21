"""Round 3, H5a signal-to-noise control: SNR, the matching rule, the simulation and the commands, on synthetic data."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np

from analysis.open_data import evoked_latency, pipeline_prios, snr_control, snr_matching, snr_simulation
from analysis.open_data.pipeline_prios import Comparison, PriosSession
from analysis.open_data.round3_settings import SNR
from analysis.open_data.snr_simulation import Cell
from analysis.open_data.tests.test_datasets_end_to_end import write_brainvision

FS = SNR.sampling_hz
MANY_TRIALS, FEW_TRIALS = 200, 10
CONNECTIONS = 9
HIGH_SNR, LOW_SNR, MEDIUM_SNR, LARGE_SNR = 4.0, 1.5, 8.0, 16.0
SMALL_JITTER_MS, LARGE_JITTER_MS = 1.0, 4.0
SNR_ONLY_RISE, MATCHED_LIMIT, KEPT_RISE = 0.4, 0.25, 0.8
ROOT_THREE, DOUBLED_NOISE, RELATIVE_TOLERANCE, NOISE_TOLERANCE = np.sqrt(3.0), 2.0, 0.1, 0.1
NULL_CONNECTIONS = 3
SEED = 11
ELECTRODES = "name\tx\ty\tz\nA1\t0\t0\t0\nA2\t0\t10\t0\nR1\t40\t0\t0\n"
AWAKE_JITTER_MS, PROPOFOL_JITTER_MS = 1.0, 4.0


def connection(awake: Cell, propofol: Cell, rng: np.random.Generator) -> dict:
    trials = [snr_simulation.synthetic_trials(SNR, cell, rng) for cell in (awake, propofol)]
    return snr_matching.matched_connection(*trials, Comparison(FS, {}, rng))


def median_over_connections(awake: Cell, propofol: Cell, field: str) -> float:
    rng = np.random.default_rng(SEED)
    return float(np.median([connection(awake, propofol, rng)[field] for _ in range(CONNECTIONS)]))


def corrected_and_layout(cell: Cell) -> tuple[np.ndarray, snr_matching.TrialLayout]:
    trials = snr_simulation.synthetic_trials(SNR, cell, np.random.default_rng(SEED))
    corrected, onset = pipeline_prios.baseline_corrected(trials, FS)
    return corrected, snr_matching.trial_layout(FS, onset)


class SnrAndDegradationTests(unittest.TestCase):
    def test_noise_scale_that_halves_an_snr_is_root_three(self) -> None:
        self.assertAlmostEqual(snr_matching.noise_scale(DOUBLED_NOISE, 1.0), ROOT_THREE)
        self.assertEqual(snr_matching.noise_scale(1.0, 1.0), 0.0)

    def test_snr_of_a_response_without_jitter_is_its_amplitude_over_the_noise(self) -> None:
        corrected, layout = corrected_and_layout(Cell(snr_simulation.WHITE, 0.0, MANY_TRIALS, HIGH_SNR))
        self.assertAlmostEqual(snr_matching.state_snr(corrected, layout)["snr"], HIGH_SNR, delta=RELATIVE_TOLERANCE * HIGH_SNR)

    def test_degrading_by_root_three_doubles_the_noise_inside_the_span_only(self) -> None:
        corrected, layout = corrected_and_layout(Cell(snr_simulation.WHITE, 0.0, MANY_TRIALS, 0.0))
        noisier = snr_matching.degraded(corrected, layout, ROOT_THREE)
        self.assertAlmostEqual(float(np.median(noisier[:, layout.span].std(axis=1))), DOUBLED_NOISE, delta=NOISE_TOLERANCE)
        np.testing.assert_array_equal(noisier[:, : layout.span.start], corrected[:, : layout.span.start])

    def test_the_higher_snr_state_is_the_one_degraded(self) -> None:
        row = connection(Cell(snr_simulation.PINK, SMALL_JITTER_MS, MANY_TRIALS, HIGH_SNR), Cell(snr_simulation.PINK, SMALL_JITTER_MS, MANY_TRIALS, LOW_SNR), np.random.default_rng(SEED))
        self.assertEqual(row["degraded_state"], snr_matching.AWAKE)
        self.assertLess(row["log_snr_ratio"], 0.0)


# log SNR ratio, r as run, matched r: the first fell by more than log 1.25 = 0.22, the second by less.
RESTRICTION_ROWS = ((-0.5, 9.0, 1.0), (-0.2, 2.0, None), (0.3, 4.0, 3.0))
RESTRICTED_MEDIAN, MATCHED_MEDIAN = 3.0, 2.0


class MatchingRuleTests(unittest.TestCase):
    def test_matching_removes_a_rise_produced_by_a_drop_in_snr_alone(self) -> None:
        awake = Cell(snr_simulation.PINK, SMALL_JITTER_MS, MANY_TRIALS, HIGH_SNR)
        propofol = replace(awake, nominal_snr=LOW_SNR)
        self.assertGreater(median_over_connections(awake, propofol, "relative_change"), SNR_ONLY_RISE)
        self.assertLess(abs(median_over_connections(awake, propofol, "matched_relative_change")), MATCHED_LIMIT)

    def test_matching_keeps_a_rise_of_the_true_jitter(self) -> None:
        awake = Cell(snr_simulation.WHITE, SMALL_JITTER_MS, MANY_TRIALS, HIGH_SNR)
        propofol = replace(awake, jitter_ms=LARGE_JITTER_MS)
        self.assertGreater(median_over_connections(awake, propofol, "matched_relative_change"), KEPT_RISE)

    def test_the_restriction_keeps_connections_whose_snr_fell_by_at_most_the_ratio(self) -> None:
        snr = {s: {"snr": 1.0} for s in snr_matching.STATES}
        fields = ("log_snr_ratio", "relative_change", "matched_relative_change")
        rows = [{**dict(zip(fields, values, strict=True)), "snr": snr} for values in RESTRICTION_ROWS]
        summary = snr_control.patient_summary(rows)
        self.assertEqual(summary["restricted_connections"], 2)
        self.assertEqual(summary["median_restricted_relative_change"], RESTRICTED_MEDIAN)
        self.assertEqual(summary["median_matched_relative_change"], MATCHED_MEDIAN)
        self.assertEqual(summary["median_log_snr_ratio"], RESTRICTION_ROWS[1][0])


class ReproducesH5aTests(unittest.TestCase):
    def test_same_draws_as_the_committed_comparison(self) -> None:
        cells = [Cell(snr_simulation.WHITE, j, FEW_TRIALS, MEDIUM_SNR) for j in (AWAKE_JITTER_MS, PROPOFOL_JITTER_MS)]
        awake, propofol = (snr_simulation.synthetic_trials(SNR, c, np.random.default_rng(SEED)) for c in cells)
        committed = pipeline_prios.compare_connection(awake, propofol, Comparison(FS, {}, np.random.default_rng(SEED)))
        controlled = snr_matching.matched_connection(awake, propofol, Comparison(FS, {}, np.random.default_rng(SEED)))
        self.assertEqual({k: controlled[k] for k in committed}, committed)

    def test_a_patient_gives_the_committed_h5a_result_and_the_committed_function_is_restored(self) -> None:
        committed_function = pipeline_prios.compare_connection
        with tempfile.TemporaryDirectory() as tmp:
            session = synthetic_session(Path(tmp))
            committed = pipeline_prios.subject_changes(session, np.random.default_rng(SEED))
            controlled = snr_control.subject_snr_control(session, np.random.default_rng(SEED))
        self.assertIs(pipeline_prios.compare_connection, committed_function)
        self.assertEqual(controlled["median_relative_change"], committed["median_relative_change"])
        self.assertEqual([c["relative_change"] for c in controlled["connections"]], [c["relative_change"] for c in committed["connections"]])


def synthetic_session(folder: Path) -> PriosSession:
    rng = np.random.default_rng(SEED)
    write_brainvision(folder, "sub-X_task-SPESclin", AWAKE_JITTER_MS, rng)
    write_brainvision(folder, "sub-X_task-SPESprop", PROPOFOL_JITTER_MS, rng)
    (folder / "electrodes.tsv").write_text(ELECTRODES)
    return PriosSession(folder, "sub-X_task-SPESclin", "sub-X_task-SPESprop", folder / "electrodes.tsv")


SMALL_SPEC = replace(SNR, connections=30, snr_doublings=(0.0, 4.0), trial_counts=(FEW_TRIALS, MANY_TRIALS // 2), jitter_ms=(2.0,), colours=(snr_simulation.WHITE,), null_awake_snr=(LARGE_SNR,), null_snr_ratios=(0.25,))
JITTER_TOLERANCE_MS, COLLAPSED_SPREAD_MS = 0.5, 0.5


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cells = {(c["trials"], c["nominal_snr"]): c for c in snr_simulation.simulate(SMALL_SPEC, np.random.default_rng(SEED))}

    def test_with_many_trials_and_a_high_snr_the_estimator_recovers_the_true_jitter(self) -> None:
        cell = self.cells[(MANY_TRIALS // 2, LARGE_SNR)]
        self.assertAlmostEqual(cell["latency_sd_ms"], SMALL_SPEC.jitter_ms[0], delta=JITTER_TOLERANCE_MS)

    def test_with_few_trials_a_low_snr_pulls_single_trial_shifts_towards_zero(self) -> None:
        # Each trial is part of the template it is aligned to, so at a low SNR it aligns with its own noise at zero shift.
        self.assertLess(self.cells[(FEW_TRIALS, 1.0)]["latency_sd_ms"], COLLAPSED_SPREAD_MS)

    def test_amplitude_drop_table_pairs_snrs_within_one_condition(self) -> None:
        table = snr_simulation.amplitude_drop_table(list(self.cells.values()))
        self.assertEqual(len(table), len(SMALL_SPEC.trial_counts))
        few = next(r for r in table if r["trials"] == FEW_TRIALS)
        expected = np.log(self.cells[(FEW_TRIALS, 1.0)]["latency_sd_ms"] / self.cells[(FEW_TRIALS, LARGE_SNR)]["latency_sd_ms"])
        self.assertAlmostEqual(few["relative_change"], expected)

    def test_null_check_reports_both_statistics(self) -> None:
        rows = snr_simulation.null_check(replace(SMALL_SPEC, connections=NULL_CONNECTIONS), np.random.default_rng(SEED))
        self.assertEqual(len(rows), 1)
        self.assertLessEqual(rows[0]["connections"], NULL_CONNECTIONS)
        self.assertIn("median_matched_relative_change", rows[0])


SIMULATED_SNR, HALVED_SNR = (1.0, 2.0, 4.0, 8.0), (4.0, 2.0)


class SnrOnlyChangeTests(unittest.TestCase):
    def test_spread_inversely_proportional_to_snr_gives_the_log_snr_ratio(self) -> None:
        cells = [{"colour": "white", "jitter_ms": 0.0, "trials": FEW_TRIALS, "measured_snr": s, "latency_sd_ms": 1.0 / s} for s in SIMULATED_SNR]
        (row,) = snr_simulation.snr_only_change(cells, HALVED_SNR)
        self.assertAlmostEqual(row["relative_change"], np.log(HALVED_SNR[0] / HALVED_SNR[1]))
        self.assertTrue(row["inside_simulated_range"])
        (outside,) = snr_simulation.snr_only_change(cells, (LARGE_SNR, HALVED_SNR[1]))
        self.assertFalse(outside["inside_simulated_range"])


# Simulated spread of a 2 ms jitter at 10 trials: collapsed at an SNR of 2, recovered at 8.
SENSITIVITY_CURVE = ((2.0, 0.1), (8.0, 2.0))


class MatchedSensitivityTests(unittest.TestCase):
    def cells(self) -> list[dict]:
        return [
            {"colour": c, "jitter_ms": SNR.sensitivity_jitter_ms, "trials": SNR.sensitivity_trials, "measured_snr": snr, "latency_sd_ms": spread}
            for c in SNR.colours
            for snr, spread in SENSITIVITY_CURVE
        ]

    def test_the_matched_comparison_is_informative_only_where_a_true_jitter_survives_the_estimator(self) -> None:
        (low_snr, collapsed), (high_snr, recovered) = SENSITIVITY_CURVE
        low = snr_control.matched_sensitivity(self.cells(), low_snr)
        high = snr_control.matched_sensitivity(self.cells(), high_snr)
        self.assertFalse(low["informative"])
        self.assertTrue(high["informative"])
        self.assertAlmostEqual(high["simulated_spread_ms"][snr_simulation.PINK], recovered)
        self.assertAlmostEqual(low["simulated_spread_ms"][snr_simulation.WHITE], collapsed)


class CommandTests(unittest.TestCase):
    def test_patient_simulation_and_group_commands_run_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snr_control.deviations, "apply_deviations") as applied, mock.patch.object(snr_control, "SNR", SMALL_SPEC):
            session = Path(tmp) / "sub-PRIOSX" / "ses-1"
            (session / "ieeg").mkdir(parents=True)
            rng = np.random.default_rng(SEED)
            write_brainvision(session / "ieeg", "sub-PRIOSX_ses-1_task-SPESclin_run-1", AWAKE_JITTER_MS, rng)
            write_brainvision(session / "ieeg", "sub-PRIOSX_ses-1_task-SPESprop_run-2", PROPOFOL_JITTER_MS, rng)
            (session / "ieeg" / "sub-PRIOSX_ses-1_electrodes.tsv").write_text(ELECTRODES)
            out = Path(tmp) / "out"
            snr_control.main(["prios", "--session-dir", str(session), "--out", str(out)])
            snr_control.main(["simulate", "--out", str(out / "simulation.json"), "--connections", str(NULL_CONNECTIONS)])
            snr_control.main(["group", "--inputs", str(out), "--simulation", str(out / "simulation.json"), "--out", str(out / "group.json")])
            patient = json.loads((out / "prios_sub-PRIOSX.json").read_text())[snr_control.RESULT_FIELD]
            summary = json.loads((out / "group.json").read_text())["secondary_H5a_snr_control"]
        applied.assert_called_once()
        self.assertEqual(len(patient["connections"]), 1)
        self.assertEqual(set(summary["tests"]), set(snr_control.GROUP_FIELDS))
        self.assertEqual(summary["tests"]["as_run"]["effect"], patient["median_relative_change"])
        self.assertEqual(summary["verdict"], snr_control.NO_VERDICT)
        self.assertIn("snr_only_relative_change", summary)
        self.assertIn("informative", summary["matched_sensitivity"])


if __name__ == "__main__":
    unittest.main()
