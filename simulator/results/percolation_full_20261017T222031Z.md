### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T22:20:31.392482+00:00 |
| Finished (UTC) | 2026-10-17T22:21:21.370900+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `f9d4ba1152281dc5d583dfc1ca6f56acbff3a54e` (working tree dirty: True) |
| SHA-256 `calibration.py` | `f2004f8beadb94de151a8d176cce884e3cd927678d2e855024b01a11932662db` |
| SHA-256 `connectomes.py` | `28a0fc40a77bfeca508a0a1abc288a89ffbbc9d74a02e6771fc0e893b87d5e9e` |
| SHA-256 `dpc_simulator.py` | `a0967c8fd20968eb7dfd2b1c3a739c2302f484e6f7aec801f600320e5d17ea64` |
| SHA-256 `percolation_thresholds.py` | `dbd4ea3d3e68158d908cdaf7ad6b718961c3ff50d46d88847a72032428a81fb8` |
| SHA-256 `phase_dynamics.py` | `b12417d2578f071d33e00cfad9b586435c621aaae9d3210a29f32a987497b529` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `c65f99684bc737a223916dbf97f6e891874b78e0e7561914851f3aeecef37593` |

### Percolation and quorum thresholds (connectomes treated as undirected)

| Organism | Nodes | Connections | Mean degree | Onset π_c (formula) | Quorum π_q, q* = 0.5 (formula) | Quorum π_q (measured) | Critical failure p_q (formula / measured) | Critical jitter σ_q, ms (formula / measured) |
|---|---|---|---|---|---|---|---|---|
| C. elegans | 448 | 4,741 | 21.2 | 0.0331 | 0.0610 | 0.0643 ± 0.0041 | 0.930 / 0.926 | 19.6 / 18.6 |
| Drosophila | 138,639 | 2,511,789 | 36.2 | 0.0053 | 0.0415 | 0.0438 ± 0.0002 | 0.952 / 0.949 | 28.8 / 27.3 |
| Human | 998 | 17,865 | 35.8 | 0.0239 | 0.0368 | 0.0381 ± 0.0022 | 0.958 / 0.956 | 32.5 / 31.4 |
