### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-18T22:11:19.971565+00:00 |
| Finished (UTC) | 2026-10-18T22:30:09.950308+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `0677161701738895512e2b047b40f3857406a5d5` (working tree dirty: True) |
| SHA-256 `calibration.py` | `7ea6348cdb8c88f692e6f61bec42de8d733a2d52b2d1cabfa09facd7323b1c6c` |
| SHA-256 `congestion_study.py` | `2a5ce75670eaa049838768925d1df2e9bf4591e7e7938731373f7f1d16c3f73a` |
| SHA-256 `connectomes.py` | `b6c0dfb53639d036ca42b1f9710afa944d5c29bb620ec7e584185ab363e35127` |
| SHA-256 `dpc_simulator.py` | `07f3b3f1828859c628f596f543d65e33c45403483d5696bd355d8f48fd856fdf` |
| SHA-256 `excitatory_inhibitory.py` | `9dd9c862a90dd444e51e660ee716e42b363428ecf4aac2ba583d0effaed843bc` |
| SHA-256 `phase_dynamics.py` | `6cb05f21585c509cc34549e486ef8c1c8fc137091c042b2d704720fecc745f54` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |

### Confirmatory tests (runs in which the test passes)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | synchrony surges to ≥1.5 times awake before collapse | test | 4/10 (17–69%) | 7/10 (40–89%) | 2/10 (6–51%) | 5/10 (24–76%) | 9/10 (60–98%) | 3/10 (11–60%) | 2/10 (6–51%) | 8/10 (49–94%) | 1/10 (2–40%) |
| X2 | the synchrony surge is larger at high sensory load | test | 5/10 (24–76%) | 8/10 (49–94%) | 5/10 (24–76%) | 6/10 (31–83%) | 7/10 (40–89%) | 2/10 (6–51%) | 4/10 (17–69%) | 6/10 (31–83%) | 4/10 (17–69%) |

### Activity tests (secondary in this mode)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | Hub activity rises ≥10% before collapse, no compensation | test | 0/10 (0–28%) | 0/10 (0–28%) | 1/10 (2–40%) | not run | not run | not run | not run | not run | not run |
| W4 | The rise is larger at high sensory load (and reaches 10%) | test | 0/10 (0–28%) | 1/10 (2–40%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) |
| W2 | Hub activity rises ≥10% before collapse, slow compensation | test | not run | not run | not run | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | not run | not run | not run |
| W3 | Hub activity rises ≥10% before collapse, fast compensation | test | not run | not run | not run | not run | not run | not run | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) |

### Graceful degradation, P8 (pre-specified; reported separately from the verdict)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 | Batching: burstiness rises to ≥1.5 times awake at or beyond the synchrony surge | test | 1/10 (2–40%) | 6/10 (31–83%) | 4/10 (17–69%) | 3/10 (11–60%) | 7/10 (40–89%) | 7/10 (40–89%) | 1/10 (2–40%) | 5/10 (24–76%) | 4/10 (17–69%) |
| G2 | Backoff: bursts are further apart at the deepest step that has them than at the surge | test | 2/2 (34–100%) | 2/2 (34–100%) | 4/6 (30–90%) | n/a | 0/1 (0–79%) | 1/1 (21–100%) | 2/2 (34–100%) | 1/1 (21–100%) | 1/2 (9–91%) |

### Measurements (mean ± SD across seeds)

| Condition | Peak hub activity / awake, low load | Same, high load | Synchrony surge, low load | Same, high load | Collapse concentration |
|---|---|---|---|---|---|
| none, C=0.5 | 1.009 ± 0.016 | 1.020 ± 0.025 | 1.482 ± 0.281 | 1.629 ± 0.757 | 1.100 ± 0.079 |
| none, C=1 | 1.014 ± 0.016 | 1.023 ± 0.040 | 2.380 ± 1.139 | 3.373 ± 1.207 | 1.000 ± 0.270 |
| none, C=2 | 1.043 ± 0.086 | 1.014 ± 0.023 | 1.308 ± 0.424 | 1.215 ± 0.252 | 0.938 ± 0.135 |
| slow, C=0.5 | 1.005 ± 0.006 | 1.019 ± 0.018 | 1.836 ± 0.990 | 1.808 ± 0.782 | 1.075 ± 0.121 |
| slow, C=1 | 1.017 ± 0.029 | 1.008 ± 0.012 | 2.974 ± 1.180 | 2.902 ± 1.106 | 1.050 ± 0.237 |
| slow, C=2 | 1.015 ± 0.021 | 1.014 ± 0.025 | 1.414 ± 0.467 | 1.341 ± 0.569 | 0.950 ± 0.105 |
| fast, C=0.5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.348 ± 0.327 | 1.482 ± 0.793 | 0.950 ± 0.350 |
| fast, C=1 | 1.000 ± 0.000 | 1.000 ± 0.001 | 2.816 ± 1.052 | 3.307 ± 1.015 | 0.975 ± 0.316 |
| fast, C=2 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.194 ± 0.205 | 1.224 ± 0.410 | 0.800 ± 0.237 |
