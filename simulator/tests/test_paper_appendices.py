"""Tests for the appendix generator's assembly (not the report contents, which other tests check).

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest
from unittest import mock

import paper_appendices as appendices

PAPER_TEXT = "# Title\n\nBody text.\n"


class AssemblyTests(unittest.TestCase):
    def setUp(self) -> None:
        stubs = {
            "simulator_appendix": lambda: f"{appendices.SIMULATOR_APPENDIX_HEADING}\nsimulator",
            "studies_appendix": lambda: "## Appendix C: studies\nstudies",
        }
        self.patches = [mock.patch.object(appendices, name, stub) for name, stub in stubs.items()]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in self.patches:
            patch.stop()

    def test_regenerating_replaces_the_appendices_instead_of_appending_them_again(self) -> None:
        for note in ("", appendices.PT_APPENDIX_NOTE):
            once = appendices.with_appendices(PAPER_TEXT, note)
            self.assertEqual(appendices.with_appendices(once, note), once)

    def test_the_paper_text_is_kept_and_followed_by_appendices_b_to_d(self) -> None:
        paper = appendices.with_appendices(PAPER_TEXT)
        self.assertTrue(paper.startswith(PAPER_TEXT.rstrip("\n")))
        positions = [paper.index(heading) for heading in ("## Appendix B", "## Appendix C", "## Appendix D")]
        self.assertEqual(positions, sorted(positions))

    def test_the_translation_carries_the_note_before_the_appendices(self) -> None:
        paper = appendices.with_appendices(PAPER_TEXT, appendices.PT_APPENDIX_NOTE)
        self.assertLess(paper.index(appendices.PT_APPENDIX_NOTE), paper.index("## Appendix B"))


class ReportSectionTests(unittest.TestCase):
    def test_a_study_without_a_report_is_marked_not_yet_run_instead_of_stopping_generation_regression(self) -> None:
        self.assertEqual(appendices.report_section("study_that_was_never_run"), appendices.NOT_YET_RUN)

    def test_an_existing_report_is_given_with_its_source_file(self) -> None:
        section = appendices.report_section("validation")
        self.assertTrue(section.startswith(f"Source: `simulator/results/{appendices.report_name('validation')}`."))


class ProvenanceVerdictTests(unittest.TestCase):
    HASHES = {"model.py": "a", "study.py": "b"}

    def verdict(self, files_by_commit: dict[str, dict[str, str]], later: list[str]) -> str:
        committed = lambda commit, name: files_by_commit.get(commit, {}).get(name)
        listing = mock.Mock(stdout=" ".join(later))
        with mock.patch.object(appendices, "committed_sha256", committed), mock.patch.object(appendices.subprocess, "run", return_value=listing):
            return appendices.provenance_verdict("recorded", self.HASHES)

    def test_a_report_whose_files_equal_its_commit_matches(self) -> None:
        self.assertEqual(self.verdict({"recorded": dict(self.HASHES)}, []), "every file matches")

    def test_code_run_from_a_working_copy_is_traced_to_the_commit_that_holds_it(self) -> None:
        files = {"recorded": {"model.py": "old", "study.py": "b"}, "next": dict(self.HASHES)}
        self.assertIn("committed unchanged in `next`", self.verdict(files, ["next"]))

    def test_code_found_in_no_commit_is_named_file_by_file_regression(self) -> None:
        files = {"recorded": {"model.py": "old", "study.py": "b"}, "next": {"model.py": "other", "study.py": "b"}}
        self.assertEqual(self.verdict(files, ["next"]), "differs from every later commit: `model.py`")



class PublicLabelTests(unittest.TestCase):
    def test_tests_that_reuse_postulate_names_get_a_label_that_is_not_a_postulate_Regression(self) -> None:
        for identifier, label in appendices.public_labels.REPORT_TO_PUBLIC.items():
            self.assertRegex(identifier, r"^P\d")
            self.assertNotRegex(label, r"^P\d")

    def test_only_cells_that_are_an_identifier_are_relabelled(self) -> None:
        report = "| P3 | Stimulated area keeps processing (P3) | 17/20 |\n| K1 | Ketamine | 12/20 |\nPostulate P3 in prose."
        relabelled = appendices.public_labels.relabel_table_cells(report)
        self.assertEqual(relabelled, "| T3 | Stimulated area keeps processing (P3) | 17/20 |\n| K1 | Ketamine | 12/20 |\nPostulate P3 in prose.")

    def test_identifier_cells_in_a_table_header_are_relabelled_Regression(self) -> None:
        # The sensitivity report's phase-model table names its columns by test, so B.6 printed P2a, P2b and P3.
        header = "| Variation | P2a | P2b | P3 |\n|---|---|---|---|\n| Coupling K = 2 | 5/5 | 5/5 | 3/5 |"
        relabelled = appendices.public_labels.relabel_table_cells(header)
        self.assertEqual(relabelled, "| Variation | T2a | T2b | T3 |\n|---|---|---|---|\n| Coupling K = 2 | 5/5 | 5/5 | 3/5 |")

    def test_congestion_batching_tests_do_not_share_labels_with_the_glial_checks_Regression(self) -> None:
        labels = appendices.public_labels
        self.assertEqual(labels.public_label("G1", "congestion"), "B1")
        self.assertEqual(labels.public_label("G2", "congestion"), "B2")
        self.assertEqual(labels.public_label("G1", "glia"), "G1")
        self.assertEqual(labels.relabel_table_cells("| G1 | Batching |\n| W1 | Hub |", "congestion"), "| B1 | Batching |\n| W1 | Hub |")
        self.assertEqual(labels.relabel_table_cells("| G1 | Microglia |", "glia"), "| G1 | Microglia |")

    def test_every_public_label_is_unique_and_names_no_postulate(self) -> None:
        public = [label for _, _, label in appendices.public_labels.correspondence_rows()]
        self.assertEqual(len(public), len(set(public)))
        for label in public:
            self.assertNotRegex(label, r"^P\d")

    def test_report_sections_show_public_labels(self) -> None:
        with mock.patch.object(appendices, "report_name", return_value="species_full_x.md"), mock.patch.object(appendices, "latest_report", return_value="| P1b | rise | 18/20 |"):
            self.assertIn("| T1b | rise | 18/20 |", appendices.report_section("species"))


if __name__ == "__main__":
    unittest.main()
