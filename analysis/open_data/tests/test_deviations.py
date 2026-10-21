"""Deviations D1 to D5 (Appendix E.13), on synthetic data whose answer is known."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from analysis.open_data import deviations, loaders, outputs, pipeline_neurotycho, threshold_shape
from analysis.open_data.loaders.neurotycho import Marker
from analysis.open_data.pipeline_michigan import Subject

REGIONS, VOLUMES = 5, 8
SAMPLES_PER_SECOND = 1000.0


def a_run(number: int, empty: tuple[int, ...] = ()) -> loaders.MichiganRun:
    series = np.arange(REGIONS * VOLUMES, dtype=float).reshape(REGIONS, VOLUMES)
    series[list(empty)] = np.nan
    flat = np.zeros(VOLUMES)
    return loaders.MichiganRun("sub-x", number, series, [f"r{k}" for k in range(REGIONS)], flat, flat, flat, np.zeros((VOLUMES, 4)))


def a_marker(label: str, index: int) -> Marker:
    return Marker(session="Session1", label=label, index=index, seconds=index / SAMPLES_PER_SECOND)


class EmptyRegionTests(unittest.TestCase):
    def test_a_region_empty_in_any_run_is_removed_from_every_run(self) -> None:
        subject = Subject(a_run(1), a_run(2, empty=(1,)), (a_run(3), a_run(4, empty=(3,))))
        cleaned = deviations.drop_empty_regions(subject)
        for run_ in (cleaned.awake, cleaned.induction, *cleaned.emergence):
            self.assertEqual(run_.parcels, ["r0", "r2", "r4"])
            self.assertFalse(np.isnan(run_.timeseries).any())

    def test_a_subject_without_empty_regions_is_unchanged(self) -> None:
        subject = Subject(a_run(1), a_run(2), (a_run(3),))
        cleaned = deviations.drop_empty_regions(subject)
        np.testing.assert_array_equal(cleaned.induction.timeseries, subject.induction.timeseries)

    def test_a_region_missing_in_only_some_volumes_is_still_refused(self) -> None:
        partly = a_run(2)
        partly.timeseries[0, 3] = np.nan
        with self.assertRaises(ValueError):
            deviations.drop_empty_regions(Subject(a_run(1), partly, (a_run(3),)))


class FirstInjectionTests(unittest.TestCase):
    def test_the_first_of_several_injections_marks_induction(self) -> None:
        markers = [a_marker(pipeline_neurotycho.INJECTION, i) for i in (40, 10, 70)]
        markers.sort(key=lambda m: m.index)
        self.assertEqual(deviations.first_injection(markers, pipeline_neurotycho.INJECTION).index, 10)

    def test_other_markers_still_need_exactly_one(self) -> None:
        markers = [a_marker(pipeline_neurotycho.LOC, 5), a_marker(pipeline_neurotycho.LOC, 9)]
        with self.assertRaises(ValueError):
            deviations.first_injection(markers, pipeline_neurotycho.LOC)


def never_converges(*_: object) -> object:
    raise RuntimeError("no sigmoid fit converged")


class FailedFitTests(unittest.TestCase):
    def test_a_fit_that_does_not_converge_gives_no_steepness(self) -> None:
        with mock.patch.object(threshold_shape, "fit_shape", never_converges):
            self.assertIsNone(deviations.steepness_or_none(np.arange(8.0), np.arange(8.0)))

    def test_a_test_whose_fit_does_not_converge_is_recorded_as_not_evaluable(self) -> None:
        result = deviations.attempt_recording_failed_fits(never_converges)
        self.assertIn(outputs.EXCLUDED, result)
        self.assertTrue(result[outputs.EXCLUDED].startswith("not evaluable"))

    def test_a_stated_exclusion_is_still_recorded_as_committed(self) -> None:
        def excluded() -> dict:
            raise ValueError("stated rule")
        self.assertEqual(deviations.attempt_recording_failed_fits(excluded), {outputs.EXCLUDED: "stated rule"})


class EarliestAwakeRunTests(unittest.TestCase):
    def test_the_earlier_of_two_awake_runs_is_used_and_other_files_must_be_unique(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            for name in ("x_task-SPESclin_run-021506_ieeg.vhdr", "x_task-SPESclin_run-021417_ieeg.vhdr", "a_electrodes.tsv", "b_electrodes.tsv"):
                (Path(folder) / name).touch()
            chosen = deviations.earliest_awake_run(Path(folder), "*task-SPESclin_*_ieeg.vhdr")
            self.assertEqual(chosen.name, "x_task-SPESclin_run-021417_ieeg.vhdr")
            with self.assertRaises(FileNotFoundError):
                deviations.earliest_awake_run(Path(folder), "*_electrodes.tsv")


class EmptyTestFamilyTests(unittest.TestCase):
    def test_a_test_without_subjects_counts_as_p_one_and_is_not_evaluable(self) -> None:
        primary = {"H1": {"no_subject": True, "n": 0}, "H3": {"p_value": 0.01, "effect": 0.5, "smallest_effect": 0.1, "equivalence_p": 0.9, "n": 20}}
        with mock.patch.object(deviations.verdicts, "general_verdict", lambda result, p: f"rule at {p:.2f}"):
            out = deviations.family_verdicts_with_empty_tests(primary)
        self.assertEqual(out["H1"]["verdict"], deviations.NO_SUBJECT)
        self.assertEqual(out["H1"]["adjusted_p"], 1.0)
        self.assertAlmostEqual(out["H3"]["adjusted_p"], 0.02)


if __name__ == "__main__":
    unittest.main()
