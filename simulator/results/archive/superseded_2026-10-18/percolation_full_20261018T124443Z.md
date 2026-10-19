### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-18T12:44:43.128980+00:00 |
| Finished (UTC) | 2026-10-18T12:45:34.508459+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `5c7512c46abc11bc56b1dfc5fe78c529892aab97` (working tree dirty: True) |
| SHA-256 `calibration.py` | `93ceca8c940b181fe6b9818b3dd4a328e29014f910bf2c28da362ead6532dd59` |
| SHA-256 `connectomes.py` | `8f007604165a6b4ed5bfcbb11bccfcfc2cedfd8875fc5d1aab33101343fa0f02` |
| SHA-256 `dpc_simulator.py` | `9080470f6134967e13b6f6bee7b295c1f04cbac75f545a5bbd89d7e5aca8da25` |
| SHA-256 `percolation_thresholds.py` | `2b652685905ee4214f3cb1f93e46f8c008980d6750d6dcfe3a5bbefc512e2c46` |
| SHA-256 `phase_dynamics.py` | `ded050bac6545f6a63d67347508fc922ffc152b4a58bb353cb37ea4e315b9d98` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |

### Percolation and quorum thresholds (connectomes treated as undirected)

| Organism | Nodes | Connections | Mean degree | Onset π_c (formula) | Quorum π_q, q* = 0.5 (formula) | Quorum π_q (measured) | Critical failure p_q (formula / measured) | Critical jitter σ_q, ms (formula / measured) |
|---|---|---|---|---|---|---|---|---|
| C. elegans | 448 | 4,741 | 21.2 | 0.0331 | 0.0610 | 0.0643 ± 0.0041 | 0.841 / 0.832 | 19.6 / 18.6 |
| Drosophila | 138,639 | 2,511,789 | 36.2 | 0.0053 | 0.0415 | 0.0438 ± 0.0002 | 0.892 / 0.886 | 28.8 / 27.3 |
| Human | 998 | 17,865 | 35.8 | 0.0239 | 0.0368 | 0.0381 ± 0.0022 | 0.904 / 0.901 | 32.5 / 31.4 |

### Quorum threshold on the directed wiring (largest strongly connected component)

| Organism | Quorum π_q, undirected | Quorum π_q, directed (strong component) | Critical failure p_q | Critical jitter σ_q, ms |
|---|---|---|---|---|
| C. elegans | 0.0643 | 0.1173 ± 0.0072 | 0.694 | 10.2 |
| Drosophila | 0.0438 | 0.1503 ± 0.0006 | 0.608 | 7.9 |
| Human | 0.0381 | 0.0495 ± 0.0015 | 0.871 | 24.2 |
