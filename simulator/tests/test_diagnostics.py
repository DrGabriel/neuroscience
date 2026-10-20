"""The pieces of the 20 October diagnostics whose logic decides what their reports say."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "diagnostics"))

import phase_dynamics as dynamics  # noqa: E402
import phase_inertia_scan as scan  # noqa: E402
import reference_leak as leak  # noqa: E402

FEEDBACK, AROUSAL = 0.45, 0.5


class CoreReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.study_drive = dynamics.PhaseReferenceDrive(FEEDBACK, AROUSAL)
        self.phases = np.random.default_rng(1).uniform(0, 2 * np.pi, 8)
        self.is_core = np.array([False, False, True, True, True, True, True, True])

    def test_a_core_of_every_population_is_the_study_reference(self) -> None:
        everyone = np.ones(self.phases.size, dtype=bool)
        mean_field = np.exp(1j * self.phases).mean()
        np.testing.assert_allclose(leak.CoreReferenceDrive(self.study_drive, everyone)(self.phases, mean_field, 0.0), self.study_drive(self.phases, mean_field, 0.0))

    def test_sensory_phases_do_not_move_the_reference_felt_by_the_core(self) -> None:
        drive = leak.CoreReferenceDrive(self.study_drive, self.is_core)
        shifted = self.phases.copy()
        shifted[~self.is_core] += 1.0
        before = drive(self.phases, np.exp(1j * self.phases).mean(), 0.0)
        after = drive(shifted, np.exp(1j * shifted).mean(), 0.0)
        np.testing.assert_allclose(after[self.is_core], before[self.is_core])


class InertiaScanTests(unittest.TestCase):
    @staticmethod
    def result(loss: float | None, recovery: float | None) -> scan.ScanResult:
        return scan.ScanResult(scan.ScanTask(0.0, 0.6, 1), loss, recovery)

    def test_a_run_that_never_recovers_has_no_ratio_and_is_counted(self) -> None:
        summary = scan.cell_summary([self.result(1.4, None), self.result(None, None), self.result(1.4, 1.4)])
        self.assertIsNone(self.result(1.4, None).ratio)
        self.assertEqual((summary["never_recovered"], summary["never_lost"], summary["runs"]), (1, 1, 3))

    def test_hysteresis_of_exactly_one_grid_step_is_not_counted_as_wider(self) -> None:
        # 1.4 - 1.35 is 0.04999999999999982 in floating point: one step, not more.
        summary = scan.cell_summary([self.result(1.4, 1.35), self.result(1.4500000000000002, 1.35)])
        self.assertEqual(summary["ratios_above_one_step"], 1)


if __name__ == "__main__":
    unittest.main()
