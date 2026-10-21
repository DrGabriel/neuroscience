"""Every fixed value of the pair-rule study's design that is not taken unchanged from Appendix C.12."""

from __future__ import annotations

from readout_study.settings import AGENT_ORGANISMS, AGENT_SEEDS

# Seeds: base seed plus 6000. Earlier studies used offsets 0 to 19 (species, sensitivity, convergence, calibrations,
# diagnostics), 1000 (congestion confirmatory), 2000, 3000 and 4000 (pre-specified studies), and Appendix C.12 used
# 5000 (tests, up to 20 seeds), 5500 (calibrations, 10) and 5600 (coupling calibration, 4), so no seed of this study
# has been run before.
SEED_OFFSET = 6000

# C. elegans, the human connectome and Drosophila, in C.12's run order, with C.12's seeds: 20, 20 and 6.
ORGANISMS = AGENT_ORGANISMS
SEEDS = {organism: AGENT_SEEDS[organism] for organism in ORGANISMS}
