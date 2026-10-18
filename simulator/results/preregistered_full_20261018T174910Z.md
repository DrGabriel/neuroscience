### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-18T17:49:10.413562+00:00 |
| Finished (UTC) | 2026-10-18T20:19:08.484250+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0, matplotlib 3.11.2 |
| Git commit | `7ba034e3e40e82e11e30a6833d3c32e56c0192d1` (working tree dirty: False) |
| SHA-256 `calibration.py` | `93ceca8c940b181fe6b9818b3dd4a328e29014f910bf2c28da362ead6532dd59` |
| SHA-256 `connectomes.py` | `b6c0dfb53639d036ca42b1f9710afa944d5c29bb620ec7e584185ab363e35127` |
| SHA-256 `dpc_simulator.py` | `6d5896a5b0552a26c2896ab1fa6a6a044202134677c2f5581a0b898454d2d18e` |
| SHA-256 `phase_dynamics.py` | `2eeb9971c5c7b7c10e9822d712a17975a8dc0eafe800c66f38a77432db270e50` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `preregistered_study.py` | `c11b96e47fbbf08e8d44eab71862d23b89440275b5b764d8a3d916a4ce07b4ea` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |
| SHA-256 `species_study.py` | `b00dfd9939e84600b73619d60e326190e898f52bb2f9bbc19d157e5732eb80eb` |

### Pre-registered tests (seeds in which the test holds; passes at 80% or more)

| ID | Statement | C. elegans | Drosophila | Human |
|---|---|---|---|---|
| K2a | Timing faults on feedback connections alone abolish quorum | 0/20 (0–16%), fails | 0/6 (0–39%), fails | not run |
| K2b | Where they do, the stimulus still spreads (broadcast at least half its awake value) | 0/20 (0–16%), fails | 0/6 (0–39%), fails | not run |
| P1c | Replication of P1b: fluctuations rise at least tenfold on the conscious side of the threshold | 18/20 (70–97%), passes | 6/6 (61–100%), passes | 20/20 (84–100%), passes |
| K2c | Control: as many random connections need a higher concentration, or never abolish quorum | 0/20 (0–16%), fails | 0/6 (0–39%), fails | not run |

### Feedback connections (share of all connections)

| Organism | Feedback share |
|---|---|
| C. elegans | 21.1% |
| Drosophila | 27.0% |

### Measurements (mean ± SD across seeds; concentrations relative to EC50)

| Quantity | Condition | C. elegans | Drosophila | Human |
|---|---|---|---|---|
| Loss concentration | NMDA-antagonist-like on feedback connections, sensory stimulus | not reached (0/20) | not reached (0/6) | not reached (0/0) |
| Loss concentration | NMDA-antagonist-like on as many random connections, sensory stimulus | not reached (0/20) | not reached (0/6) | not reached (0/0) |
| Broadcast ratio, awake | NMDA-antagonist-like on feedback connections, sensory stimulus | 0.449 ± 0.193 | 0.207 ± 0.007 | not reached (0/0) |
| Broadcast ratio, first unconscious | NMDA-antagonist-like on feedback connections, sensory stimulus | not reached (0/20) | not reached (0/6) | not reached (0/0) |
| Coherence at the highest concentration, relative to awake | NMDA-antagonist-like on feedback connections, sensory stimulus | 0.840 ± 0.049 | 0.896 ± 0.021 | not reached (0/0) |
| Coherence at the highest concentration, relative to awake | NMDA-antagonist-like on as many random connections, sensory stimulus | 0.934 ± 0.012 | 0.928 ± 0.014 | not reached (0/0) |
| Loss concentration | GABAergic-like | 1.363 ± 0.043 | 1.300 ± 0.000 | 1.475 ± 0.034 |
