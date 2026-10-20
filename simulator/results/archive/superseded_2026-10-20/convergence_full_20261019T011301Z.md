### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-19T01:13:01.996261+00:00 |
| Finished (UTC) | 2026-10-19T02:56:17.977028+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `6d8b0370bbc02702955f7037e6bd8002a6b57754` (working tree dirty: False) |
| SHA-256 `calibration.py` | `7ea6348cdb8c88f692e6f61bec42de8d733a2d52b2d1cabfa09facd7323b1c6c` |
| SHA-256 `connectomes.py` | `b6c0dfb53639d036ca42b1f9710afa944d5c29bb620ec7e584185ab363e35127` |
| SHA-256 `convergence_study.py` | `b667648748e61d97043cc376238f7e5ff1b5bcd3afcfd78ef004979931c28d44` |
| SHA-256 `dpc_simulator.py` | `07f3b3f1828859c628f596f543d65e33c45403483d5696bd355d8f48fd856fdf` |
| SHA-256 `phase_dynamics.py` | `6cb05f21585c509cc34549e486ef8c1c8fc137091c042b2d704720fecc745f54` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |
| SHA-256 `species_study.py` | `f68310bd49f5e36700c57cca19b82a7e097186d38481ae0843edfc75f2503f8e` |

### Phase model on the Human connectome: reference settings against longer and finer integration

| Quantity (mean ± SD across seeds) | reference | twice the simulated time | half the time step |
|---|---|---|---|
| c_off | 1.470 ± 0.027 | 1.480 ± 0.045 | 1.480 ± 0.045 |
| Broadcast ratio, awake | 0.592 ± 0.057 | 0.331 ± 0.104 | 0.600 ± 0.045 |
| Broadcast ratio, first unconscious | 0.130 ± 0.019 | 0.041 ± 0.010 | 0.127 ± 0.029 |

### Phase model on the Drosophila connectome: reference settings against longer and finer integration

| Quantity (mean ± SD across seeds) | reference | twice the simulated time | half the time step |
|---|---|---|---|
| c_off | 1.300 ± 0.000 | 1.300 ± 0.000 | 1.300 ± 0.000 |
| Broadcast ratio, awake | 0.194 ± 0.002 | 0.184 ± 0.001 | 0.191 ± 0.002 |
| Broadcast ratio, first unconscious | 0.101 ± 0.040 | 0.052 ± 0.027 | 0.105 ± 0.048 |
