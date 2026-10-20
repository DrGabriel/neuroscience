### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-20T01:32:36.901705+00:00 |
| Finished (UTC) | 2026-10-20T01:50:32.632551+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `38e86cbaa5c084c7a9d05a0da2bf4d08648ada80` (working tree dirty: False) |
| SHA-256 `calibration.py` | `f0760a3875a9007af2640417c43eb9c99b6a2898e63ac5ce1a5b6c915a502f8d` |
| SHA-256 `congestion_study.py` | `f6d346699defb083b07fbd6bed0cb4339053262712857274028c6d862e74e50a` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `dpc_simulator.py` | `07f3b3f1828859c628f596f543d65e33c45403483d5696bd355d8f48fd856fdf` |
| SHA-256 `excitatory_inhibitory.py` | `8a9b47e6f8a66f76cd22a46262f540d7d1182ac7a969d3ed69a58aa16666c074` |
| SHA-256 `phase_dynamics.py` | `7470f3f061d933b64e51bb060752914bbcfa166b3653d1dc89beeb4fc032241a` |
| SHA-256 `plant_tissue.py` | `1b04ef76f1fa0860e6a7daca5ea54dab72234bd9e11855efa616f248ad91c935` |
| SHA-256 `provenance.py` | `f320d7cc34706f1a0a92ea109c270872557e999139b9832304eef1fc5032b122` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |

### Confirmatory tests (runs in which the test passes)

| ID | Statement | Kind | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | synchrony surges to ≥1.5 times awake before collapse | test | 4/10 (17–69%) | 9/10 (60–98%) | 2/10 (6–51%) | 5/10 (24–76%) | 10/10 (72–100%) | 3/10 (11–60%) | 2/10 (6–51%) | 8/10 (49–94%) | 2/10 (6–51%) |
| X2 | the synchrony surge is larger at high sensory load | test | 5/10 (24–76%) | 8/10 (49–94%) | 5/10 (24–76%) | 7/10 (40–89%) | 7/10 (40–89%) | 2/10 (6–51%) | 5/10 (24–76%) | 7/10 (40–89%) | 4/10 (17–69%) |

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
| G2 | Backoff: bursts are further apart at the deepest step that has them than at the surge | test | 2/2 (34–100%) | n/a | 4/6 (30–90%) | n/a | n/a | 1/1 (21–100%) | 2/2 (34–100%) | n/a | 1/2 (9–91%) |

### Measurements (mean ± SD across seeds)

| Condition | Peak hub activity / awake, low load | Same, high load | Synchrony surge, low load | Same, high load | Collapse concentration |
|---|---|---|---|---|---|
| none, C=0.5 | 1.009 ± 0.016 | 1.020 ± 0.025 | 1.482 ± 0.281 | 1.698 ± 0.738 | 1.125 ± 0.000 |
| none, C=1 | 1.014 ± 0.016 | 1.023 ± 0.040 | 2.571 ± 1.025 | 3.502 ± 0.978 | 1.125 ± 0.000 |
| none, C=2 | 1.043 ± 0.086 | 1.014 ± 0.023 | 1.308 ± 0.424 | 1.215 ± 0.252 | 1.000 ± 0.000 |
| slow, C=0.5 | 1.005 ± 0.006 | 1.019 ± 0.018 | 1.836 ± 0.990 | 1.882 ± 0.734 | 1.113 ± 0.040 |
| slow, C=1 | 1.017 ± 0.029 | 1.008 ± 0.012 | 3.116 ± 0.986 | 3.050 ± 0.892 | 1.125 ± 0.000 |
| slow, C=2 | 1.015 ± 0.021 | 1.014 ± 0.025 | 1.455 ± 0.444 | 1.341 ± 0.569 | 0.975 ± 0.079 |
| fast, C=0.5 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.378 ± 0.300 | 1.565 ± 0.771 | 1.137 ± 0.040 |
| fast, C=1 | 1.000 ± 0.000 | 1.000 ± 0.001 | 2.868 ± 0.958 | 3.498 ± 0.644 | 1.125 ± 0.000 |
| fast, C=2 | 1.000 ± 0.000 | 1.000 ± 0.000 | 1.251 ± 0.299 | 1.224 ± 0.410 | 0.988 ± 0.040 |
