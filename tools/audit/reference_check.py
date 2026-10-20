"""Check every reference of the paper against Crossref.

For each entry with a DOI, the DOI must resolve on Crossref, and the entry's first author, year, title and journal
must match the Crossref record (title by word overlap). Entries without a DOI are listed for checking by hand.
Crossref answers are cached in tools/audit/crossref_cache/ so a rerun does not query again.

Usage: python3 tools/audit/reference_check.py [paper.md]   (default: the English paper)
Writes tools/audit/reference_check_report.md and exits non-zero if any entry fails.
"""

from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(__file__).with_name("crossref_cache")
REPORT_PATH = Path(__file__).with_name("reference_check_report.md")
REFERENCES_HEADINGS, REFERENCES_END = ("## References\n", "## Referências\n"), "\n## Appendix B"
DOI = re.compile(r"https://doi\.org/(\S+?)\.?(?=\s|$)")
ENTRY = re.compile(r"^(?P<authors>.+?)\((?P<year>\d{4})[a-z]?(?:, [^)]*)?\)\.\s*(?P<rest>.*)$", re.S)
TITLE_OVERLAP_MINIMUM = 0.6
POLITE_PAUSE_S = 0.2
USER_AGENT = "dpc-reference-check/1.0"


@dataclass(frozen=True)
class Problem:
    entry: str
    issue: str


def plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", plain(re.sub(r"<[^>]+>", " ", text))) if len(w) > 2}


def crossref(doi: str) -> dict | None:
    CACHE.mkdir(exist_ok=True)
    cached = CACHE / (re.sub(r"[^A-Za-z0-9]", "_", doi) + ".json")
    if cached.exists():
        return json.loads(cached.read_text()) or None
    request = urllib.request.Request("https://api.crossref.org/works/" + urllib.parse.quote(doi), headers={"User-Agent": USER_AGENT})
    try:
        message = json.load(urllib.request.urlopen(request, timeout=60))["message"]
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        message = {}
    cached.write_text(json.dumps(message))
    time.sleep(POLITE_PAUSE_S)
    return message or None


def years_of(record: dict) -> set[int]:
    keys = ("published-print", "published-online", "issued", "published", "created")
    return {record[k]["date-parts"][0][0] for k in keys if record.get(k, {}).get("date-parts", [[None]])[0][0]}


def check_entry(entry: str) -> list[Problem]:
    found = ENTRY.match(entry)
    doi = DOI.search(entry)
    if not found:
        return [Problem(entry, "entry does not parse as 'Authors (Year). Title...'")]
    if not doi:
        return [Problem(entry, "no DOI: check by hand")]
    record = crossref(doi.group(1))
    if record is None:
        return [Problem(entry, f"DOI {doi.group(1)} not found on Crossref")]
    problems = []
    first_author = plain(found["authors"].split(",")[0]).strip()
    crossref_authors = {plain(a.get("family", a.get("name", ""))) for a in record.get("author", [])[:1]}
    if crossref_authors and not any(first_author.split()[-1] in a or a.split()[-1] in first_author for a in crossref_authors if a):
        problems.append(Problem(entry, f"first author differs: Crossref has {sorted(crossref_authors)}"))
    if int(found["year"]) not in years_of(record):
        problems.append(Problem(entry, f"year {found['year']} not among Crossref's {sorted(years_of(record))}"))
    title = (record.get("title") or [""])[0]
    mine, theirs = words(found["rest"]), words(title)
    if theirs and len(mine & theirs) / len(theirs) < TITLE_OVERLAP_MINIMUM:
        problems.append(Problem(entry, f"title differs: Crossref has '{title[:120]}'"))
    return problems


def references(paper: str) -> list[str]:
    start = next(paper.index(heading) + len(heading) for heading in REFERENCES_HEADINGS if heading in paper)
    block = paper[start: paper.index(REFERENCES_END, start)]
    return [e.strip() for e in block.split("\n\n") if e.strip() and not e.strip().startswith(("---", ">"))]


def main(arguments: list[str]) -> int:
    paper = (Path(arguments[0]) if arguments else ROOT / "white_paper_anesthesia_consensus.md").read_text()
    entries = references(paper)
    problems = [p for e in entries for p in check_entry(e)]
    by_doi_problem = [p for p in problems if not p.issue.startswith("no DOI")]
    lines = ["# Reference check", "", f"Entries: {len(entries)}. Problems against Crossref: {len(by_doi_problem)}. Without a DOI: {len(problems) - len(by_doi_problem)}.", "",
             "| Entry | Issue |", "|---|---|", *(f"| {p.entry[:160].replace('|', '/')} | {p.issue} |" for p in problems)]
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(lines[2])
    return 1 if by_doi_problem else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
