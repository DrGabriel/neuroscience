"""Labels the paper and the explainer use for tests whose report identifiers clash with another name.

Two kinds of clash are resolved. The species and pre-specified studies name tests P1 to P3b, the labels of postulates
P1 to P3, although the tests do not correspond to them (test P3 asks whether a stimulated sensory area keeps processing;
postulate P3 is quorum); readers see them as T1 to T3b. The congestion study names its batching and backoff tests G1
and G2, the labels of the glial study's microglia checks; readers see them as B1 and B2. The reports keep the
identifiers they were written with, so archived results stay unchanged and traceable.
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
# Identifiers that clash only in one study, keyed by the study's report kind.
STUDY_REPORT_TO_PUBLIC = {
    "congestion": {"G1": "B1", "G2": "B2"},
}


def labels_for(study: str | None) -> dict[str, str]:
    return REPORT_TO_PUBLIC | STUDY_REPORT_TO_PUBLIC.get(study or "", {})


def public_label(identifier: str, study: str | None = None) -> str:
    return labels_for(study).get(identifier, identifier)


def relabel_table_rows(markdown: str, study: str | None = None) -> str:
    """A report's Markdown with the identifier cell that opens each table row shown by its public label."""
    labels = labels_for(study)
    row_identifier = re.compile(r"^\| (" + "|".join(sorted(map(re.escape, labels), key=len, reverse=True)) + r") \|", re.MULTILINE)
    return row_identifier.sub(lambda match: f"| {labels[match.group(1)]} |", markdown)


def correspondence_rows() -> list[tuple[str, str, str]]:
    """(study, report identifier, label in the paper) for every relabelled test."""
    shared = [("species and pre-specified", identifier, label) for identifier, label in REPORT_TO_PUBLIC.items()]
    specific = [(study, identifier, label) for study, labels in STUDY_REPORT_TO_PUBLIC.items() for identifier, label in labels.items()]
    return shared + specific
