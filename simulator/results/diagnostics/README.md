# Diagnostics

Post hoc analyses that explain a result. They are not tests, carry no verdict and are not listed in the results catalogue.

| Report | Question | Answer |
|---|---|---|
| `k1_ablation_20261019T134610Z` | Why did the worm's K1 result (ketamine on sensory pathways) move from 2/20 in the overnight run to 12/20 in the rerun? | Each of the five code changes between the runs was undone on its own, on 20 seeds. Controls reproduce both runs exactly (largest difference 0.0). Undoing the whole-cycle measurement window raised the median broadcast at the deepest dose from 47% to 79% of awake, and keeping the muscles in the graph raised it to 65%; the other three changes moved it by 11 points or less (36-43%). No single change restores the overnight 109%; all five together do. Pairwise combinations were not run. |
| `phase_inertia_scan_20261020T115453Z` | Does the phase model show neural inertia at settings its calibration did not try (arousal level 0; feedback 0.6 to 0.75 in steps of 0.025)? | No. *C. elegans*, GABAergic-like agent, 10 seeds per setting: mean loss/recovery ratios 0.92 to 1.01, hysteresis wider than one concentration step in 0 to 2 of 10 seeds per setting, and every run recovered. |
| `reference_leak_20261020T115851Z` | Under ketamine-like faults on the sensory pathways (K1), does the stimulus reach the rest of the network through the shared reference? | No. The control reproduces the species report exactly (largest difference 0.0). Without the reference, the median broadcast at the deepest dose is 39% of awake on *C. elegans* and 60% on the human connectome (47% and 55% with it); with a reference formed by the non-sensory populations only, 52% and 61%. What carries the remaining broadcast was not established. |

Scripts: `simulator/diagnostics/`.
