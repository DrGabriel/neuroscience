"""Group verdicts of the exploratory analysis (Appendix E.13, deviation D7), read from a list of result files.

The exploratory inputs are spread over two folders: the committed code's results wherever no deviation applied
(confirmatory/) and the results the deviations produced (exploratory/). The committed group step reads every file of
one folder. This module replaces only that reading, with the files named in a list (one repository-relative path per
line), read in file-name order as one folder would be, and otherwise runs the committed group step with the
deviations of deviations.py, which it leaves unchanged.

Usage, from the repository root:
    .venv/bin/python -I -m analysis.open_data.exploratory_group group --inputs <list> --out <verdicts.json>
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from . import deviations, outputs, run

_committed_load_all = run.load_all


def listed_paths(listing: Path) -> list[Path]:
    return [outputs.REPO / line for line in listing.read_text().split()]


def load_listed(source: Path, prefix: str) -> list[dict]:
    """D7: a folder is read as committed; a list gives its files of this dataset in file-name order."""
    if source.is_dir():
        return _committed_load_all(source, prefix)
    chosen = sorted((p for p in listed_paths(source) if p.name.startswith(f"{prefix}_")), key=lambda p: p.name)
    repeated = [name for name, count in Counter(p.name for p in chosen).items() if count > 1]
    if repeated:
        raise ValueError(f"{source}: the same result file is listed more than once: {repeated}")
    return [json.loads(p.read_text()) for p in chosen]


if __name__ == "__main__":
    deviations.apply_deviations()
    run.load_all = load_listed
    run.main()
