"""Round 3, deviation D8 and its launcher: per-subject seeds, order independence, the listing and the launcher, on synthetic data."""

from __future__ import annotations

import argparse
import json
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from analysis.open_data import launch_reseeded, reseeded, run, settings
from analysis.open_data.loaders import RunLocation
from analysis.open_data.tests.test_datasets_end_to_end import write_michigan

PARCELS, VOLUMES = 12, 600
NULL_REALISATIONS, SURROGATES = "3", "20"
FIRST, SECOND = "sub-01", "sub-03"
SECOND_NUMBER = 3
TIMING = "Subject,LOR time (TR in task2),ROR time (TR in task3)\nsub-01,200,300\nsub-03,200,300\n"
UNCOMPARED = ("provenance", "seconds")
EARLIER_SECONDS = {FIRST: 100.0, SECOND: 300.0}
FAILING_EXIT = 3
FAKE_INTERPRETER = f"""#!/bin/sh
while [ $# -gt 0 ]; do
  case "$1" in --subject) subject=$2 ;; --out) out=$2 ;; esac
  shift
done
if [ "$subject" = "{SECOND}" ]; then echo "boom in $subject" >&2; exit {FAILING_EXIT}; fi
mkdir -p "$out" && echo '{{"seconds": 1}}' > "$out/michigan_$subject.json"
"""


def two_subject_root(tmp: Path) -> Path:
    """Two synthetic subjects with different data; the second is written under its own name."""
    root, other = tmp / "michigan", tmp / "other"
    write_michigan(root, PARCELS, VOLUMES, np.random.default_rng(1), all_runs=True)
    write_michigan(other, PARCELS, VOLUMES, np.random.default_rng(2), all_runs=True)
    for path in sorted(p for p in other.rglob(f"*{FIRST}*") if p.is_file()):
        target = root / str(path.relative_to(other)).replace(FIRST, SECOND)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (root / "derivatives" / "LOR_ROR_Timing.csv").write_text(TIMING)
    return root


def comparable(path: Path) -> dict:
    return {k: v for k, v in json.loads(path.read_text()).items() if k not in UNCOMPARED}


def arguments(root: Path, subjects: list[str], out: Path) -> argparse.Namespace:
    return argparse.Namespace(root=str(root), subject=subjects, out=str(out), null_realisations=int(NULL_REALISATIONS), surrogates=int(SURROGATES), check_only=False)


class SeedTests(unittest.TestCase):
    def test_each_subject_is_seeded_with_the_committed_seed_plus_its_number(self) -> None:
        self.assertEqual(reseeded.subject_seed(SECOND), settings.SEED + SECOND_NUMBER)
        with self.assertRaises(ValueError):
            reseeded.subject_seed("subject-3")


class OrderIndependenceTests(unittest.TestCase):
    def test_a_subject_gives_the_same_result_whatever_its_place_in_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(reseeded.deviations, "apply_deviations") as applied, mock.patch.object(run, "michigan", run.michigan):
            tmp = Path(tmp)
            root = two_subject_root(tmp)
            reseeded.michigan_reseeded(arguments(root, [FIRST, SECOND], tmp / "forwards"))
            command = ["michigan", "--root", str(root), "--subject", SECOND, "--subject", FIRST, "--out", str(tmp / "backwards")]
            reseeded.main([*command, "--null-realisations", NULL_REALISATIONS, "--surrogates", SURROGATES])
            results = {(d, s): comparable(tmp / d / reseeded.result_name(s)) for d in ("forwards", "backwards") for s in (FIRST, SECOND)}
        applied.assert_called_once()
        for subject in (FIRST, SECOND):
            self.assertEqual(results[("forwards", subject)], results[("backwards", subject)])
        self.assertEqual(results[("forwards", SECOND)][reseeded.SEED_FIELD], settings.SEED + SECOND_NUMBER)


def a_result(folder: Path, name: str, payload: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(json.dumps(payload))
    return path


class ListingTests(unittest.TestCase):
    def previous(self, tmp: Path) -> Path:
        earlier = tmp / "exploratory"
        paths = [a_result(earlier, reseeded.result_name(FIRST), {"seconds": 1}), a_result(earlier, "neurotycho_x.json", {}), a_result(earlier, "prios_y.json", {})]
        listing = earlier / "group_inputs.txt"
        listing.write_text("\n".join(str(p) for p in paths))
        return listing

    def test_only_michigan_files_are_replaced_by_their_reseeded_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            listing = self.previous(tmp)
            new = a_result(tmp / "reseeded", reseeded.result_name(FIRST), {reseeded.SEED_FIELD: reseeded.subject_seed(FIRST)})
            lines = reseeded.reseeded_listing(listing, tmp / "reseeded")
        self.assertEqual([Path(line).name for line in lines], [reseeded.result_name(FIRST), "neurotycho_x.json", "prios_y.json"])
        self.assertEqual(Path(lines[0]), new)
        self.assertEqual(Path(lines[1]).parent.name, "exploratory")

    def test_a_missing_reseeded_file_a_wrong_seed_or_an_unlisted_file_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            listing = self.previous(tmp)
            with self.assertRaises(FileNotFoundError):
                reseeded.reseeded_listing(listing, tmp / "reseeded")
            a_result(tmp / "reseeded", reseeded.result_name(FIRST), {reseeded.SEED_FIELD: settings.SEED})
            with self.assertRaises(ValueError):
                reseeded.reseeded_listing(listing, tmp / "reseeded")
            a_result(tmp / "reseeded", reseeded.result_name(FIRST), {reseeded.SEED_FIELD: reseeded.subject_seed(FIRST)})
            a_result(tmp / "reseeded", reseeded.result_name(SECOND), {reseeded.SEED_FIELD: reseeded.subject_seed(SECOND)})
            with self.assertRaises(FileNotFoundError):
                reseeded.reseeded_listing(listing, tmp / "reseeded")


LPT_DURATIONS, LPT_TWO_PROCESSES, LPT_LONGEST = [4.0, 3.0, 3.0, 2.0, 2.0], 8.0, 4.0
MANY_PROCESSES = 10


class LauncherTests(unittest.TestCase):
    def layout(self, tmp: Path, missing_run: int | None = None) -> list[str]:
        """A dataset of empty files with the real names, earlier results with run times, and the launcher's arguments."""
        root = tmp / "data"
        (root / "derivatives").mkdir(parents=True)
        (root / "derivatives" / "LOR_ROR_Timing.csv").touch()
        for subject in EARLIER_SECONDS:
            for number in launch_reseeded.REQUIRED_RUNS:
                if (subject, number) != (SECOND, missing_run):
                    path = RunLocation(root, subject, number).timeseries
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
        earlier = [a_result(tmp / "earlier", reseeded.result_name(s), {"seconds": t}) for s, t in EARLIER_SECONDS.items()]
        (tmp / "earlier" / "inputs.txt").write_text("\n".join(str(p) for p in earlier))
        interpreter = tmp / "fake_python"
        interpreter.write_text(FAKE_INTERPRETER)
        interpreter.chmod(interpreter.stat().st_mode | stat.S_IXUSR)
        return ["--root", str(root), "--previous", str(tmp / "earlier" / "inputs.txt"), "--out", str(tmp / "out"), "--python", str(interpreter), "--processes", "2"]

    def report(self, tmp: Path, name: str) -> list[dict]:
        return [json.loads(line) for line in (tmp / "out" / launch_reseeded.LOG_FOLDER / name).read_text().splitlines()]

    def test_longest_first_on_two_processes_has_a_known_wall_time(self) -> None:
        self.assertEqual(launch_reseeded.makespan(LPT_DURATIONS, 2), LPT_TWO_PROCESSES)
        self.assertEqual(launch_reseeded.makespan(LPT_DURATIONS, MANY_PROCESSES), LPT_LONGEST)
        self.assertEqual(launch_reseeded.makespan([], 2), 0.0)

    def test_dry_run_plans_longest_first_skips_existing_results_and_starts_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(launch_reseeded.subprocess, "run") as started:
            tmp = Path(tmp)
            argv = self.layout(tmp)
            a_result(tmp / "out", reseeded.result_name(FIRST), {"seconds": 1})
            self.assertEqual(launch_reseeded.main(argv), 0)
            entries = self.report(tmp, launch_reseeded.DRY_RUN_REPORT_NAME)
        started.assert_not_called()
        self.assertEqual([(e["subject"], e["outcome"]) for e in entries], [(SECOND, launch_reseeded.PLANNED), (FIRST, launch_reseeded.SKIPPED)])
        self.assertIn("analysis.open_data.reseeded", entries[0]["command"])

    def test_dry_run_fails_when_a_run_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            argv = self.layout(tmp, missing_run=launch_reseeded.REQUIRED_RUNS[-1])
            self.assertEqual(launch_reseeded.main(argv), 1)
            failures = [e for e in self.report(tmp, launch_reseeded.DRY_RUN_REPORT_NAME) if e["outcome"] == launch_reseeded.CHECK_FAILED]
        self.assertEqual([f["subject"] for f in failures], [SECOND])

    def test_execute_reports_a_failure_in_full_and_a_rerun_skips_what_is_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            argv = [*self.layout(tmp), "--execute"]
            self.assertEqual(launch_reseeded.main(argv), 1)
            self.assertTrue((tmp / "out" / reseeded.result_name(FIRST)).exists())
            self.assertEqual(launch_reseeded.main(argv), 1)
            entries = self.report(tmp, launch_reseeded.REPORT_NAME)
        failed = [e for e in entries if e["outcome"] == launch_reseeded.FAILED]
        self.assertEqual([f["subject"] for f in failed], [SECOND, SECOND])
        self.assertEqual(failed[0]["exit_code"], FAILING_EXIT)
        self.assertTrue(any("boom" in line for line in failed[0]["log_tail"]))
        outcomes = [(e.get("subject"), e["outcome"]) for e in entries]
        self.assertEqual(outcomes.count((FIRST, launch_reseeded.DONE)), 1)
        self.assertIn((FIRST, launch_reseeded.SKIPPED), outcomes)

    def test_an_unreadable_existing_result_is_run_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / reseeded.result_name(FIRST)
            result.write_text("{ truncated")
            self.assertEqual(launch_reseeded.action_for(result), launch_reseeded.RERUN)


if __name__ == "__main__":
    unittest.main()
