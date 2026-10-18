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


if __name__ == "__main__":
    unittest.main()
