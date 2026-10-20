# Zenodo deposit, v1.0.0: checklist

Nothing here is done automatically. The authors make the deposit; the repository stays private, so the code goes up
as an archive file, not through the GitHub integration.

## Gate (in order)

1. Gabriel reads the English and Portuguese PDFs in full.
2. Callina approves the content and the author list.
3. Final commit; `git status` clean.

## Files to upload

| File | How it is made |
|---|---|
| `white_paper_anesthesia_consensus.pdf` | `tools/pdf/build.mjs` (already built with every commit) |
| `white_paper_anesthesia_consensus.pt-BR.pdf` | same |
| `dpc-v1.0.0-source.zip` | from the repository root, after the final commit: `git archive --format=zip --prefix=dpc-v1.0.0/ -o ../dpc-v1.0.0-source.zip HEAD` (a read-only Git command; it packs only committed, tracked files, so `drafts/`, `.venv/` and `node_modules/` are left out) |

Before uploading the archive, unzip it into an empty folder and run, from `simulator/`:
`python3.13 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt && ../.venv/bin/python -m unittest discover -s tests -t .`
The tests must pass from the archive alone. Checked on 20 October 2026 with the commit of that day: 188 tests ran and passed; 3 skip until the connectome datasets are downloaded, by design, since the datasets are fetched on first use and checked against pinned SHA-256 hashes rather than redistributed (`NOTICE.md`).

## Zenodo form

| Field | Value |
|---|---|
| Resource type | Publication / Preprint |
| Title | The Distributed Perceptual Consensus Hypothesis of General Anaesthesia |
| Creators | Santos de Oliveira, Gabriel (Independent researcher, Rio de Janeiro, Brazil; ORCID 0009-0003-9528-9731); Gertrudes Ferreira, Callina (Universidade Veiga de Almeida, Rio de Janeiro, Brazil; ORCID 0009-0002-8512-213X) |
| Description | The paper's abstract |
| Version | 1.0.0 |
| Language | English (a Brazilian Portuguese translation is included) |
| Licence | CC BY 4.0 for the record (text and figures); the code inside the archive is under Apache 2.0, as `LICENSE` states |
| Keywords | as in `CITATION.cff` |
| Related identifiers | "Is supplemented by": the source archive (same record) |
| DOI | reserve it in the form before publishing, then write it into the paper's "Data and code availability" line and into `CITATION.cff`, rebuild the PDFs, commit, and rebuild the archive |

## After the DOI is reserved

- Paper (EN, PT): replace "DOI to be added on deposit" with the DOI.
- `CITATION.cff`: set `date-released` to the deposit date and add the DOI.
- Paper (EN, PT): set the **Date** row of the title block to the deposit date (it says 17 October 2026, the start of the work).
- Rebuild the PDFs and the archive from the new commit, then upload.

## Checked on 20 October 2026

- References: 250 in each paper, identical lists; every DOI resolves on Crossref and matches author, year, title and
  journal, except six records whose Crossref metadata is incomplete (conference digitisation dates, a proceedings item,
  an online-first date, a DOI registered in 2022 for a 1959 paper), each checked against the publisher or PubMed; the
  four entries without a DOI (ISO 11898-1:2024, Fowler 2014, Overton 1901, the 2004 blackout report) checked by hand
  (`tools/audit/reference_check.py`, report in `tools/audit/reference_check_report.md`).
- Citations: every citation in the text has a reference and every reference is cited.
- Numbers: every number in the main text is supported by a printed report value or is a derived value checked against
  the JSON (`tools/audit/number_trace.py`).
- Literature numbers: all 96 numbers in sentences that cite literature were checked against the cited sources (full text
  where open, otherwise the abstract); corrected: median, not mean, latency in van Blooijs et al. (2024), 180 years since
  1846, the bispectral-index scale no longer attributed to Lubke et al. (1999).
- Summary claims (abstract, Sections 1.2, 5.6, 6, 7.4, 8, 10, 11, Appendix C.11) rechecked against every report after
  K1c, on a copy with three planted errors, all found; the real discrepancies found were corrected.
- Keywords: 8; AI statement names each tool, version and use; licences stated in the title block, `LICENSE` files and
  `NOTICE.md`.

## For the Frontiers version (after Zenodo; not needed for the deposit)

From the journal's pages, checked on 17 October 2026: Hypothesis and Theory articles have at most 12,000 words
(excluding abstract, headings, captions, tables and references; the main text is now about 25,400), appendices of at
most one page each (code listings and full reports go to supplementary material), Harvard author-year citations with
"and" in the text, reference lists naming the first six authors before "et al." (this paper names three), and a
generative-AI statement with each tool's name, version and source. The plan of 19 October: a separate English file of
about 11,000 words, with objections and limitations merged into a Discussion.
