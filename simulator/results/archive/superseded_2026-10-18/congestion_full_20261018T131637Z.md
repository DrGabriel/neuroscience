### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-18T13:16:37.658784+00:00 |
| Finished (UTC) | 2026-10-18T13:35:39.067784+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `5c7512c46abc11bc56b1dfc5fe78c529892aab97` (working tree dirty: True) |
| SHA-256 `calibration.py` | `93ceca8c940b181fe6b9818b3dd4a328e29014f910bf2c28da362ead6532dd59` |
| SHA-256 `congestion_study.py` | `2a5ce75670eaa049838768925d1df2e9bf4591e7e7938731373f7f1d16c3f73a` |
| SHA-256 `connectomes.py` | `8f007604165a6b4ed5bfcbb11bccfcfc2cedfd8875fc5d1aab33101343fa0f02` |
| SHA-256 `dpc_simulator.py` | `9080470f6134967e13b6f6bee7b295c1f04cbac75f545a5bbd89d7e5aca8da25` |
| SHA-256 `excitatory_inhibitory.py` | `9dd9c862a90dd444e51e660ee716e42b363428ecf4aac2ba583d0effaed843bc` |
| SHA-256 `phase_dynamics.py` | `ded050bac6545f6a63d67347508fc922ffc152b4a58bb353cb37ea4e315b9d98` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |

### Pre-specified tests (runs in which the test passes)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | Hub activity rises ≥10% before collapse, no compensation | test | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | not run | not run | not run | not run | not run | not run |
| W4 | The rise is larger at high sensory load (and reaches 10%) | test | 0/10 (0–28%) | 0/10 (0–28%) | 1/10 (2–40%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) |
| W2 | Hub activity rises ≥10% before collapse, slow compensation | test | not run | not run | not run | 0/10 (0–28%) | 0/10 (0–28%) | 1/10 (2–40%) | not run | not run | not run |
| W3 | Hub activity rises ≥10% before collapse, fast compensation | test | not run | not run | not run | not run | not run | not run | 0/10 (0–28%) | 0/10 (0–28%) | 0/10 (0–28%) |

### Post hoc analyses (not part of the verdict)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | Post hoc: synchrony surges to ≥1.5 times awake before collapse | test | 3/10 (11–60%) | 9/10 (60–98%) | 0/10 (0–28%) | 7/10 (40–89%) | 8/10 (49–94%) | 0/10 (0–28%) | 5/10 (24–76%) | 9/10 (60–98%) | 1/10 (2–40%) |
| X2 | Post hoc: the synchrony surge is larger at high sensory load | test | 6/10 (31–83%) | 6/10 (31–83%) | 7/10 (40–89%) | 3/10 (11–60%) | 6/10 (31–83%) | 3/10 (11–60%) | 4/10 (17–69%) | 3/10 (11–60%) | 6/10 (31–83%) |

### Graceful degradation, P8 (pre-specified; reported separately from the verdict)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 | Batching: burstiness rises to ≥1.5 times awake at or beyond the synchrony surge | test | 0/10 (0–28%) | 7/10 (40–89%) | 1/10 (2–40%) | 2/10 (6–51%) | 8/10 (49–94%) | 1/10 (2–40%) | 3/10 (11–60%) | 8/10 (49–94%) | 1/10 (2–40%) |
| G2 | Backoff: bursts are further apart at the deepest step that has them than at the surge | test | 0/2 (0–66%) | n/a | 4/7 (25–84%) | 2/2 (34–100%) | n/a | 5/6 (44–97%) | 2/2 (34–100%) | n/a | 1/4 (5–70%) |

### Measurements (mean ± SD across seeds)

| Condition | Peak hub activity / awake, low load | Same, high load | Synchrony surge, low load | Same, high load | Collapse concentration |
|---|---|---|---|---|---|
| none, C=0.5 | 1.009 ± 0.016 | 1.011 ± 0.014 | 1.497 ± 0.597 | 1.552 ± 0.517 | 0.988 ± 0.279 |
| none, C=1 | 1.013 ± 0.019 | 1.009 ± 0.012 | 2.899 ± 0.941 | 3.046 ± 1.827 | 1.087 ± 0.119 |
| none, C=2 | 1.025 ± 0.029 | 1.024 ± 0.039 | 1.204 ± 0.181 | 1.396 ± 0.396 | 0.975 ± 0.079 |
| slow, C=0.5 | 1.011 ± 0.013 | 1.015 ± 0.019 | 1.802 ± 0.705 | 1.511 ± 0.519 | 1.025 ± 0.219 |
| slow, C=1 | 1.023 ± 0.024 | 1.023 ± 0.031 | 2.861 ± 1.111 | 3.032 ± 1.329 | 1.075 ± 0.158 |
| slow, C=2 | 1.029 ± 0.040 | 1.021 ± 0.029 | 1.115 ± 0.164 | 1.340 ± 0.663 | 0.875 ± 0.276 |
| fast, C=0.5 | 1.000 ± 0.000 | 1.000 ± 0.002 | 1.892 ± 1.002 | 1.764 ± 1.085 | 0.950 ± 0.237 |
| fast, C=1 | 1.000 ± 0.000 | 1.000 ± 0.000 | 3.729 ± 1.176 | 2.777 ± 1.356 | 1.062 ± 0.198 |
| fast, C=2 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.188 ± 0.511 | 1.259 ± 0.347 | 0.887 ± 0.181 |
