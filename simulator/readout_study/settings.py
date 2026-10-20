"""Every fixed value of the DPC readout study's design: seeds, organisms, readout settings and test thresholds."""

from __future__ import annotations

import calibration as cal
import connectome_inertia
import disconnection_study
import dpc_readout as readout
import dpc_simulator as dpc
import phase_dynamics as dynamics

# Seeds: base seed plus 5000 for every test, plus 5500 for the inertia scans and calibrations of both models, and
# 5600 for the calibration of the weaker coupling. Earlier studies used offsets 0 to 19 (species, sensitivity,
# convergence, calibrations, diagnostics), 1000 (congestion confirmatory), 2000, 3000 and 4000 (pre-specified
# studies), so no block has been run before, and no calibration seed is used to test what it calibrated.
SEED_OFFSET = 5000
CALIBRATION_SEED_OFFSET = 5500
COUPLING_CALIBRATION_SEED_OFFSET = 5600

# Run order within a block: the two small connectomes first, the fly (about an hour a run) last.
AGENT_ORGANISMS = ("celegans", "human", "drosophila")
DISCONNECTION_ORGANISMS = disconnection_study.ORGANISMS
# The fly is left out of the phase-model inertia scan, as of the null model, for cost.
INERTIA_ORGANISMS = ("celegans", "human")
# Number of populations: C. elegans 300, human 998, Drosophila 138,639 (Appendix C.1).
ORGANISMS_BY_SIZE = ("celegans", "human", "drosophila")
# The human connectome is structurally symmetric (35,730 arcs, twice its 17,865 undirected links: diffusion imaging
# gives no direction), so no directed reading is reported for it.
DIRECTED_ORGANISMS = ("celegans", "drosophila")
AGENT_SEEDS = {organism: spec.full_study_seeds for organism, spec in cal.ORGANISMS.items()}
INERTIA_SCAN_SEEDS = {organism: 10 for organism in INERTIA_ORGANISMS}
VALIDATION_SEEDS = {organism: 20 for organism in INERTIA_ORGANISMS}
COUPLING_CALIBRATION_SEEDS = {organism: 4 for organism in AGENT_ORGANISMS}
PERCOLATION_CALIBRATION_SEEDS = 10
PERCOLATION_HELD_OUT_SEEDS = 20

READOUT = readout.ReadoutSettings(
    integration_window_ms=dpc.REFERENCE_INTEGRATION_WINDOW_MS,
    quorum_fraction=cal.QUORUM_FRACTION,
    cycle_interval=cal.JITTER_CORRELATION_TIME,
)

# T1d: susceptibility at least this multiple of what independent phases at the same mean coherence would show.
# Independent phases give 1 by construction; collective fluctuations should at least double it. Free, fixed in advance.
MATCHED_COHERENCE_EXCESS = 2.0
# Kuramoto's critical coupling for the natural-frequency spread and noise of the reference dynamics.
LOCKING_THRESHOLD = readout.kuramoto_critical_coupling(cal.NATURAL_FREQUENCY_SPREAD, cal.NOISE_INTENSITY)
# The phase model's reference feedback is scanned at these multiples of it.
LOCKING_THRESHOLD_MULTIPLES = (0.0, 0.5, 0.75, 1.0, 1.25, 1.5)
SCANNED_FEEDBACK = tuple(multiple * LOCKING_THRESHOLD for multiple in LOCKING_THRESHOLD_MULTIPLES)
LOWEST_MEASURED_INERTIA_RATIO = connectome_inertia.LOWEST_MEASURED_RATIO
HIGHEST_REPRODUCED_INERTIA_RATIO = connectome_inertia.HIGHEST_REPRODUCED_RATIO
# Weaker coupling (referee point 4): awake global coherence 0.93, 0.88 and 0.96 at K = 4 is close to full synchrony.
# Target, fixed before any run: awake coherence between 0.5 and 0.7, as close as the grid allows to its middle.
METASTABLE_COHERENCE_RANGE = (0.5, 0.7)
METASTABLE_COHERENCE_TARGET = 0.6
COUPLING_GRID = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0)
AWAKE_ONLY_GRID = dpc.ConcentrationGrid(maximum=0.0, step=cal.CONCENTRATION_GRID.step)
WINDOW_CYCLES = disconnection_study.WINDOW_CYCLES

# The --smoke option: a check that the code runs end to end in a few minutes, on C. elegans only, with one seed, the
# shortest integration (two sampled cycles) and two concentrations per condition. Its report is not a result.
SMOKE_ORGANISMS = ("celegans",)
SMOKE_INTEGRATION = dynamics.IntegrationSettings(time_step=cal.FULL_TIME_STEP, relaxation_steps=20, measurement_steps=40)
SMOKE_GRID = dpc.ConcentrationGrid(maximum=cal.CONCENTRATION_GRID.maximum, step=cal.CONCENTRATION_GRID.maximum)
