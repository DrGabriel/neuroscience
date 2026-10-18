### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T23:05:10.745646+00:00 |
| Finished (UTC) | 2026-10-17T23:24:18.358816+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `f9d4ba1152281dc5d583dfc1ca6f56acbff3a54e` (working tree dirty: True) |
| SHA-256 `calibration.py` | `f2004f8beadb94de151a8d176cce884e3cd927678d2e855024b01a11932662db` |
| SHA-256 `congestion_study.py` | `3b68ed40c6a76c041e43611b20879e99ea6a296c527de3ce634a18920e410007` |
| SHA-256 `connectomes.py` | `28a0fc40a77bfeca508a0a1abc288a89ffbbc9d74a02e6771fc0e893b87d5e9e` |
| SHA-256 `dpc_simulator.py` | `a0967c8fd20968eb7dfd2b1c3a739c2302f484e6f7aec801f600320e5d17ea64` |
| SHA-256 `excitatory_inhibitory.py` | `9dd9c862a90dd444e51e660ee716e42b363428ecf4aac2ba583d0effaed843bc` |
| SHA-256 `phase_dynamics.py` | `b12417d2578f071d33e00cfad9b586435c621aaae9d3210a29f32a987497b529` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `c65f99684bc737a223916dbf97f6e891874b78e0e7561914851f3aeecef37593` |

### Confirmatory tests (runs in which the test passes)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| X1 | synchrony surges to ≥1.5 times awake before collapse | 4/10 | 7/10 | 2/10 | 5/10 | 9/10 | 3/10 | 2/10 | 8/10 | 1/10 |
| X2 | the synchrony surge is larger at high sensory load | 5/10 | 8/10 | 5/10 | 6/10 | 7/10 | 2/10 | 4/10 | 6/10 | 4/10 |

### Activity tests (secondary in this mode)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | Hub activity rises ≥10% before collapse, no compensation | 0/10 | 0/10 | 1/10 | not run | not run | not run | not run | not run | not run |
| W4 | The rise is larger at high sensory load (and reaches 10%) | 0/10 | 1/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| W2 | Hub activity rises ≥10% before collapse, slow compensation | not run | not run | not run | 0/10 | 0/10 | 0/10 | not run | not run | not run |
| W3 | Hub activity rises ≥10% before collapse, fast compensation | not run | not run | not run | not run | not run | not run | 0/10 | 0/10 | 0/10 |

### Graceful degradation, P8 (pre-specified; reported separately from the verdict)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | Batching: burstiness rises to ≥1.5 times awake at or beyond the synchrony surge | 1/10 | 6/10 | 4/10 | 3/10 | 7/10 | 7/10 | 1/10 | 5/10 | 4/10 |
| G2 | Backoff: bursts are further apart at the deepest step that has them than at the surge | 2/2 | 2/2 | 4/6 | n/a | 0/1 | 1/1 | 2/2 | 1/1 | 1/2 |

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
