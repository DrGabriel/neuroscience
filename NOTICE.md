# Third-party software, data and attributions

This file lists every third-party item that this repository uses or redistributes, with its licence and the attribution it requires. An item is included only if its licence permits the use described here.

## Software

| Item | Use in this repository | Licence | Redistributed here? |
|---|---|---|---|
| Python and its standard library | Runs the simulator and validation study | [Python Software Foundation License](https://docs.python.org/3/license.html) | No |
| Mermaid | Renders the diagrams written in Mermaid syntax, on GitHub or locally | [MIT](https://github.com/mermaid-js/mermaid/blob/develop/LICENSE) | No |
| NumPy 2.5.4 | Numerical arrays for the cross-species study | BSD-3-Clause (with bundled MIT, Zlib, 0BSD and CC0 components) | No |
| SciPy 1.18.1 | Sparse eigenvectors and k-means for spectral modules | BSD-3-Clause | No |
| Matplotlib 3.11.2 | Figures | Matplotlib License (PSF-based, BSD-compatible) | No |
| PyArrow 26.0.0 | Reads the FlyWire connection table | Apache-2.0 | No |

Transitive dependencies installed with these packages (contourpy, cycler, fonttools, kiwisolver, packaging, pillow, pyparsing, python-dateutil, six) are under BSD, MIT, MIT-CMU or Apache-2.0 licences. None is redistributed.

## Data

No third-party data are redistributed in this repository. The cross-species study downloads each dataset into `data/raw/` (excluded from version control) and checks it against a pinned SHA-256 digest.

| Dataset | Use | Licence | Required attribution |
|---|---|---|---|
| *C. elegans* hermaphrodite connectome, OpenWorm c302 edge list (`herm_full_edgelist.csv`) | Nematode network | MIT (OpenWorm) | OpenWorm c302; the underlying connectome: Cook, S. J., et al. (2019). *Nature*, 571, 63–71 |
| FlyWire v783 proofread connections, Zenodo record 10676866 | Adult *Drosophila* network | CC BY 4.0 | Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634, 124–138 |
| The Virtual Brain 998-region connectivity (`connectivity_998.zip`) | Human network | GPL-3.0; used, not redistributed | Hagmann, P., et al. (2008). *PLoS Biology*, 6(7), e159; Sanz Leon, P., et al. (2013). *Frontiers in Neuroinformatics*, 7, 10 |

The official licence text of each source accompanies the source itself; none is reproduced here because no data are redistributed.

## Algorithms and published findings

Algorithms, mathematical results and scientific findings are not subject to copyright. Each one used here is nonetheless credited to its originators in the references of the paper, including the Newman–Ziff percolation algorithm, union-find (Tarjan), the Erdős–Rényi and Barabási–Albert random-graph models, the Hill equation and the perturbational complexity index (Casali et al.).

## Trademarks

Product and company names mentioned in this repository, including those of aircraft manufacturers, standards bodies and the providers of AI tools, are trademarks or registered trademarks of their respective owners. They are used only to identify the systems and sources discussed, and their use implies no endorsement.

## Quotation policy

The paper paraphrases published work and cites it. It contains no verbatim text, figures or tables reproduced from other publications. All figures and diagrams in this repository were created for it.
