"""Trace every number in the paper's main text to a source.

A number in a sentence that cites no literature must be supported by a number printed in a current report, diagnostic
or generated appendix, written with the same or more decimals (a printed 0.4712 supports 0.47 and 47%; a printed 0.47
does not support 0.4712). Numbers in sentences that cite literature are listed
separately: they are checked against their sources, not against the simulations. Section, appendix, figure, table,
prediction and limitation references, test and postulate labels and years are skipped.

A match only shows that the value occurs somewhere in the results; whether it is the right value for the sentence is
the claim check that follows. A number with no match at all is either an error, a derived value, or a design value
stated in the text, and each one is reviewed by hand.

Usage: python3 tools/audit/number_trace.py [paper.md]   (default: the English paper)
Writes tools/audit/number_trace_report.md and exits non-zero if any simulation number is unmatched.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "simulator" / "results"
REPORT_PATH = Path(__file__).with_name("number_trace_report.md")
MAIN_TEXT_START, MAIN_TEXT_END = "## Abstract", "## Appendix A"
GENERATED_APPENDICES_START = "## Appendix B"

CITATION = re.compile(r"\b(?:et al\.|[A-Z][A-Za-z'\-]+(?: and [A-Z][A-Za-z'\-]+)?),? \(?\d{4}[a-z]?\b")
CROSS_REFERENCE = re.compile(r"\b(?:Sections?|Appendix|Appendices|Figures?|Tables?|predictions?|limitations?|items?|Steps?|Eqs?\.?)\s+[\dA-Z][\d.]*(?:(?:,|\s+and|\s+to)\s+[\dA-Z][\d.]*)*")
LABEL = re.compile(r"\b(?:P\d+b?|T\d+[a-c]?|[A-Z]{1,2}\d+[a-c]?)\b")
HEADING_OR_LIST_ITEM = re.compile(r"^\s*(?:#+\s*[\d.]+|\d+\.)(?:\s|$)")
YEAR = re.compile(r"\b(19|20)\d{2}[a-z]?\b")
NUMBER = re.compile(r"(?<![\w.])[−-]?\d+(?:[.,]\d+)?%?")
CODE = re.compile(r"`[^`]*`|\$[^$]*\$|https?://\S+")


@dataclass(frozen=True)
class Finding:
    line: int
    number: str
    kind: str
    sentence: str


def printed_numbers(paper: str) -> list[str]:
    """Numbers as printed in the current Markdown reports and diagnostics and in the generated Appendices B to D.

    Raw JSON values are not used: they include whole curves, against which almost any number matches by chance.
    """
    texts = [path.read_text() for path in [*RESULTS.glob("*.md"), *(RESULTS / "diagnostics").glob("*.md")]]
    texts.append(paper[paper.index(GENERATED_APPENDICES_START):])
    return [token.replace("−", "-").replace(",", "") for text in texts for token in NUMBER.findall(text)]


def decimals_of(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def rounds_to(value: float, token: str) -> bool:
    places = Decimal(1).scaleb(-decimals_of(token))
    target = Decimal(token)
    exact = Decimal(repr(value))
    return any(exact.quantize(places, rounding=mode) == target for mode in (ROUND_HALF_UP, ROUND_HALF_EVEN))


def supports(printed: str, token: str) -> bool:
    """A printed number supports a number in the text written with the same or fewer decimals that it rounds to."""
    printed_value, wanted = printed.rstrip("%"), token.rstrip("%")
    if decimals_of(printed_value) < decimals_of(wanted):
        return False
    return rounds_to(float(printed_value), wanted) or (
        token.endswith("%") and not printed.endswith("%") and rounds_to(100 * float(printed_value), wanted)
    )


def matches(token: str, printed: list[str]) -> bool:
    wanted = token.replace("−", "-").replace(",", "")
    return any(supports(candidate, wanted) for candidate in printed)


def sentences(text: str) -> list[tuple[int, str]]:
    """(line number, sentence or table row) for the main text."""
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        parts = [line] if line.lstrip().startswith("|") else re.split(r"(?<=[.;])\s+(?=[A-Z*(])", line)
        out.extend((number, part) for part in parts if part.strip())
    return out


def numbers_in(sentence: str) -> list[str]:
    cleaned = LABEL.sub(" ", CROSS_REFERENCE.sub(" ", YEAR.sub(" ", CODE.sub(" ", HEADING_OR_LIST_ITEM.sub(" ", sentence)))))
    return [n for n in NUMBER.findall(cleaned) if n not in {"0", "1"}]


def trace(paper: str) -> list[Finding]:
    start = paper.index(MAIN_TEXT_START)
    main = paper[start: paper.index(MAIN_TEXT_END)]
    offset = paper[:start].count("\n")
    printed = printed_numbers(paper)
    findings = []
    for line, sentence in sentences(main):
        kind = "literature" if CITATION.search(sentence) else "simulation"
        for token in numbers_in(sentence):
            if kind == "literature" or not matches(token, printed):
                findings.append(Finding(line + offset, token, kind if kind == "literature" else "unmatched", sentence.strip()))
    return findings


def to_markdown(findings: list[Finding]) -> str:
    unmatched = [f for f in findings if f.kind == "unmatched"]
    literature = [f for f in findings if f.kind == "literature"]
    lines = ["# Number trace", "", f"Unmatched numbers in sentences without a citation: {len(unmatched)}.",
             f"Numbers in sentences that cite literature (checked against their sources): {len(literature)}.", "",
             "## Unmatched", "", "| Line | Number | Sentence |", "|---|---|---|"]
    lines += [f"| {f.line} | {f.number} | {f.sentence[:300].replace('|', '/')} |" for f in unmatched]
    lines += ["", "## In sentences that cite literature", "", "| Line | Number | Sentence |", "|---|---|---|"]
    lines += [f"| {f.line} | {f.number} | {f.sentence[:300].replace('|', '/')} |" for f in literature]
    return "\n".join(lines) + "\n"


def main(arguments: list[str]) -> int:
    paper_path = Path(arguments[0]) if arguments else ROOT / "white_paper_anesthesia_consensus.md"
    findings = trace(paper_path.read_text())
    REPORT_PATH.write_text(to_markdown(findings))
    unmatched = sum(f.kind == "unmatched" for f in findings)
    print(f"unmatched simulation numbers: {unmatched}; literature numbers: {len(findings) - unmatched}; report: {REPORT_PATH}")
    return 1 if unmatched else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
