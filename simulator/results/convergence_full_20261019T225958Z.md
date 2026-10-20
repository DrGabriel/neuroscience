### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-19T22:59:58.084085+00:00 |
| Finished (UTC) | 2026-10-20T01:13:27.351832+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `f71c3697cd844b603ce53bbf7dcf405b5e5f8d92` (working tree dirty: False) |
| SHA-256 `calibration.py` | `f0760a3875a9007af2640417c43eb9c99b6a2898e63ac5ce1a5b6c915a502f8d` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `convergence_study.py` | `cacef9c2f486a92f1160e76587408321d67f7ae713c51f5fb96f075b02f6ca8a` |
| SHA-256 `dpc_simulator.py` | `07f3b3f1828859c628f596f543d65e33c45403483d5696bd355d8f48fd856fdf` |
| SHA-256 `phase_dynamics.py` | `7470f3f061d933b64e51bb060752914bbcfa166b3653d1dc89beeb4fc032241a` |
| SHA-256 `plant_tissue.py` | `1b04ef76f1fa0860e6a7daca5ea54dab72234bd9e11855efa616f248ad91c935` |
| SHA-256 `provenance.py` | `f320d7cc34706f1a0a92ea109c270872557e999139b9832304eef1fc5032b122` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |
| SHA-256 `species_study.py` | `614fcb5caba1cbd4534dbd00467c79b68f1c9d1def17877508922315609b11fd` |

### Phase model on the Human connectome: reference settings against longer and finer integration

| Quantity (mean ± SD across seeds) | reference | twice the simulated time | half the time step |
|---|---|---|---|
| c_off | 1.540 ± 0.055 | 1.550 ± 0.035 | 1.560 ± 0.022 |
| Broadcast ratio, awake | 0.341 ± 0.199 | 0.237 ± 0.102 | 0.334 ± 0.220 |
| Broadcast ratio, first unconscious | 0.077 ± 0.029 | 0.031 ± 0.010 | 0.045 ± 0.019 |
| Hysteresis (c_off - c_on) | -0.010 ± 0.042 | 0.000 ± 0.000 | 0.000 ± 0.000 |

### Phase model on the Drosophila connectome: reference settings against longer and finer integration

| Quantity (mean ± SD across seeds) | reference | twice the simulated time | half the time step |
|---|---|---|---|
| c_off | 1.400 ± 0.000 | 1.400 ± 0.000 | 1.400 ± 0.000 |
| Broadcast ratio, awake | 0.062 ± 0.001 | 0.146 ± 0.003 | 0.062 ± 0.002 |
| Broadcast ratio, first unconscious | 0.051 ± 0.000 | 0.053 ± 0.013 | 0.048 ± 0.000 |
| Hysteresis (c_off - c_on) | 0.000 ± 0.000 | 0.000 ± 0.000 | 0.000 ± 0.000 |
