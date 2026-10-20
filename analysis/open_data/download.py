"""Fetch exactly the files the open-data tests read. Dry run by default: lists every file with its size and the total.

    .venv/bin/python -I analysis/open_data/download.py michigan            # list, download nothing
    .venv/bin/python -I analysis/open_data/download.py michigan --execute  # download
    (datasets: michigan, neurotycho, prios; scope with --limit N)

Files already present with the expected size are skipped, so a rerun resumes. Every failure is printed and appended
to <destination>/download_errors.ndjson, and the exit status is non-zero if any file failed, in either mode. Archives
are extracted only with --execute, member by member, refusing any member whose path would leave the destination.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "analysis.open_data"

from .catalogues import CATALOGUES, DESTINATION
from .constants import BYTES_PER_GIGABYTE, BYTES_PER_MEGABYTE, Dataset
from .transfer import Item, fetch, http_size, safe_extract, with_retries

ERRORS_FILE = "download_errors.ndjson"
TRANSFER_ERRORS = (urllib.error.URLError, OSError, ValueError, RuntimeError, zipfile.BadZipFile)
FAILED, SUCCEEDED = 1, 0


@dataclass
class Counts:
    downloaded: int = 0
    would_download: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0
    bytes: int = 0


@dataclass(frozen=True)
class Failure:
    attempt: str
    item: Item
    error: Exception = field(compare=False)

    def record(self) -> dict:
        error = {"error_type": type(self.error).__name__, "message": str(self.error)}
        return {"attempt": self.attempt, "url": self.item.url, "target": str(self.item.target), **error}


def report_error(errors_path: Path, failure: Failure) -> None:
    print(f"ERROR {failure.attempt} {failure.item.url}: {type(failure.error).__name__}: {failure.error}", file=sys.stderr)
    with errors_path.open("a") as handle:
        handle.write(json.dumps(failure.record()) + "\n")


def handle_item(item: Item, counts: Counts, *, execute: bool) -> None:
    size = item.size if item.size is not None else http_size(item.url)
    counts.bytes += size
    if item.target.exists() and item.target.stat().st_size == size:
        counts.skipped += 1
    elif execute:
        with_retries(lambda: fetch(item, size))
        counts.downloaded += 1
    else:
        counts.would_download += 1
        print(f"would fetch {size / BYTES_PER_MEGABYTE:10.1f} MB  {item.url}")
    if execute and item.extract:
        safe_extract(item.target, item.target.parent.parent)


def process(items: list[Item], errors_path: Path, *, execute: bool) -> Counts:
    counts = Counts(total=len(items))
    for item in items:
        try:
            handle_item(item, counts, execute=execute)
        except TRANSFER_ERRORS as error:
            counts.errors += 1
            report_error(errors_path, Failure("download" if execute else "size check", item, error))
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", choices=sorted(d.value for d in Dataset))
    parser.add_argument("--execute", action="store_true", help="download; without it nothing is written")
    parser.add_argument("--limit", type=int, default=None, help="first N subjects or sessions only")
    arguments = parser.parse_args(argv)
    DESTINATION.mkdir(exist_ok=True)
    started = time.time()
    counts = process(CATALOGUES[Dataset(arguments.dataset)](arguments.limit), DESTINATION / ERRORS_FILE, execute=arguments.execute)
    mode = "execute" if arguments.execute else "dry run"
    summary = json.dumps(counts.__dict__)
    print(f"{arguments.dataset} ({mode}): {summary}; {counts.bytes / BYTES_PER_GIGABYTE:.2f} GB in total; {time.time() - started:.0f} s")
    return FAILED if counts.errors else SUCCEEDED


if __name__ == "__main__":
    sys.exit(main())
