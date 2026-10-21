"""The explainer export's handling of repeated test outcomes."""

from __future__ import annotations

import unittest

import explainer_export as export

REPORT = "a_report.json"


def an_outcome(holding: int) -> dict[str, object]:
    return {"identifier": "T2a-M", "group": "Human", "holding": holding, "applicable": 20}


class RepeatTests(unittest.TestCase):
    def test_an_outcome_listed_twice_with_identical_results_is_kept_once_Regression(self) -> None:
        # The readout study of 20 October 2026 lists a test once per calibrated coupling, and two connectomes were
        # calibrated to the same coupling, so their weaker-coupling tests appear twice with identical results.
        self.assertEqual(export.without_repeats(REPORT, [an_outcome(20), an_outcome(20)]), [an_outcome(20)])

    def test_an_outcome_listed_twice_with_different_results_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            export.without_repeats(REPORT, [an_outcome(20), an_outcome(19)])


if __name__ == "__main__":
    unittest.main()
