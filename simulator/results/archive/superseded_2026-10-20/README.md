# Superseded by the corrected runs of 19-20 October 2026

These reports were produced by code that the hostile review and the second code audit of 19 October 2026 corrected (Appendix D): timing errors summed instead of combined in quadrature, a measurement window that did not cover whole stimulus cycles, the *C. elegans* graph including muscles and counting gap junctions twice, the null model breaking degrees, transmitter predictions read as GABA when missing, a single noisy window counted as a congestion collapse, and comparisons of grid values decided by floating-point rounding. They are kept, unedited, so that every earlier figure can be traced.

| Report | Superseded by | Why |
|---|---|---|
| `validation_full_20261018T210913Z` | `validation_full_20261019T113035Z` | Rerun after the code fixes |
| `calibration_phase_feedback_full_20261018T211914Z` | `calibration_phase_feedback_full_20261019T114211Z` | Rerun after the phase-model fixes |
| `sensitivity_full_20261018T212118Z` | `sensitivity_full_20261019T114501Z` | Rerun after the phase-model fixes |
| `species_full_20261019T025707Z` | `species_full_20261020T103719Z` | Run on the uncorrected phase model and worm graph |
| `species_full_20261019T123532Z` | `species_full_20261020T103719Z` | The same runs, unchanged; the successor recomputes their verdicts with the corrected grid comparisons (T1 and F3) |
| `preregistered_full_20261018T174910Z` | `prespecified_full_20261019T202442Z` | Rerun after the fixes; the study was renamed from "pre-registered" to "pre-specified" |
| `convergence_full_20261019T011301Z` | `convergence_full_20261019T225958Z` | Rerun after the phase-model fixes |
| `percolation_full_20261018T211816Z` | `percolation_full_20261020T011339Z` | Worm graph now neurons only (300); per-seed thresholds now stored |
| `glia_full_20261018T211808Z` | `glia_full_20261020T011431Z` | Rerun after the width-tolerance fix |
| `congestion_full_20261018T215236Z` | `congestion_full_20261020T011438Z` | Collapse must now be sustained |
| `congestion_confirmatory_20261018T221119Z` | `congestion_confirmatory_20261020T013236Z` | Collapse must now be sustained |
