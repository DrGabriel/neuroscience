"""Labels the paper and the explainer use for tests whose report identifiers reuse the names of postulates P1 to P3.

Those tests do not correspond to the postulates of the same name (test P3 asks whether a stimulated sensory area keeps
processing; postulate P3 is quorum), so readers see them as T1 to T3b instead. The reports keep the identifiers they
were written with, so archived results stay unchanged and traceable.
"""

from __future__ import annotations

import re

REPORT_TO_PUBLIC = {
    "P1": "T1",
    "P1b": "T1b",
    "P1c": "T1c",
    "P2a": "T2a",
    "P2b": "T2b",
    "P3": "T3",
    "P3b": "T3b",
}
_TABLE_ROW_IDENTIFIER = re.compile(r"^\| (" + "|".join(sorted(REPORT_TO_PUBLIC, key=len, reverse=True)) + r") \|", re.MULTILINE)


def public_label(identifier: str) -> str:
    return REPORT_TO_PUBLIC.get(identifier, identifier)


def relabel_table_rows(markdown: str) -> str:
    """A report's Markdown with the identifier cell that opens each table row shown by its public label."""
    return _TABLE_ROW_IDENTIFIER.sub(lambda match: f"| {public_label(match.group(1))} |", markdown)
