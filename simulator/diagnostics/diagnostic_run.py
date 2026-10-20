"""Shared plumbing for post hoc diagnostics: their reports go to results/diagnostics, apart from the study reports."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

SIMULATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIMULATOR))

import provenance  # noqa: E402

OUTPUT_DIRECTORY = SIMULATOR / "results" / "diagnostics"


def write_report(name: str, started: datetime, body: dict[str, object], to_markdown: Callable[[dict[str, object]], str]) -> Path:
    """Writes NAME_<start time>.json and .md to results/diagnostics and returns the Markdown path."""
    document = {
        "label": "diagnostic",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), ("numpy", "scipy")),
        **body,
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stem = f"{name}_{started.strftime('%Y%m%dT%H%M%SZ')}"
    (OUTPUT_DIRECTORY / f"{stem}.json").write_text(json.dumps(document, indent=2))
    markdown = OUTPUT_DIRECTORY / f"{stem}.md"
    markdown.write_text(to_markdown(document))
    print(to_markdown(document))
    return markdown
