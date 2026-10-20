# K1 diagnostic: does the stimulus leak through the shared reference?

Post hoc diagnostic, no verdict. Script: `simulator/diagnostics/reference_leak.py`.

| Check | Result |
|---|---|
| largest difference from the species report, reference as in the study | 0.0 |

| Variant | Connectome | Broadcast at deepest dose, median share of awake | Range | Quorum held | K1 holds |
|---|---|---|---|---|---|
| reference as in the study | C. elegans | 47% | 4%–168% | 20/20 | 12/20 |
| reference as in the study | Human | 55% | 14%–306% | 20/20 | 10/20 |
| no reference (feedback 0) | C. elegans | 39% | 14%–93% | 20/20 | 11/20 |
| no reference (feedback 0) | Human | 60% | 20%–255% | 20/20 | 9/20 |
| reference formed by non-sensory populations only | C. elegans | 52% | 5%–260% | 20/20 | 9/20 |
| reference formed by non-sensory populations only | Human | 61% | 19%–396% | 20/20 | 8/20 |
