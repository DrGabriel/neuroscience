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


if __name__ == "__main__":
    unittest.main()
