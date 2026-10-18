### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T21:35:46.505041+00:00 |
| Finished (UTC) | 2026-10-17T21:37:42.193723+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; standard library only |
| Git commit | `b6a4fca845093eaf193fb5bc966f44c4660d2aa2` (working tree dirty: True) |
| SHA-256 `calibrate_feedback.py` | `6d2ca5d374b35c8fa39ba76719b874b1efc00ffa552cce2e8f04b286441c7b23` |
| SHA-256 `dpc_simulator.py` | `a0967c8fd20968eb7dfd2b1c3a739c2302f484e6f7aec801f600320e5d17ea64` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `c65f99684bc737a223916dbf97f6e891874b78e0e7561914851f3aeecef37593` |

### Feedback λ calibrated to published inertia ratios (N = 10,000, 10 seeds)

| Arousal level | Target ratio | λ (ms) | Model ratio | Reproduced | Source |
|---|---|---|---|---|---|
| 0 | 1.07 | 3.80 | 1.069 | yes | Warnaby et al. (2017), propofol, humans |
| 0 | 1.08 | 4.00 | 1.079 | yes | Friedman et al. (2010), isoflurane, mice |
| 0 | 1.11 | 4.50 | 1.109 | yes | Iwakiri et al. (2005), propofol, humans (reference target) |
| 0 | 1.63 | 7.65 | 1.629 | yes | Sepúlveda et al. (2018), propofol, humans |
| 0.3 | 1.07 | 4.67 | 1.070 | yes | Warnaby et al. (2017), propofol, humans |
| 0.3 | 1.08 | 4.95 | 1.079 | yes | Friedman et al. (2010), isoflurane, mice |
| 0.3 | 1.11 | 5.77 | 1.110 | yes | Iwakiri et al. (2005), propofol, humans (reference target) |
| 0.3 | 1.63 | 10.67 | 1.628 | yes | Sepúlveda et al. (2018), propofol, humans |
| 0.5 | 1.07 | 5.56 | 1.069 | yes | Warnaby et al. (2017), propofol, humans |
| 0.5 | 1.08 | 5.94 | 1.080 | yes | Friedman et al. (2010), isoflurane, mice |
| 0.5 | 1.11 | 6.99 | 1.110 | yes | Iwakiri et al. (2005), propofol, humans (reference target) |
| 0.5 | 1.63 | 14.51 | 1.627 | yes | Sepúlveda et al. (2018), propofol, humans |
| 0.7 | 1.07 | 6.83 | 1.069 | yes | Warnaby et al. (2017), propofol, humans |
| 0.7 | 1.08 | 7.38 | 1.079 | yes | Friedman et al. (2010), isoflurane, mice |
| 0.7 | 1.11 | 8.90 | 1.110 | yes | Iwakiri et al. (2005), propofol, humans (reference target) |
| 0.7 | 1.63 | 22.87 | 1.627 | yes | Sepúlveda et al. (2018), propofol, humans |
