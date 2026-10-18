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


# Fixed before preregistered_study.py was first run; the wording must not change after it.
PRESPECIFIED_TESTS = """The tests below, their conditions and their pass rule were written into this paper before the study that evaluates them was run (`simulator/preregistered_study.py`). Before that, the code was checked with one shortened run (one *C. elegans* seed, with a quarter of the integration time); it is not part of the results. The study uses seeds that no earlier run used (from the base seed plus 2000): 20 for *C. elegans*, 6 for *Drosophila* and 20 for the human connectome. A test passes for an organism when it holds in at least 80% of that organism's seeds.

**Feedback connections.** A connection is classed as feedback when its target lies fewer steps from the sensory populations than its source, counting steps along directed connections from the nearest sensory population (breadth-first search). Connections from populations that no sensory population reaches are not classed. By this rule 21% of *C. elegans* connections and 27% of *Drosophila* connections are feedback. The human connectome is not used for K2: diffusion imaging gives no direction, so every connection appears in both directions and the classification would be arbitrary.

**K2 (ketamine's timing faults on feedback connections).** The NMDA-antagonist-like agent adds its timing error only on feedback connections; baseline timing error and transmission failure act as before, and the sensory stimulus of P3 is applied.

- K2a: quorum is lost within the concentration range.
- K2b: at the first concentration without quorum, the stimulus still spreads: the broadcast ratio is at least half its awake value. Seeds in which quorum is never lost count as failing.
- K2c (control, paired by seed): with the same added timing error on an equal number of connections drawn at random, quorum is lost at a higher concentration than with feedback faults, or not at all, while feedback faults abolish it.

What we expect, stated before the run: the phase model has no rule that agreement requires closed loops, and forward and lateral connections alone can keep populations in step. Test K1 showed that timing error confined to a minority of connections left quorum intact. K2 may therefore fail in this model. A failure would show that the model cannot decide where ketamine acts; it would not refute the proposal, which then rests on prediction 7 (Section 7) and on directional connectivity measured in patients (U. Lee et al., 2013). A pass would show that, in these two wiring diagrams, feedback connections are where timing faults break agreement.

**P1c (replication of P1b).** P1b, found post hoc in Appendix D.3, states that under the GABAergic-like agent the susceptibility at the last conscious concentration is at least ten times its awake value. P1c applies exactly this criterion to the fresh seeds on all three connectomes. A rise of fluctuations near a threshold is expected of threshold models in general, so P1c tests whether the model behaviour repeats, not whether DPC is right."""


RUN_NOTES = """A first launch of the study was stopped after its *C. elegans* runs, before any of its results were read, so that agent names and comments in the simulator could be brought into line with the paper's terms (omission and timing faults; giant component). No equation or parameter changed. The study was then run again from the start on the same seeds; the report below is from that run."""


def preregistered_results() -> str:
    try:
        return f"Source: `simulator/results/{report_name('preregistered')}`.\n\n{latest_report('preregistered')}"
    except FileNotFoundError:
        return "Results: not yet run."


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

### D.4 Numerical convergence of the phase model

The human-connectome conditions are repeated with twice the simulated time and with half the integration step. Source: `simulator/results/{report_name("convergence")}`.

{latest_report("convergence")}

### D.5 Congestion and graceful degradation (exploratory run)

Source: `simulator/results/{report_name("congestion")}`.

{latest_report("congestion")}

### D.6 Synchrony surge (confirmatory run on fresh seeds)

Source: `simulator/results/{report_name("congestion", "confirmatory")}`.

{latest_report("congestion", "confirmatory")}

### D.7 Pre-specified tests on fresh seeds: K2 and P1c

{PRESPECIFIED_TESTS}

{RUN_NOTES}

{preregistered_results()}

### D.8 Figures

![Figure 1. Coherent fraction during induction and emergence in the percolation model, without and with calibrated reference feedback.](figures/figure_1_percolation_hysteresis.png)

![Figure 2. Loss and recovery concentrations against network size (mean ± SD across seeds).](figures/figure_2_finite_size.png)

![Figure 3. Global coherence relative to the awake value during induction and emergence on three connectomes (mean ± SD across seeds).](figures/figure_3_species_coherence.png)

![Figure 4. Propagation of a sensory stimulus beyond the stimulated populations during induction (mean ± SD across seeds).](figures/figure_4_broadcast.png)

![Figure 5. Open-junction fraction at which action-potential propagation fails in plant tissue, against junction conductance.](figures/figure_5_plant_tissue.png)

![Figure 6. Hub activity and global synchrony during induction in the Wilson-Cowan model of the human connectome.](figures/figure_6_congestion.png)

### D.9 Reproducing every result

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
../.venv/bin/python convergence_study.py
../.venv/bin/python preregistered_study.py
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
