# K1 diagnostic: real entrainment against locking to a phantom stimulus

Post hoc diagnostic, no verdict. Script: `simulator/diagnostics/phantom_stimulus.py`. Medians across seeds of the locking value (0: none, 1: complete) of the non-sensory populations (broadcast) and of the sensory populations.

| Check | Result |
|---|---|
| largest difference from the species report, applied stimulus, study window | 0.0 |

| Connectome | Window (multiple of the study's) | Stimulus | Broadcast, awake | Broadcast, deepest dose | Sensory, deepest dose | Seeds |
|---|---|---|---|---|---|---|
| C. elegans | 1× | applied | 0.212 | 0.093 | 0.406 | 20 |
| C. elegans | 1× | phantom (zero strength) | 0.093 | 0.090 | 0.086 | 20 |
| C. elegans | 4× | applied | 0.156 | 0.039 | 0.399 | 20 |
| C. elegans | 4× | phantom (zero strength) | 0.034 | 0.026 | 0.027 | 20 |
| Human | 1× | applied | 0.040 | 0.033 | 0.207 | 20 |
| Human | 1× | phantom (zero strength) | 0.029 | 0.033 | 0.026 | 20 |
