### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T22:46:02.236999+00:00 |
| Finished (UTC) | 2026-10-17T23:05:10.188891+00:00 |
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

### Pre-specified tests (runs in which the test passes)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| W1 | Hub activity rises ≥10% before collapse, no compensation | 0/10 | 0/10 | 0/10 | not run | not run | not run | not run | not run | not run |
| W4 | The rise is larger at high sensory load (and reaches 10%) | 0/10 | 0/10 | 1/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| W2 | Hub activity rises ≥10% before collapse, slow compensation | not run | not run | not run | 0/10 | 0/10 | 1/10 | not run | not run | not run |
| W3 | Hub activity rises ≥10% before collapse, fast compensation | not run | not run | not run | not run | not run | not run | 0/10 | 0/10 | 0/10 |

### Post hoc analyses (not part of the verdict)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| X1 | Post hoc: synchrony surges to ≥1.5 times awake before collapse | 3/10 | 9/10 | 0/10 | 7/10 | 8/10 | 0/10 | 5/10 | 9/10 | 1/10 |
| X2 | Post hoc: the synchrony surge is larger at high sensory load | 6/10 | 6/10 | 7/10 | 3/10 | 6/10 | 3/10 | 4/10 | 3/10 | 6/10 |

### Graceful degradation, P8 (pre-specified; reported separately from the verdict)

| ID | Statement | none, C=0.5 | none, C=1 | none, C=2 | slow, C=0.5 | slow, C=1 | slow, C=2 | fast, C=0.5 | fast, C=1 | fast, C=2 |
|---|---|---|---|---|---|---|---|---|---|---|
| G1 | Batching: burstiness rises to ≥1.5 times awake at or beyond the synchrony surge | 0/10 | 7/10 | 1/10 | 2/10 | 8/10 | 1/10 | 3/10 | 8/10 | 1/10 |
| G2 | Backoff: bursts are further apart at the deepest step that has them than at the surge | 0/2 | n/a | 4/7 | 2/2 | n/a | 5/6 | 2/2 | n/a | 1/4 |

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
