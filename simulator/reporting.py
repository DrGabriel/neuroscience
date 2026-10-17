"""Shared reporting for the studies: descriptive statistics, Markdown tables and report files.

Standard library only, so that every study, including the standard-library-only ones, uses it.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Generic, Sequence, TypeVar

RESULTS_DIRECTORY = Path(__file__).resolve().parent / "results"
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%SZ"
NORMAL_95_PERCENT_Z = 1.959964
NOT_APPLICABLE = "n/a"

Run = TypeVar("Run")
Task = TypeVar("Task")
Result = TypeVar("Result")
SECONDS_PER_MINUTE = 60


def run_in_parallel(
    work: Callable[[Task], Result], tasks: Sequence[Task], label: str, workers: int | None = None
) -> list[Result]:
    """Run tasks across processes, report progress after each completion, and return results in task order.

    Each task carries its own seed, so completion order does not affect any result.
    """
    started = time.monotonic()
    results: list[Result | None] = [None] * len(tasks)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(work, task): index for index, task in enumerate(tasks)}
        for done, future in enumerate(as_completed(futures), start=1):
            results[futures[future]] = future.result()
            report_progress(label, done, len(tasks), time.monotonic() - started)
    return results  # type: ignore[return-value]


def report_progress(label: str, done: int, total: int, elapsed_seconds: float) -> None:
    """One line on standard error per completed task: count, percentage, elapsed and estimated remaining time."""
    remaining_seconds = elapsed_seconds / done * (total - done)
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
    """A claim, pillar or test evaluated once per run; it returns None where it is undefined."""

    identifier: str
    statement: str
    holds_for: Callable[[Run], bool | None]


@dataclass(frozen=True)
class CheckOutcome:
    identifier: str
    statement: str
    group: str
    runs_holding: int
    runs_applicable: int

    @property
    def holds(self) -> bool:
        """True when the check holds in every run where it is defined (vacuously if it is defined in none)."""
        return self.runs_holding == self.runs_applicable

    def cell(self) -> str:
        return NOT_APPLICABLE if self.runs_applicable == 0 else f"{self.runs_holding}/{self.runs_applicable}"


def evaluate(checks: Sequence[Check[Run]], groups: dict[str, Sequence[Run]]) -> list[CheckOutcome]:
    outcomes = []
    for check in checks:
        for name, runs in groups.items():
            verdicts = [verdict for verdict in map(check.holds_for, runs) if verdict is not None]
            if runs:
                outcomes.append(CheckOutcome(check.identifier, check.statement, name, sum(verdicts), len(verdicts)))
    return outcomes


def outcome_table(outcomes: Sequence[CheckOutcome], group_names: Sequence[str]) -> list[str]:
    identifiers = list(dict.fromkeys(outcome.identifier for outcome in outcomes))
    rows = []
    for identifier in identifiers:
        matching = {outcome.group: outcome for outcome in outcomes if outcome.identifier == identifier}
        statement = next(iter(matching.values())).statement
        cells = [matching[g].cell() if g in matching else "not run" for g in group_names]
        rows.append([identifier, statement, *cells])
    return markdown_table(["ID", "Statement", *group_names], rows)


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
    return json_path, markdown_path
