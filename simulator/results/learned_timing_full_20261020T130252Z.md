### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-20T13:02:52.282850+00:00 |
| Finished (UTC) | 2026-10-20T13:49:19.720634+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0, matplotlib 3.11.2 |
| Git commit | `07dc10efe4c7ecd55177b7f3af2c0ad62fece747` (working tree dirty: False) |
| SHA-256 `calibration.py` | `927c086c7d329d4fbeb895412f083b07e776c05d83fd7be0a807076107bfefea` |
| SHA-256 `comparisons.py` | `340b044083ffa2e8f98988da8fb400fa25c961db5f08c4bce42e5681441b92c8` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `dpc_simulator.py` | `621859b0bca3cc34cedd82e1559e1097bf90142d698e8c7d95b3e0907417c452` |
| SHA-256 `learned_timing_study.py` | `466818c79d2cd6498e3f2af7577d69520ab5c02dcb83829871453d4cce04240d` |
| SHA-256 `phase_dynamics.py` | `256d7f68896a7b587732757eab90ba1d931a6eb9873db312f987773cdc0718fc` |
| SHA-256 `plant_tissue.py` | `e9dac3d0f0c2c9baa8e813f65ea71615e65a027edd4d3115e86e556203ece030` |
| SHA-256 `prespecified_runs.py` | `f1109431136f11f2a15c4c840ff674f722c2424ff44dc2f7772b033db7e93dae` |
| SHA-256 `provenance.py` | `4bf9f706eb10c32c3878843146193c79bbafa7ba37e2486d2fbdaa1c2b156350` |
| SHA-256 `reporting.py` | `661056b7bab4548101eb2b1008146146ed2b0977893b0b570a00a38fa0c8b0f2` |
| SHA-256 `species_study.py` | `ecf45bb37fa24ec88570c5846ac80f9b74df736f1c0e3e82e21f508872348c0f` |

### Pre-specified tests of learned arrival times (seeds in which the test holds; passes at 80% or more)

| ID | Statement | C. elegans | Human |
|---|---|---|---|
| L1 | With learned arrival times, fixed timing offsets never abolish quorum | 0/20 (0–16%), fails | 0/20 (0–16%), fails |
| L2 | With learned arrival times, timing jitter of the same size still abolishes quorum, at most one step later | 20/20 (84–100%), passes | 20/20 (84–100%), passes |
| L3 | With learned arrival times, conduction delays no longer lower the loss concentration by more than one step | not run | 0/20 (0–16%), fails |
| L4 | Learning keeps the awake state (at least 90% of its coherence) and moves the GABAergic-like loss by at most one step | 0/20 (0–16%), fails | 0/20 (0–16%), fails |

### Measurements (mean ± SD across seeds; concentrations relative to EC50)

| Quantity | Condition | C. elegans | Human |
|---|---|---|---|
| Loss concentration | NMDA-antagonist-like, fixed timing offsets | 0.600 ± 0.000 | 0.650 ± 0.000 |
| Loss concentration | NMDA-antagonist-like, fixed timing offsets, learned arrival times | 0.092 ± 0.034 | 0.118 ± 0.024 |
| Loss concentration | NMDA-antagonist-like | 0.650 ± 0.000 | 0.698 ± 0.011 |
| Loss concentration | NMDA-antagonist-like, learned arrival times | 0.075 ± 0.026 | 0.123 ± 0.038 |
| Loss concentration | GABAergic-like | 1.400 ± 0.063 | 1.578 ± 0.047 |
| Loss concentration | GABAergic-like, learned arrival times | 0.077 ± 0.026 | 0.123 ± 0.038 |
| Loss concentration | GABAergic-like, conduction delays | not reached (0/0) | 1.205 ± 0.043 |
| Loss concentration | GABAergic-like, conduction delays, learned arrival times | not reached (0/0) | 0.735 ± 0.206 |
