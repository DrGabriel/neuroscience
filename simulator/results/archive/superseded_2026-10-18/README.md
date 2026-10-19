# Superseded reports (18 October 2026)

These reports were made on 18 October 2026 and are superseded by the reports in `simulator/results/`. They are
kept unchanged so that every step of the simulations can be checked. Do not cite these numbers as results of the model.

- Made before the switch of the reference inertia ratio from 1.11 (Iwakiri et al., 2005) to 1.08 (Friedman
  et al., 2010, isoflurane) and the other changes of that day, then rerun from one commit (`0677161`) overnight:
  `calibration_feedback_full_20261018T123315Z`, `calibration_phase_feedback_full_20261018T124535Z`,
  `congestion_full_20261018T131637Z`, `congestion_confirmatory_20261018T133541Z`, `glia_full_20261018T124435Z`,
  `percolation_full_20261018T124443Z`, `sensitivity_full_20261018T124731Z`, `species_full_20261018T135451Z`,
  `validation_full_20261018T123515Z`.
- `calibration_feedback_full_20261018T205648Z`: a single calibration run from commit `4bf724b` that added the
  halothane ratio of 2.85 and found that the model cannot reproduce it. The overnight rerun repeated the
  calibration from `0677161` with the same result.
- `species_full_20261018T223010Z`: the cross-species study of the overnight rerun, with 2 *Drosophila* seeds.
  It was repeated with 6 *Drosophila* seeds (`species_full_20261019T025707Z`). Every *C. elegans*, human and
  plant run, and both of the first two *Drosophila* seeds in every condition, are identical in the two reports.
