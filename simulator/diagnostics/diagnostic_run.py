"""Shared plumbing for post hoc diagnostics: their reports go to results/diagnostics, apart from the study reports."""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

SIMULATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIMULATOR))

import provenance  # noqa: E402
import reporting  # noqa: E402


def write_report(name: str, started: datetime, body: dict[str, object], to_markdown: Callable[[dict[str, object]], str]) -> Path:
    """Publishes the diagnostic with provenance and returns the Markdown path."""
    document = {
        "label": reporting.RunLabel.DIAGNOSTIC,
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), provenance.NUMERICAL_PACKAGES),
        **body,
    }
    return reporting.publish(name, document, to_markdown(document))[1]
