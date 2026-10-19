"""Catalogue of every study report, current and archived, for the explainer's results archive.

Every JSON report in results/ and results/archive/<set>/ is listed with its study, label, start and
finish times, machine, Git commit and a count of its checks. Each report is also wrapped in a small
script (Markdown and JSON together) that the explainer loads on demand, because a page opened from
file:// cannot fetch files. Reports are never changed or removed; this script only reads them.

Usage: python3 results_catalogue.py
Standard library only.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

import provenance
import reporting

EXPLAINER_DATA = Path(__file__).resolve().parent.parent / "explainer" / "data" / "results"
CATALOGUE_FILE = EXPLAINER_DATA / "catalogue.js"
ARCHIVE = reporting.RESULTS_DIRECTORY / "archive"
CURRENT_SET = "current"
# Paths the explainer links to, relative to explainer/index.html.
LINK_BASE = "../simulator/results"
# A check outcome is any record carrying every field CheckOutcome requires.
OUTCOME_FIELDS = tuple(field.name for field in dataclasses.fields(reporting.CheckOutcome) if field.default is dataclasses.MISSING)
# The machine is named by its model and processor, the first two keys provenance records.
MACHINE_KEYS = provenance.SYSCTL_KEYS[:2]
LICENCE_NOTE = "Study reports of the DPC simulator; text CC BY 4.0, see NOTICE.md."


@dataclass(frozen=True)
class CheckCount:
    checks: int
    holding_in_every_run: int
    holding_in_none: int


@dataclass(frozen=True)
class CatalogueEntry:
    identifier: str
    kind: str
    label: str
    report_set: str
    set_note: str
    started_utc: str
    machine: str
    git_commit: str
    working_tree_dirty: bool | None
    checks: CheckCount
    has_curves: bool
    json_link: str
    markdown_link: str | None
    script: str


def report_sets() -> Iterator[tuple[str, str, Path]]:
    """(set name, note, directory): the current reports first, then each archived set."""
    yield CURRENT_SET, "", reporting.RESULTS_DIRECTORY
    for directory in sorted(path for path in ARCHIVE.glob("*") if path.is_dir()):
        readme = directory / "README.md"
        note = readme.read_text().splitlines()[0].lstrip("# ").strip() if readme.exists() else ""
        yield directory.name, note, directory


@dataclass(frozen=True)
class ReportName:
    """kind_label_timestamp, as reporting.publish names every report."""

    kind: str
    label: str

    @classmethod
    def of(cls, path: Path) -> ReportName:
        parts = path.stem.rsplit("_", 2)
        try:
            kind, label, stamp = parts
            datetime.strptime(stamp, reporting.TIMESTAMP_FORMAT)
        except ValueError:
            raise ValueError(f"{path.name}: not a study report name (kind_label_timestamp)") from None
        return cls(kind, label)


def check_outcomes(node: object) -> Iterator[dict]:
    """Every check outcome anywhere in a report, whatever list it sits in."""
    if isinstance(node, dict):
        if all(field in node for field in OUTCOME_FIELDS):
            yield node
            return
        for value in node.values():
            yield from check_outcomes(value)
    elif isinstance(node, list):
        for value in node:
            yield from check_outcomes(value)


def count_checks(document: dict) -> CheckCount:
    outcomes = [o for o in check_outcomes(document) if o["runs_applicable"]]
    return CheckCount(
        checks=len(outcomes),
        holding_in_every_run=sum(o["runs_holding"] == o["runs_applicable"] for o in outcomes),
        holding_in_none=sum(o["runs_holding"] == 0 for o in outcomes),
    )


def machine_of(provenance: dict) -> str:
    hardware = provenance.get("hardware", {})
    return " · ".join(str(hardware[key]) for key in MACHINE_KEYS if key in hardware)


def has_curves(document: dict) -> bool:
    runs = document.get("runs")
    return isinstance(runs, list) and bool(runs) and isinstance(runs[0], dict) and "induction_coherence" in runs[0]


@dataclass(frozen=True)
class Report:
    """One report as read from disk: its JSON document and its Markdown twin, if there is one."""

    path: Path
    report_set: str
    note: str
    document: dict
    markdown: str | None

    @classmethod
    def read(cls, path: Path, report_set: str, note: str) -> Report:
        markdown = path.with_suffix(".md")
        return cls(path, report_set, note, json.loads(path.read_text()), markdown.read_text() if markdown.exists() else None)

    def link(self, suffix: str) -> str:
        return f"{LINK_BASE}/{self.path.with_suffix(suffix).relative_to(reporting.RESULTS_DIRECTORY).as_posix()}"


def script_path(report_set: str, stem: str) -> Path:
    return EXPLAINER_DATA / report_set / f"{stem}.js"


def entry_for(report: Report) -> CatalogueEntry:
    name = ReportName.of(report.path)
    source = report.document.get("provenance", {}).get("source", {})
    return CatalogueEntry(
        identifier=f"{report.report_set}/{report.path.stem}",
        kind=name.kind,
        label=name.label,
        report_set=report.report_set,
        set_note=report.note,
        started_utc=str(report.document.get("started_utc", "")),
        machine=machine_of(report.document.get("provenance", {})),
        git_commit=str(source.get("git_commit", "")),
        working_tree_dirty=source.get("git_working_tree_dirty"),
        checks=count_checks(report.document),
        has_curves=has_curves(report.document),
        json_link=report.link(".json"),
        markdown_link=report.link(".md") if report.markdown is not None else None,
        script=script_path(report.report_set, report.path.stem).relative_to(EXPLAINER_DATA.parent.parent).as_posix(),
    )


def wrapper(entry: CatalogueEntry, report: Report) -> str:
    body = json.dumps({"markdown": report.markdown or "", "document": report.document}, ensure_ascii=False, separators=(",", ":"))
    return f"/* Generated by simulator/results_catalogue.py from {report.path.name}. {LICENCE_NOTE} */\nglobalThis.DPC_RESULT_LOADED({json.dumps(entry.identifier)}, {body});\n"


def remove_stale_wrappers(written: set[Path]) -> None:
    """Wrappers are generated copies: one left behind by a report that moved to the archive would list it twice."""
    for stale in set(EXPLAINER_DATA.glob("*/*.js")) - written:
        stale.unlink()


def write_catalogue() -> list[CatalogueEntry]:
    entries, written = [], set()
    for report_set, note, directory in report_sets():
        for path in sorted(directory.glob("*.json")):
            report = Report.read(path, report_set, note)
            entry = entry_for(report)
            target = script_path(report_set, path.stem)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(wrapper(entry, report))
            written.add(target)
            entries.append(entry)
    remove_stale_wrappers(written)
    listing = json.dumps([asdict(entry) for entry in entries], ensure_ascii=False, indent=1)
    CATALOGUE_FILE.write_text(f"/* Generated by simulator/results_catalogue.py; do not edit by hand. {LICENCE_NOTE} */\nglobalThis.DPC_RESULTS_CATALOGUE = Object.freeze({listing});\n")
    return entries


def main() -> int:
    entries = write_catalogue()
    sets = sorted({entry.report_set for entry in entries})
    print(f"Catalogued {len(entries)} reports in {len(sets)} sets ({', '.join(sets)}) into {CATALOGUE_FILE.relative_to(CATALOGUE_FILE.parents[2])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
