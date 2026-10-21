"""Result provenance must read the same wherever the repository is cloned."""

from __future__ import annotations

import argparse
import unittest

from analysis.open_data import outputs

INSIDE = outputs.REPO / "analysis" / "open_data" / "results" / "a_run"
OUTSIDE = "/elsewhere/raw/sub-01"
A_NUMBER = 20


class PortableArgumentTests(unittest.TestCase):
    def test_an_output_folder_inside_the_repository_is_recorded_relative_to_its_root_Regression(self) -> None:
        # The confirmatory and exploratory results of 21 October 2026 recorded the absolute output folder of the
        # machine that ran them, which fails the repository's portability test.
        arguments = outputs.provenance(argparse.Namespace(out=INSIDE))["arguments"]
        self.assertEqual(arguments["out"], "analysis/open_data/results/a_run")

    def test_a_value_that_is_not_a_repository_path_is_kept_as_given(self) -> None:
        self.assertEqual(outputs.portable(OUTSIDE), OUTSIDE)
        self.assertEqual(outputs.portable(A_NUMBER), str(A_NUMBER))


if __name__ == "__main__":
    unittest.main()
