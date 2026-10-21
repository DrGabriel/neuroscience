"""Parallel launcher for the reseeded Michigan analysis (deviation D8): one process per subject, at most N at a time.

Dry run by default. It lists every subject, whether its result already exists (it is then skipped), the exact
command, the time the subject took in the earlier run and the expected wall time on N processes, and it checks that
the interpreter, the dataset's timing table and each subject's runs are present (by file name only; no file is
opened). It starts nothing and writes only its report. With --execute it runs the subjects, longest expected first,
each in its own process with its own log file. Every failure is printed with the subject, the command, the exit code
and the end of its log, and appended to the report (one JSON object per line). A summary closes every run, and the
exit status is non-zero if any check or any subject failed, in either mode. Re-running skips every subject whose
result file exists and reads as JSON, so an interrupted run is resumed by running the same command again.

Usage, from the repository root:
    .venv/bin/python -E -s -m analysis.open_data.launch_reseeded --root data_external/ds006623 \
        --previous analysis/open_data/results/2026-10-21/exploratory/group_inputs.txt --out <folder> [--execute]
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import outputs, reseeded
from .constants import Dataset
from .loaders import RunLocation, michigan_run_exists
from .loaders.michigan import TIMING_TABLE
from .pipeline_michigan import AWAKE_RUN, EMERGENCE_RUNS, INDUCTION_RUN
from .round3_settings import LAUNCHER

MODULE = "analysis.open_data.reseeded"
INTERPRETER_FLAGS = ("-E", "-s", "-m")
DEFAULT_PYTHON = outputs.REPO / ".venv" / "bin" / "python"
SINGLE_THREAD = {name: "1" for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")}
REQUIRED_RUNS = (AWAKE_RUN, INDUCTION_RUN, EMERGENCE_RUNS[0])
DERIVATIVES = "derivatives"
REPORT_NAME, LOG_FOLDER = "launch_report.ndjson", "logs"
DRY_RUN_REPORT_NAME = "launch_report.dry-run.ndjson"
SECONDS_FIELD, SECONDS_PER_HOUR = "seconds", 3600.0
RUN, SKIP, RERUN = "run", "skip (result exists)", "run again (existing result unreadable)"
PLANNED, DONE, FAILED, CHECK_FAILED, SKIPPED = "planned", "done", "failed", "check failed", "skipped"
LOG_SUFFIX = ".log"


@dataclass(frozen=True)
class Config:
    root: Path
    out: Path
    subjects: tuple[str, ...]
    expected_seconds: dict[str, float]
    processes: int
    python: Path
    execute: bool

    @property
    def logs(self) -> Path:
        return self.out / LOG_FOLDER

    @property
    def report(self) -> Path:
        return self.out / LOG_FOLDER / (REPORT_NAME if self.execute else DRY_RUN_REPORT_NAME)


@dataclass(frozen=True)
class Job:
    subject: str
    action: str
    expected_seconds: float
    command: tuple[str, ...]

    @property
    def runs(self) -> bool:
        return self.action != SKIP


@dataclass
class Reporter:
    """Prints every outcome and appends it to the report as one JSON object per line."""

    path: Path
    counts: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, outcome: str, entry: dict) -> None:
        line = {"time_utc": time.strftime(outputs.UTC_FORMAT, time.gmtime()), "outcome": outcome, **entry}
        with self.lock:
            self.counts[outcome] = self.counts.get(outcome, 0) + 1
            with self.path.open("a") as handle:
                handle.write(json.dumps(line) + "\n")
            stream = sys.stderr if outcome in (FAILED, CHECK_FAILED) else sys.stdout
            print(json.dumps(line), file=stream, flush=True)


def listed_michigan(previous: Path) -> list[Path]:
    return [p for p in exploratory_paths(previous) if p.name.startswith(f"{Dataset.MICHIGAN}_")]


def exploratory_paths(previous: Path) -> list[Path]:
    return [outputs.REPO / line for line in previous.read_text().split()]


def subject_of(path: Path) -> str:
    return path.name.removeprefix(f"{Dataset.MICHIGAN}_").removesuffix(reseeded.RESULT_SUFFIX)


def earlier_seconds(previous: Path) -> dict[str, float]:
    """Seconds each subject took in the earlier run (the result files' 'seconds' field), for ordering and estimates."""
    return {subject_of(p): float(json.loads(p.read_text())[SECONDS_FIELD]) for p in listed_michigan(previous)}


def readable(path: Path) -> bool:
    try:
        json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    return True


def action_for(result: Path) -> str:
    if not result.exists():
        return RUN
    return SKIP if readable(result) else RERUN


def command_for(config: Config, subject: str) -> tuple[str, ...]:
    arguments = ("michigan", "--root", outputs.portable(config.root), "--subject", subject, "--out", outputs.portable(config.out))
    return (str(config.python), *INTERPRETER_FLAGS, MODULE, *arguments)


def plan(config: Config) -> list[Job]:
    """Every subject, longest expected first; a subject whose result exists and reads as JSON is skipped."""
    known = sorted(config.expected_seconds.values())
    fallback = known[len(known) // 2] if known else 0.0
    jobs = [
        Job(s, action_for(config.out / reseeded.result_name(s)), config.expected_seconds.get(s, fallback), command_for(config, s))
        for s in config.subjects
    ]
    return sorted(jobs, key=lambda j: (-j.expected_seconds, j.subject))


def makespan(durations: list[float], processes: int) -> float:
    """Wall time when each job goes to the first free process in the given order (longest first: LPT)."""
    finish = [0.0] * max(1, min(processes, len(durations)))
    for duration in durations:
        heapq.heappush(finish, heapq.heappop(finish) + duration)
    return max(finish)


def check_errors(config: Config, jobs: list[Job]) -> list[dict]:
    """Everything a run needs that can be checked without opening a data file."""
    errors = [] if os.access(config.python, os.X_OK) else [{"check": "interpreter", "path": outputs.portable(config.python), "error": "not executable"}]
    if config.processes < 1:
        errors.append({"check": "processes", "error": f"--processes must be at least 1, not {config.processes}"})
    timing = config.root / DERIVATIVES / TIMING_TABLE
    if not timing.exists():
        errors.append({"check": "timing table", "path": outputs.portable(timing), "error": "missing"})
    return errors + [e for e in (_subject_error(config, j) for j in jobs if j.runs) if e is not None]


def _subject_error(config: Config, job: Job) -> dict | None:
    seed_error = _seed_error(job.subject)
    missing = [r for r in REQUIRED_RUNS if not michigan_run_exists(RunLocation(config.root, job.subject, r))]
    if not (missing or seed_error):
        return None
    return {"check": "subject", "subject": job.subject, "error": seed_error or f"runs missing: {missing}"}


def _seed_error(subject: str) -> str | None:
    try:
        reseeded.subject_seed(subject)
    except ValueError as error:
        return str(error)
    return None


def log_tail(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()[-LAUNCHER.log_tail_lines :] if path.exists() else []


def run_job(job: Job, config: Config, reporter: Reporter) -> None:
    """One subject in its own process; a non-zero exit or a missing result is a failure, reported in full."""
    log = config.logs / f"{job.subject}{LOG_SUFFIX}"
    started, entry = time.time(), {"subject": job.subject, "command": portable_command(job), "log": outputs.portable(log)}
    try:
        exit_code = started_process(job, log)
    except OSError as error:
        reporter.record(FAILED, {**entry, "error_type": type(error).__name__, "error": str(error)})
        return
    entry = {**entry, "exit_code": exit_code, SECONDS_FIELD: round(time.time() - started, 1)}
    if exit_code == 0 and readable_if_exists(config.out / reseeded.result_name(job.subject)):
        reporter.record(DONE, entry)
        return
    error = "non-zero exit" if exit_code else "process ended without a readable result file"
    reporter.record(FAILED, {**entry, "error_type": error, "log_tail": log_tail(log)})


def started_process(job: Job, log: Path) -> int:
    with log.open("w") as handle:
        completed = subprocess.run(job.command, cwd=outputs.REPO, stdout=handle, stderr=subprocess.STDOUT, env={**os.environ, **SINGLE_THREAD}, check=False)
    return completed.returncode


def portable_command(job: Job) -> list[str]:
    return [outputs.portable(part) for part in job.command]


def readable_if_exists(path: Path) -> bool:
    return path.exists() and readable(path)


def execute(config: Config, jobs: list[Job], reporter: Reporter) -> None:
    with ThreadPoolExecutor(max_workers=config.processes) as pool:
        futures = [pool.submit(run_job, job, config, reporter) for job in jobs if job.runs]
    for future in futures:
        future.result()


def report_plan(config: Config, jobs: list[Job], reporter: Reporter) -> None:
    for job in jobs:
        outcome = PLANNED if job.runs else SKIPPED
        reporter.record(outcome, {"subject": job.subject, "action": job.action, "expected_hours": round(job.expected_seconds / SECONDS_PER_HOUR, 2), "command": portable_command(job)})
    pending = [j.expected_seconds for j in jobs if j.runs]
    hours = makespan(pending, config.processes) / SECONDS_PER_HOUR if pending else 0.0
    print(f"{len(pending)} to run on {config.processes} processes; expected wall time {hours:.1f} h (from the earlier run's per-subject seconds)")


def summary(reporter: Reporter, total: int) -> int:
    counts = reporter.counts
    failures = counts.get(FAILED, 0) + counts.get(CHECK_FAILED, 0)
    print(f"summary: done {counts.get(DONE, 0)} / planned {counts.get(PLANNED, 0)} / skipped {counts.get(SKIPPED, 0)} / errors {failures} / subjects {total}; report {outputs.portable(reporter.path)}")
    return 1 if failures else 0


def launch(config: Config) -> int:
    config.logs.mkdir(parents=True, exist_ok=True)
    reporter, jobs = Reporter(config.report), plan(config)
    for error in check_errors(config, jobs):
        reporter.record(CHECK_FAILED, {"error_type": "check", **error})
    if not config.execute or reporter.counts.get(CHECK_FAILED):
        report_plan(config, jobs, reporter)
        return summary(reporter, len(jobs))
    reporter.record("started", {"processes": config.processes, "config": {k: outputs.portable(v) for k, v in asdict(config).items()}})
    report_plan(config, jobs, reporter)
    execute(config, jobs, reporter)
    return summary(reporter, len(jobs))


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument("--root", required=True, help="the Michigan dataset, data_external/ds006623")
    top.add_argument("--previous", required=True, help="the earlier group inputs (exploratory/group_inputs.txt): subjects and their run times")
    top.add_argument("--out", required=True, help="results/<run date>/exploratory_reseeded")
    top.add_argument("--subject", action="append", help="limit to these subjects (repeatable), for a staged first run")
    top.add_argument("--processes", type=int, default=LAUNCHER.processes)
    top.add_argument("--python", default=str(DEFAULT_PYTHON))
    top.add_argument("--execute", action="store_true", help="run the subjects; without it, nothing is started")
    return top


def config_from(arguments: argparse.Namespace) -> Config:
    previous = Path(arguments.previous)
    subjects = tuple(arguments.subject or [subject_of(p) for p in listed_michigan(previous)])
    expected = earlier_seconds(previous)
    paths = (Path(p).absolute() for p in (arguments.root, arguments.out, arguments.python))
    root, out, python = paths
    return Config(root, out, subjects, expected, arguments.processes, python, arguments.execute)


def main(argv: list[str] | None = None) -> int:
    return launch(config_from(parser().parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
