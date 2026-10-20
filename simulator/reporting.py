"""Shared reporting for the studies: descriptive statistics, Markdown tables and report files.

Standard library only, so that every study, including the standard-library-only ones, uses it.
"""

from __future__ import annotations

import hashlib
import json
import math
import pickle
import re
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Generic, Sequence, TypeVar

import provenance

RESULTS_DIRECTORY = Path(__file__).resolve().parent / "results"
LIVE_SUBDIRECTORY = "live"
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
NORMAL_95_PERCENT_Z = 1.959964
NOT_APPLICABLE = "n/a"
TEST = "test"
CONSISTENCY_CHECK = "consistency check"
LIVE_REPORT_INTERVAL_SECONDS = 30.0

Run = TypeVar("Run")
Task = TypeVar("Task")
Result = TypeVar("Result")
SECONDS_PER_MINUTE = 60


@dataclass(frozen=True)
class ParallelRun(Generic[Result]):
    """How one batch of tasks is run: its progress label, worker count and optional live summary.

    live_markdown turns the results completed so far into a Markdown summary, written to
    results/live/ while the batch runs so that partial results can be read before it ends.
    """

    label: str
    workers: int | None = None
    live_markdown: Callable[[list[Result]], str] | None = None


def code_fingerprint() -> str:
    """Hash of the simulator modules loaded by the running study and the Python version.

    Any change to code that can affect a result invalidates saved results; report-only modules
    that the study never imports (figures, appendices) do not.
    """
    digest = hashlib.sha256(sys.version.encode())
    for path in provenance.loaded_sources():
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class Checkpoint:
    """Results of completed tasks, appended to disk as each finishes so an interrupted batch resumes.

    A task is reused only when the same function ran it on an identical task description under
    identical source code; tasks whose description is not reproducible are always rerun.
    """

    def __init__(self, label: str) -> None:
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        self.directory = RESULTS_DIRECTORY / LIVE_SUBDIRECTORY
        self.path = self.directory / f"{slug}.pickle"
        self.summary_path = self.directory / f"{slug}.md"
        self._fingerprint = code_fingerprint()

    def key(self, work: Callable[..., object], task: object) -> str | None:
        """None when the task's description is not reproducible, so its result is never reused."""
        description = repr(task)
        if " at 0x" in description or "..." in description:
            print(f"[{self.path.stem}] task cannot be resumed (its description is not reproducible): {description[:80]}", file=sys.stderr)
            return None
        return hashlib.sha256(f"{self._fingerprint}|{work.__module__}.{work.__qualname__}|{description}".encode()).hexdigest()

    def load(self) -> dict[str, object]:
        saved: dict[str, object] = {}
        if not self.path.exists():
            return saved
        with self.path.open("rb") as handle:
            while True:
                try:
                    key, result = pickle.load(handle)
                except EOFError:
                    return saved
                saved[key] = result

    def save(self, key: str | None, result: object) -> None:
        if key is None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("ab") as handle:
            pickle.dump((key, result), handle)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
        self.summary_path.unlink(missing_ok=True)
        if self.directory.exists() and not any(self.directory.iterdir()):
            self.directory.rmdir()


_CHECKPOINTS_THIS_PROCESS: list[Checkpoint] = []


def run_in_parallel(work: Callable[[Task], Result], tasks: Sequence[Task], run: ParallelRun[Result]) -> list[Result]:
    """Run tasks across processes and return results in task order, saving each result as it completes.

    Each task carries its own seed, so completion order does not affect any result. Results saved
    by an earlier, interrupted run of identical code are reused instead of being recomputed.
    """
    checkpoint = Checkpoint(run.label)
    _CHECKPOINTS_THIS_PROCESS.append(checkpoint)
    keys = [checkpoint.key(work, task) for task in tasks]
    saved = checkpoint.load()
    results: list[Result | None] = [saved.get(key) if key is not None else None for key in keys]
    pending = [index for index, result in enumerate(results) if result is None]
    reused = len(tasks) - len(pending)
    if reused:
        print(f"[{run.label}] resuming: {reused}/{len(tasks)} tasks already completed", file=sys.stderr, flush=True)
    started = time.monotonic()
    last_summary = 0.0
    with ProcessPoolExecutor(max_workers=run.workers) as executor:
        futures = {executor.submit(work, tasks[index]): index for index in pending}
        for done, future in enumerate(as_completed(futures), start=1):
            index = futures[future]
            results[index] = future.result()
            checkpoint.save(keys[index], results[index])
            elapsed = time.monotonic() - started
            report_progress(run.label, reused + done, len(tasks), elapsed, done)
            if run.live_markdown and (done == len(pending) or elapsed - last_summary >= LIVE_REPORT_INTERVAL_SECONDS):
                write_live_summary(checkpoint, run, [r for r in results if r is not None], len(tasks))
                last_summary = elapsed
    return results  # type: ignore[return-value]


def write_live_summary(checkpoint: Checkpoint, run: ParallelRun[Result], completed: list[Result], total: int) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = f"## Live results: {run.label}\n\n{len(completed)}/{total} tasks completed, updated {stamp}. Partial results; the final report replaces this file.\n\n"
    checkpoint.directory.mkdir(parents=True, exist_ok=True)
    checkpoint.summary_path.write_text(header + run.live_markdown(completed))


def report_progress(label: str, done: int, total: int, elapsed_seconds: float, computed: int | None = None) -> None:
    """One line on standard error per completed task: count, percentage, elapsed and estimated remaining time.

    computed is how many of the done tasks ran in this process, which sets the pace estimate when
    earlier ones were reused from a checkpoint.
    """
    pace = elapsed_seconds / (computed or done)
    remaining_seconds = pace * (total - done)
    print(
        f"[{label}] {done}/{total} ({100 * done / total:.0f}%) · "
        f"{elapsed_seconds / SECONDS_PER_MINUTE:.1f} min elapsed · about {remaining_seconds / SECONDS_PER_MINUTE:.1f} min left",
        file=sys.stderr,
        flush=True,
    )


@dataclass(frozen=True)
class Distribution:
    """Mean, sample SD and normal-approximation 95% confidence half-width of the defined values."""

    defined_count: int
    total_count: int
    mean: float | None
    standard_deviation: float | None
    confidence_half_width_95: float | None

    @classmethod
    def of(cls, values: Sequence[float | None]) -> Distribution:
        defined = [value for value in values if value is not None]
        if not defined:
            return cls(0, len(values), None, None, None)
        spread = statistics.stdev(defined) if len(defined) > 1 else 0.0
        half_width = NORMAL_95_PERCENT_Z * spread / math.sqrt(len(defined))
        return cls(len(defined), len(values), statistics.fmean(defined), spread, half_width)

    def describe(self) -> str:
        if self.mean is None:
            return f"not reached (0/{self.total_count})"
        text = f"{self.mean:.3f} ± {self.standard_deviation:.3f}"
        return text if self.defined_count == self.total_count else f"{text} ({self.defined_count}/{self.total_count})"


def describe(values: Sequence[float | None]) -> str:
    """Mean ± sample SD of the defined values, noting how many were undefined."""
    return Distribution.of(values).describe()


def markdown_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    return [
        f"| {' | '.join(header)} |",
        f"|{'---|' * len(header)}",
        *[f"| {' | '.join(row)} |" for row in rows],
    ]


@dataclass(frozen=True)
class Check(Generic[Run]):
    """A claim, pillar or test evaluated once per run; it returns None where it is undefined.

    kind separates tests, which the model could fail, from consistency checks, which follow from
    the model's equations and confirm only that the code implements them.
    """

    identifier: str
    statement: str
    holds_for: Callable[[Run], bool | None]
    kind: str = TEST


@dataclass(frozen=True)
class CheckOutcome:
    identifier: str
    statement: str
    group: str
    runs_holding: int
    runs_applicable: int
    kind: str = TEST

    @property
    def holds(self) -> bool:
        """True when the check holds in every run where it is defined; false when it is defined in none."""
        return self.runs_applicable > 0 and self.runs_holding == self.runs_applicable

    def cell(self) -> str:
        """Count with its Wilson 95% confidence interval for the share of runs in which the check holds."""
        if self.runs_applicable == 0:
            return NOT_APPLICABLE
        low, high = wilson_interval(self.runs_holding, self.runs_applicable)
        return f"{self.runs_holding}/{self.runs_applicable} ({100 * low:.0f}–{100 * high:.0f}%)"


def outcome_sections(sections: Sequence[tuple[str, Sequence[CheckOutcome]]], group_names: Sequence[str]) -> str:
    """One Markdown table per titled group of outcomes, as used by the live summaries."""
    return "\n".join(line for title, outcomes in sections for line in (f"### {title}", "", *outcome_table(outcomes, group_names), ""))


def wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion (Wilson, 1927); sound for small counts and for 0 or n."""
    z = NORMAL_95_PERCENT_Z
    share = successes / trials
    denominator = 1 + z**2 / trials
    centre = (share + z**2 / (2 * trials)) / denominator
    half_width = z * math.sqrt(share * (1 - share) / trials + z**2 / (4 * trials**2)) / denominator
    return max(0.0, centre - half_width), min(1.0, centre + half_width)


def evaluate(checks: Sequence[Check[Run]], groups: dict[str, Sequence[Run]]) -> list[CheckOutcome]:
    outcomes = []
    for check in checks:
        for name, runs in groups.items():
            verdicts = [verdict for verdict in map(check.holds_for, runs) if verdict is not None]
            if runs:
                outcomes.append(CheckOutcome(check.identifier, check.statement, name, sum(verdicts), len(verdicts), check.kind))
    return outcomes


def outcome_table(outcomes: Sequence[CheckOutcome], group_names: Sequence[str]) -> list[str]:
    identifiers = list(dict.fromkeys(outcome.identifier for outcome in outcomes))
    rows = []
    for identifier in identifiers:
        matching = {outcome.group: outcome for outcome in outcomes if outcome.identifier == identifier}
        first = next(iter(matching.values()))
        cells = [matching[g].cell() if g in matching else "not run" for g in group_names]
        rows.append([identifier, first.statement, first.kind, *cells])
    return markdown_table(["ID", "Statement", "Kind", *group_names], rows)


def run_metadata_section(document: dict[str, object], provenance_rows: Sequence[str]) -> list[str]:
    """The run-metadata table shared by every report: timestamps first, then provenance rows."""
    rows = [["Started (UTC)", str(document["started_utc"])], ["Finished (UTC)", str(document["finished_utc"])]]
    return ["### Run metadata", "", *markdown_table(["Field", "Value"], rows), *provenance_rows, ""]


def publish(kind: str, document: dict[str, object], markdown: str) -> tuple[Path, Path]:
    """Write the JSON and Markdown reports, named by study kind, label and start time, and print the summary."""
    RESULTS_DIRECTORY.mkdir(exist_ok=True)
    started = datetime.fromisoformat(str(document["started_utc"]))
    stem = RESULTS_DIRECTORY / f"{kind}_{document['label']}_{started.strftime(TIMESTAMP_FORMAT)}"
    json_path, markdown_path = stem.with_suffix(".json"), stem.with_suffix(".md")
    json_path.write_text(json.dumps(document, indent=2, default=str, ensure_ascii=False))
    markdown_path.write_text(markdown)
    print(markdown)
    print(f"Reports written to {json_path.name} and {markdown_path.name} in {RESULTS_DIRECTORY.name}/")
    clear_checkpoints()
    return json_path, markdown_path


def clear_checkpoints() -> None:
    """Remove the saved partial results of this process once its final report exists."""
    while _CHECKPOINTS_THIS_PROCESS:
        _CHECKPOINTS_THIS_PROCESS.pop().clear()
