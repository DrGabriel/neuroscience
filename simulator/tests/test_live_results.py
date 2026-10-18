"""Tests for saving results as they complete and resuming an interrupted batch."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import unittest.mock
from dataclasses import dataclass
from pathlib import Path

import reporting


@dataclass(frozen=True)
class SquareTask:
    value: int


def square(task: SquareTask) -> int:
    return task.value**2


def summary(done: list[int]) -> str:
    return f"{len(done)} squares, total {sum(done)}"


TASKS = [SquareTask(value) for value in range(6)]


class LiveResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        patcher = unittest.mock.patch.object(reporting, "RESULTS_DIRECTORY", Path(self.directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(reporting._CHECKPOINTS_THIS_PROCESS.clear)

    def run_batch(self, tasks: list[SquareTask], run: reporting.ParallelRun[int]) -> tuple[list[int], str]:
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            results = reporting.run_in_parallel(square, tasks, run)
        return results, errors.getvalue()

    def test_results_come_back_in_task_order(self) -> None:
        results, _ = self.run_batch(TASKS, reporting.ParallelRun("squares", workers=2))
        self.assertEqual(results, [value**2 for value in range(6)])

    def test_interrupted_batch_resumes_without_recomputing(self) -> None:
        self.run_batch(TASKS[:4], reporting.ParallelRun("squares", workers=2))
        with unittest.mock.patch.object(reporting, "ProcessPoolExecutor", wraps=reporting.ProcessPoolExecutor) as pool:
            results, log = self.run_batch(TASKS, reporting.ParallelRun("squares", workers=2))
        self.assertEqual(results, [value**2 for value in range(6)])
        self.assertIn("resuming: 4/6", log)
        self.assertEqual(pool.call_count, 1)

    def test_changed_code_invalidates_saved_results(self) -> None:
        self.run_batch(TASKS, reporting.ParallelRun("squares", workers=2))
        with unittest.mock.patch.object(reporting, "code_fingerprint", return_value="changed"):
            _, log = self.run_batch(TASKS, reporting.ParallelRun("squares", workers=2))
        self.assertNotIn("resuming", log)

    def test_abbreviated_task_descriptions_are_never_reused(self) -> None:
        checkpoint = reporting.Checkpoint("squares")
        warnings = io.StringIO()
        with contextlib.redirect_stderr(warnings):
            self.assertIsNone(checkpoint.key(square, "array([1, 2, ..., 9])"))
            self.assertIsNone(checkpoint.key(square, "<function f at 0x1>"))
        self.assertIn("cannot be resumed", warnings.getvalue())

    def test_live_summary_is_written_while_running_and_removed_on_publish(self) -> None:
        self.run_batch(TASKS, reporting.ParallelRun("squares", workers=2, live_markdown=summary))
        live = Path(self.directory.name) / reporting.LIVE_SUBDIRECTORY / "squares.md"
        self.assertIn("6 squares, total 55", live.read_text())
        document = {"label": "quick", "started_utc": "2026-10-18T00:00:00+00:00"}
        with contextlib.redirect_stdout(io.StringIO()):
            reporting.publish("squares", document, "final")
        self.assertFalse(live.exists())
        self.assertFalse(live.with_suffix(".pickle").exists())


if __name__ == "__main__":
    unittest.main()
