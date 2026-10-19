# Diagnostics

Post hoc analyses that explain a result. They are not tests, carry no verdict and are not listed in the results catalogue.

| Report | Question | Answer |
|---|---|---|
| `k1_ablation_20261019T134610Z` | Why did the worm's K1 result (ketamine on sensory pathways) move from 2/20 in the overnight run to 12/20 in the rerun? | Each of the five code changes between the runs was undone on its own, on 20 seeds. Controls reproduce both runs exactly (largest difference 0.0). Undoing the whole-cycle measurement window raised the median broadcast at the deepest dose from 47% to 79% of awake, and keeping the muscles in the graph raised it to 65%; the other three changes moved it by 11 points or less (36-43%). No single change restores the overnight 109%; all five together do. Pairwise combinations were not run. |

Script: `simulator/diagnostics/k1_ablation.py`.
