# Zenodo deposit, v1.0.0: checklist

The release goes to Zenodo through its GitHub integration: the repository is made public, Zenodo watches it, and each
GitHub release is archived with its own DOI. `.zenodo.json` sets the record's metadata (preprint, CC BY 4.0, both
authors with ORCIDs, abstract, keywords). The authors make every step below; nothing is done automatically.

## Gate (in order)

1. Gabriel reads the English and Portuguese PDFs in full.
2. Callina approves the content and the author list of this version.
3. Set the **Date** row of both papers and `date-released` in `CITATION.cff` to the release date; rebuild both PDFs
   (`tools/pdf/build.mjs`); commit and push; `git status` clean.

## Release

1. On GitHub, make `DrGabriel/neuroscience` public (Settings, General, Danger Zone, Change visibility). Its full
   history, including the pre-specification commits and GitHub's push records, becomes public. The author
   photographs are in the repository and its history; `NOTICE.md` keeps them outside the CC BY licence.
2. On Zenodo, log in with GitHub, open GitHub in the account menu, and switch the repository on.
3. On GitHub, create a release with tag `v1.0.0` from `main`, title "v1.0.0". Zenodo archives the release's source
   archive, which leaves the photographs out (`.gitattributes`), and mints the DOI.
4. Check the Zenodo record: type Preprint, licence CC BY 4.0, both authors, abstract. Edit it there if needed.

## After the DOI exists (optional, v1.0.1)

Write the DOI into both papers' "Data and code availability" line and into `CITATION.cff`, rebuild the PDFs, commit,
and create release `v1.0.1`; Zenodo gives it its own DOI under the same concept DOI.

## Before the release: test from the archive

From an empty folder: `git archive --format=zip --prefix=dpc-v1.0.0/ -o dpc-v1.0.0-source.zip HEAD`, unzip, then in
`dpc-v1.0.0/`: `python3.13 -m venv .venv && .venv/bin/pip install -r simulator/requirements.txt`, and run
`(cd simulator && ../.venv/bin/python -m unittest discover -s tests -t .)`,
`.venv/bin/python -I analysis/open_data/run_tests.py` and `node --test explainer/tests/explainer.test.js`. Checked on
22 October 2026 at commit `102b40a`: 356 simulator tests (3 skipped until the connectome datasets are downloaded),
101 open-data tests and 48 explainer tests passed from the archive alone.

## Checked on 20 October 2026

- References: 254 in each paper, identical lists; every DOI resolves on Crossref and matches author, year, title and
  journal, except six records whose Crossref metadata is incomplete (conference digitisation dates, a proceedings item,
  an online-first date, a DOI registered in 2022 for a 1959 paper), each checked against the publisher or PubMed; the
  four entries without a DOI (ISO 11898-1:2024, Fowler 2014, Overton 1901, the 2004 blackout report) checked by hand
  (`tools/audit/reference_check.py`, report in `tools/audit/reference_check_report.md`).
- Citations: every citation in the text has a reference and every reference is cited.
- Prior work added on 20 October 2026 after a prior-art search per contribution: Bardon et al. (2025), Kordas (2026)
  and Tong et al. (2026), checked against the full text on PubMed Central; Waters et al. (2026), a bioRxiv preprint,
  checked against the abstract only (the full text was not reachable), and cited only for what the abstract states.
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
