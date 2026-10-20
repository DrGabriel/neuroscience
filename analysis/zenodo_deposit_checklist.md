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
- Rebuild the PDFs and the archive from the new commit, then upload.
