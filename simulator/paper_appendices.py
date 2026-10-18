"""Builds Appendices C and D of the paper from the latest full reports and the model source.

The paper ends with the two appendices. Running this script replaces everything from the
Appendix C heading to the end of the paper, so it can be rerun after every new set of results.
Listings are copied byte for byte; tests/test_dpc_simulator.py checks that they match the source.

Usage: python3 paper_appendices.py
Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

import provenance
import reporting

PAPER = provenance.SIMULATOR_DIRECTORY.parent / "white_paper_anesthesia_consensus.md"
APPENDIX_C_HEADING = "## Appendix C: Computational reference simulator (percolation model)"
SEPARATOR = "\n---\n\n"
REPORT_HEADING_LEVEL = "#### "


def latest_report_path(kind: str, label: str = "full") -> Path:
    paths = sorted(reporting.RESULTS_DIRECTORY.glob(f"{kind}_{label}_*.md"))
    if not paths:
        raise FileNotFoundError(f"No {label} {kind} report in {reporting.RESULTS_DIRECTORY}")
    return paths[-1]


def latest_report(kind: str, label: str = "full") -> str:
    return latest_report_path(kind, label).read_text().replace("### ", REPORT_HEADING_LEVEL).strip()


def report_name(kind: str, label: str = "full") -> str:
    return latest_report_path(kind, label).name


def listing(name: str) -> str:
    source = (provenance.SIMULATOR_DIRECTORY / name).read_text()
    return f"<!-- begin {name} -->\n```python\n{source}```\n<!-- end {name} -->"


def source_hash_rows() -> list[str]:
    rows = [
        [f"`simulator/{path.name}`", f"`{provenance.file_sha256(path)}`"]
        for path in sorted(provenance.SIMULATOR_DIRECTORY.glob("*.py"))
    ]
    return reporting.markdown_table(["File", "SHA-256"], rows)


def parameter_table() -> str:
    """The parameter records stored in the latest cross-species report, so the table matches the run."""
    records = json.loads(latest_report_path("species").with_suffix(".json").read_text())["calibration"]
    rows = [[record["name"], f"`{record['value']}`", record["basis"], record["source"]] for record in records]
    return "\n".join(reporting.markdown_table(["Parameter", "Value", "Basis", "Source"], rows))


def appendix_c() -> str:
    return f"""{APPENDIX_C_HEADING}

### C.1 Purpose

The percolation model implements Section 4 exactly as written. The studies below check that the model has the properties the paper attributes to it and calibrate its one fitted parameter. A simulation cannot show that the brain works this way; it shows that the stated mechanism is internally consistent and produces the claimed behaviour. Every parameter is labelled in the source as measured, calibrated or free.

### C.2 Algorithms and software

| Component | Method | Reference |
|---|---|---|
| Homogeneous network | Erdős-Rényi $G(n, m)$ random graph | Erdős and Rényi (1959) |
| Hub-dominated network | Barabási-Albert preferential attachment | Barabási and Albert (1999) |
| Giant component $F(\\pi)$ | Newman-Ziff algorithm: edges added in random order, giving the giant-component fraction for every $\\pi$ in one pass | Newman and Ziff (2000) |
| Connected components | Union-find with union by size and path compression | Tarjan (1975) |
| Self-consistent state | Fixed-point iteration of $S = F(\\pi(c, S))$ from the previous state, so that induction and emergence follow their own branches | Section 4.3 |
| Dose-response | Hill equation | Hill (1910) |
| Quorum threshold formula | Generating functions of the degree distribution | Callaway et al. (2000) |
| Statistics | Mean, sample standard deviation and normal-approximation 95% confidence half-width across independent seeds | |
| Software | CPython, standard library only | |

### C.3 Calibration of the reference feedback

Source: `simulator/results/{report_name("calibration_feedback")}`.

{latest_report("calibration_feedback")}

### C.4 Validation across network sizes

Network sizes run from 302 nodes, the number of *C. elegans* neurons (White et al., 1986), and 1,000, the finest common cortical parcellation (Schaefer et al., 2018), to 1,000,000. Claims C1-C7 are properties the paper attributes to the model; observations O1-O4 and extension tests E1-E3 are reported without entering the verdict. Each check is labelled either a test, which the model could fail, or a consistency check, which follows from the model's equations and confirms only that the code implements them. Every count of seeds is given with its Wilson 95% confidence interval (Wilson, 1927); a check is said to hold only when it holds in every seed. Source: `simulator/results/{report_name("validation")}`.

{latest_report("validation")}

### C.5 Quorum thresholds of empirical connectomes

Source: `simulator/results/{report_name("percolation")}`.

{latest_report("percolation")}

### C.6 Sensitivity to free parameters

Each free parameter is varied with the others held at their reference values. Source: `simulator/results/{report_name("sensitivity")}`.

{latest_report("sensitivity")}

### C.7 Glial regulation (postulate P9)

The glial extensions of Section 4.6 run on the same networks and seeds. The checks were fixed before the multi-seed run; a single exploratory seed at N = 1,000 was run beforehand to confirm that the code executes, and its results were seen before the checks were written, so the checks are not blind to the direction of the effects. Source: `simulator/results/{report_name("glia")}`.

{latest_report("glia")}

### C.8 Listing: `simulator/dpc_simulator.py`

{listing("dpc_simulator.py")}

### C.9 Listing: `simulator/validation_study.py`

{listing("validation_study.py")}

### C.10 Listing: `simulator/glial_regulation.py`

{listing("glial_regulation.py")}
"""


def appendix_d() -> str:
    return f"""## Appendix D: Cross-species, congestion and plant-tissue studies

### D.1 Methods

The phase-oscillator model (`simulator/phase_dynamics.py`), a Kuramoto-Sakaguchi network (Kuramoto, 1984; Sakaguchi and Kuramoto, 1986) of the kind used for large-scale brain dynamics (Cabral et al., 2011; Breakspear, 2017), is run on three empirical connectomes (`simulator/connectomes.py`): *C. elegans* (OpenWorm c302 edge list of the complete hermaphrodite wiring diagram, derived from Cook et al., 2019; 448 nodes, comprising the 302 neurons and the muscles and other cells they synapse onto), adult *Drosophila* (FlyWire v783, Dorkenwald et al., 2024, with synapses detected by Buhmann et al., 2021, and Heinrich et al., 2018, and transmitters predicted by Eckstein et al., 2024; connections of at least five synapses) and a 998-region human structural connectome (Hagmann et al., 2008; Sanz Leon et al., 2013). Each dataset is checked against a pinned SHA-256 digest before use. All parameters, with their basis, are listed in `simulator/calibration.py`. The congestion test uses Wilson-Cowan excitatory-inhibitory populations (Wilson and Cowan, 1972) with the local parameters and inhibitory plasticity rule of Abeysuriya et al. (2018), after Vogels et al. (2011), on the human connectome; synchrony is measured with the index of Golomb and Rinzel (1993) with measured conduction delays (`simulator/excitatory_inhibitory.py`). Plant tissue is a sheet of FitzHugh-Nagumo cells (FitzHugh, 1961; Nagumo et al., 1962) coupled through junctions (`simulator/plant_tissue.py`); on a square lattice the bond-percolation threshold is exactly 1/2 (Kesten, 1980). Pre-specified tests were fixed before the runs that evaluate them; post hoc analyses are labelled as such and do not enter any verdict. Timing jitter in the phase model persists for a correlation time τ before it changes (an Ornstein-Uhlenbeck process), so that it acts as a timing error during each exchange; jitter redrawn at every integration step would average to a uniform weakening of coupling, indistinguishable from transmission failure. As a null model, the GABAergic-like and sensory-stimulus conditions are repeated on rewired copies of the *C. elegans* and human connectomes in which the targets of connections are shuffled, which keeps every node's number of inputs and outputs (conditions N1 and N2). Every parameter is listed below with its basis: measured, a measured range, calibrated, or free; the sensitivity analysis varies each one that is not measured.

{parameter_table()}

### D.2 Oscillator feedback calibration

The attempt to calibrate the oscillator model's feedback to the measured inertia ratio is reported in full. Source: `simulator/results/{report_name("calibration_phase_feedback")}`.

{latest_report("calibration_phase_feedback")}

### D.3 Cross-species study

Source: `simulator/results/{report_name("species")}`.

{latest_report("species")}

### D.4 Congestion and graceful degradation (exploratory run)

Source: `simulator/results/{report_name("congestion")}`.

{latest_report("congestion")}

### D.5 Synchrony surge (confirmatory run on fresh seeds)

Source: `simulator/results/{report_name("congestion", "confirmatory")}`.

{latest_report("congestion", "confirmatory")}

### D.6 Figures

![Figure 1. Coherent fraction during induction and emergence in the percolation model, without and with calibrated reference feedback.](figures/figure_1_percolation_hysteresis.png)

![Figure 2. Loss and recovery concentrations against network size (mean ± SD across seeds).](figures/figure_2_finite_size.png)

![Figure 3. Global coherence relative to the awake value during induction and emergence on three connectomes (mean ± SD across seeds).](figures/figure_3_species_coherence.png)

![Figure 4. Propagation of a sensory stimulus beyond the stimulated populations during induction (mean ± SD across seeds).](figures/figure_4_broadcast.png)

![Figure 5. Open-junction fraction at which action-potential propagation fails in plant tissue, against junction conductance.](figures/figure_5_plant_tissue.png)

![Figure 6. Hub activity and global synchrony during induction in the Wilson-Cowan model of the human connectome.](figures/figure_6_congestion.png)

### D.7 Reproducing every result

```sh
cd simulator
python3 -m venv ../.venv && ../.venv/bin/pip install -r requirements.txt
../.venv/bin/python -m unittest discover -s tests -t .
python3 calibrate_feedback.py && python3 validation_study.py && python3 glial_study.py
../.venv/bin/python percolation_thresholds.py
../.venv/bin/python calibrate_phase_feedback.py
../.venv/bin/python sensitivity_study.py
../.venv/bin/python congestion_study.py && ../.venv/bin/python congestion_study.py --confirm
../.venv/bin/python species_study.py
../.venv/bin/python figures.py
python3 paper_appendices.py
```

Every report records the machine, operating system, Python and package versions, Git commit and the SHA-256 hash of every simulator module that ran. The source files that produced the results above have these hashes:

{chr(10).join(source_hash_rows())}
"""


def main() -> None:
    paper = PAPER.read_text()
    if APPENDIX_C_HEADING in paper:
        paper = paper[: paper.index(SEPARATOR + APPENDIX_C_HEADING)]
    PAPER.write_text(paper.rstrip("\n") + "\n" + SEPARATOR + appendix_c() + SEPARATOR + appendix_d())
    print(f"Appendices C and D written to {PAPER.name}")


if __name__ == "__main__":
    main()
