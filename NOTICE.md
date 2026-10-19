# Third-party software, data and attributions

This file lists every third-party item that this repository uses or redistributes, with its licence and the attribution it requires. An item is included only if its licence permits the use described here.

## Software

| Item | Use in this repository | Licence | Redistributed here? |
|---|---|---|---|
| Python and its standard library | Runs the simulator and validation study | [Python Software Foundation License](https://docs.python.org/3/license.html) | No |
| Mermaid | Renders the diagrams written in Mermaid syntax, on GitHub or locally | [MIT](https://github.com/mermaid-js/mermaid/blob/develop/LICENSE) | No |
| KaTeX 0.16.11 | Typesets the mathematics in the PDFs (`tools/pdf/`); its fonts are embedded in the PDFs | MIT, including the KaTeX fonts (katex-fonts repository) | Embedded in the PDFs only |
| marked 12.0.2 | Converts the Markdown paper to HTML for the PDFs | MIT | No |
| Playwright (playwright-core 1.63.0) | Drives the installed Chrome to print the PDFs | Apache-2.0 | No |
| NumPy 2.5.4 | Numerical arrays for the cross-species study | BSD-3-Clause (with bundled MIT, Zlib, 0BSD and CC0 components) | No |
| SciPy 1.18.1 | Sparse eigenvectors and k-means for spectral modules | BSD-3-Clause | No |
| Matplotlib 3.11.2 | Figures | Matplotlib License (PSF-based, BSD-compatible) | No |
| PyArrow 26.0.0 | Reads the FlyWire connection table | Apache-2.0 | No |
| Source Serif 4, Barlow Condensed and IBM Plex Mono typefaces | Text of the interactive explainer, served from this repository (`explainer/assets/fonts/`) so that no visitor data go to a third party; Source Serif 4 and IBM Plex Mono are also embedded in the PDFs of the paper by `tools/pdf/build.mjs` | SIL Open Font License 1.1; licence texts in `explainer/assets/fonts/licences/`. Source Serif 4 and Barlow Condensed are Google Fonts' Latin subsets, unmodified; IBM Plex Mono is IBM's own unmodified WOFF2 file, since "Plex" is a Reserved Font Name | Yes, unmodified |
| Okabe–Ito colour palette | Colour-blind-safe colours of the explainer (Wong, B. (2011). Points of view: Color blindness. *Nature Methods*, 8, 441. https://doi.org/10.1038/nmeth.1618) | Colour values; credited, no licence applies | Not applicable |

Transitive dependencies installed with these packages (contourpy, cycler, fonttools, kiwisolver, packaging, pillow, pyparsing, python-dateutil, six) are under BSD, MIT, MIT-CMU or Apache-2.0 licences. None is redistributed.

## Data

Three third-party datasets are redistributed, in derived form, in the interactive explainer (`explainer/data/explainer-data.js`): the *C. elegans* connections, under the OpenWorm MIT licence, whose copyright and permission notice is reproduced at the top of that file; the 219-region human consensus connectome of Shafiei, Markello et al. (2019), under CC BY 4.0; and a neuropil-level summary of the FlyWire adult fly connectome (FlyWire Consortium, 2024), under CC BY 4.0. For both CC BY datasets the attribution, licence link and a statement of the changes made are at the top of that file. No other third-party data are redistributed. The explainer's results archive (`explainer/data/results/`) holds copies of this project's own study reports, which cite the datasets they used but contain none of them. The cross-species study downloads each dataset into `data/raw/` (excluded from version control) and checks it against a pinned SHA-256 digest.

| Dataset | Use | Licence | Required attribution |
|---|---|---|---|
| *C. elegans* hermaphrodite connectome, OpenWorm c302 edge list (`herm_full_edgelist.csv`) | Nematode network | MIT (OpenWorm); redistributed as undirected connections in `explainer/data/` | OpenWorm c302; the underlying connectome: Cook, S. J., et al. (2019). *Nature*, 571, 63–71 |
| FlyWire v783 proofread connections, Zenodo record 10676866 | Adult *Drosophila* network; a neuropil-level summary in the explainer | CC BY 4.0; neuropil summary redistributed in `explainer/data/` with changes stated. Dataset: FlyWire Consortium (2024), https://doi.org/10.5281/zenodo.10676866 | Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634, 124–138. Synapses: Buhmann, J., et al. (2021), *Nature Methods*, 18, 771–774, and Heinrich, L., et al. (2018), MICCAI 2018, LNCS 11071, 317–325. Transmitter predictions: Eckstein, N., et al. (2024), *Cell*, 187, 2574–2594 |
| Consensus structural and functional connectome from 70 young healthy adults, Zenodo record 3067849 (`Consensus_Connectomes.mat`) | Human brain in 3D in the explainer only; not used by the paper's studies | CC BY 4.0; 219-region scale redistributed in `explainer/data/` with changes stated | Shafiei, G., Markello, R. D., Talpalaru, T., Makowski, C., Kirschner, M., Devenyi, G. A., et al. (2019). [Data set]. Zenodo. https://doi.org/10.5281/zenodo.3067849; described in Shafiei, G., et al. (2020). *Biological Psychiatry*, 87(8), 727–735. https://doi.org/10.1016/j.biopsych.2019.09.031 |
| The Virtual Brain 998-region connectivity (`connectivity_998.zip`) | Human network | GPL-3.0; used, not redistributed | Hagmann, P., et al. (2008). *PLoS Biology*, 6(7), e159; Sanz Leon, P., et al. (2013). *Frontiers in Neuroinformatics*, 7, 10 |

Data that are only used are downloaded from their source, where their licence text lives. Data redistributed in derived form carry their notices at the top of `explainer/data/explainer-data.js`, as described above.

## Author photographs

The photographs of the authors in `explainer/assets/` are published with the consent of the people shown. They are **not** covered by the CC BY 4.0 licence of this repository: all rights are reserved, and they may not be reused without the subject's permission.

## Algorithms and published findings

Algorithms, mathematical results and scientific findings are not subject to copyright. Each one used here is nonetheless credited to its originators in the references of the paper, including the Newman–Ziff percolation algorithm, union-find (Tarjan), the Erdős–Rényi and Barabási–Albert random-graph models, the Hill equation and the perturbational complexity index (Casali et al.).

## Trademarks

Product and company names mentioned in this repository, including those of aircraft manufacturers, standards bodies and the providers of AI tools, are trademarks or registered trademarks of their respective owners. They are used only to identify the systems and sources discussed, and their use implies no endorsement.

## Quotation policy

The paper paraphrases published work and cites it. It contains no unattributed verbatim text and no figures or tables reproduced from other publications; standard formulations, such as the ICMJE authorship wording and the names of methods, are used as they are. All figures and diagrams in this repository were created for it.
