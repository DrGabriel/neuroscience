"""Tests for the results catalogue that feeds the explainer's archive.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import results_catalogue as catalogue


def outcome(holding: int, applicable: int) -> dict:
    return {"identifier": "X", "statement": "s", "group": "g", "runs_holding": holding, "runs_applicable": applicable}


class CheckCountTests(unittest.TestCase):
    def test_counts_outcomes_wherever_they_sit_and_skips_inapplicable_ones(self) -> None:
        document = {"pillars": [outcome(5, 5), outcome(0, 5)], "nested": {"secondary": [outcome(2, 5), outcome(0, 0)]}}
        self.assertEqual(catalogue.count_checks(document), catalogue.CheckCount(checks=3, holding_in_every_run=1, holding_in_none=1))

    def test_a_report_without_checks_counts_none(self) -> None:
        self.assertEqual(catalogue.count_checks({"ratios": [1, 2]}).checks, 0)


class CurveDetectionTests(unittest.TestCase):
    def test_sweep_runs_have_curves(self) -> None:
        self.assertTrue(catalogue.has_curves({"runs": [{"induction_coherence": [1.0]}]}))

    def test_other_runs_do_not(self) -> None:
        self.assertFalse(catalogue.has_curves({"runs": [{"hub_activity": 1.0}]}))
        self.assertFalse(catalogue.has_curves({}))


class ReportNameTests(unittest.TestCase):
    def test_study_kinds_with_underscores_parse(self) -> None:
        name = catalogue.ReportName.of(Path("calibration_phase_feedback_full_20261018T124535Z.json"))
        self.assertEqual((name.kind, name.label), ("calibration_phase_feedback", "full"))

    def test_any_run_label_is_accepted(self) -> None:
        self.assertEqual(catalogue.ReportName.of(Path("prespecified_full_20261018T150000Z.json")).kind, "prespecified")

    def test_a_file_that_is_not_a_report_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stray = Path(directory) / "notes.json"
            stray.write_text("{}")
            with self.assertRaises(ValueError):
                catalogue.entry_for(catalogue.Report.read(stray, catalogue.CURRENT_SET, ""))


class CatalogueTests(unittest.TestCase):
    def test_every_report_is_listed_and_wrapped_and_none_is_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results, explainer = Path(directory) / "results", Path(directory) / "explainer"
            (results / "archive" / "old_set").mkdir(parents=True)
            report = {"started_utc": "2026-01-01T00:00:00+00:00", "pillars": [outcome(1, 1)]}
            current = results / "species_full_20260101T000000Z.json"
            old = results / "archive" / "old_set" / "validation_full_20251231T000000Z.json"
            for path in (current, old):
                path.write_text(json.dumps(report))
            (results / "archive" / "old_set" / "README.md").write_text("# Old results\n")
            before = {path: path.read_bytes() for path in (current, old)}
            with mock.patch.object(catalogue.reporting, "RESULTS_DIRECTORY", results), \
                    mock.patch.object(catalogue, "ARCHIVE", results / "archive"), \
                    mock.patch.object(catalogue, "EXPLAINER_DATA", explainer), \
                    mock.patch.object(catalogue, "CATALOGUE_FILE", explainer / "catalogue.js"):
                entries = catalogue.write_catalogue()
            self.assertEqual([e.identifier for e in entries], ["current/species_full_20260101T000000Z", "old_set/validation_full_20251231T000000Z"])
            self.assertEqual(entries[1].set_note, "Old results")
            self.assertTrue((explainer / "old_set" / "validation_full_20251231T000000Z.js").exists())
            self.assertIn("DPC_RESULTS_CATALOGUE", (explainer / "catalogue.js").read_text())
            self.assertEqual({path: path.read_bytes() for path in (current, old)}, before)

    def test_a_wrapper_left_by_a_report_moved_to_the_archive_is_removed_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            results, explainer = Path(directory) / "results", Path(directory) / "explainer"
            results.mkdir()
            (results / "species_full_20260101T000000Z.json").write_text(json.dumps({"started_utc": "2026-01-01T00:00:00+00:00"}))
            stale = explainer / "current" / "species_full_20251231T000000Z.js"
            stale.parent.mkdir(parents=True)
            stale.write_text("/* left behind when its report was archived */")
            with mock.patch.object(catalogue.reporting, "RESULTS_DIRECTORY", results), \
                    mock.patch.object(catalogue, "ARCHIVE", results / "archive"), \
                    mock.patch.object(catalogue, "EXPLAINER_DATA", explainer), \
                    mock.patch.object(catalogue, "CATALOGUE_FILE", explainer / "catalogue.js"):
                catalogue.write_catalogue()
            self.assertFalse(stale.exists())
            self.assertTrue((explainer / "current" / "species_full_20260101T000000Z.js").exists())

    def test_a_local_smoke_run_is_not_listed_but_an_archived_check_is_regression(self) -> None:
        # Quick runs in results/ are git-ignored; listing one would publish an untracked file in the explainer.
        with tempfile.TemporaryDirectory() as directory:
            results, explainer = Path(directory) / "results", Path(directory) / "explainer"
            (results / "archive" / "checks").mkdir(parents=True)
            report = json.dumps({"started_utc": "2026-01-01T00:00:00+00:00"})
            (results / "glia_quick_20260101T000000Z.json").write_text(report)
            (results / "archive" / "checks" / "sensitivity_quick_20260101T000000Z.json").write_text(report)
            with mock.patch.object(catalogue.reporting, "RESULTS_DIRECTORY", results), \
                    mock.patch.object(catalogue, "ARCHIVE", results / "archive"), \
                    mock.patch.object(catalogue, "EXPLAINER_DATA", explainer), \
                    mock.patch.object(catalogue, "CATALOGUE_FILE", explainer / "catalogue.js"):
                entries = catalogue.write_catalogue()
            self.assertEqual([e.identifier for e in entries], ["checks/sensitivity_quick_20260101T000000Z"])


if __name__ == "__main__":
    unittest.main()
