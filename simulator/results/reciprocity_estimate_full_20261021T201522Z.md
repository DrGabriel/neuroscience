### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-21T20:15:22.882696+00:00 |
| Finished (UTC) | 2026-10-21T20:15:25.736361+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `74f9cb009f6e5096b0fcea8f23b798a9d941eb60` (working tree dirty: False) |
| SHA-256 `calibration.py` | `da8a964155ad650d0c5cbdf570f95a5334a8fc3e8eacbcc83d59d9e5c60c5b3a` |
| SHA-256 `comparisons.py` | `340b044083ffa2e8f98988da8fb400fa25c961db5f08c4bce42e5681441b92c8` |
| SHA-256 `connection_pairs.py` | `892ddab333a17948f1eeb131fb5e69a3748f7567a099caf81ff315a83b802445` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `dpc_readout.py` | `9102690116ddfc5ec6a9e1f37cb2534b4b8ad0f4eb07ca15a12faea289b23b99` |
| SHA-256 `dpc_simulator.py` | `621859b0bca3cc34cedd82e1559e1097bf90142d698e8c7d95b3e0907417c452` |
| SHA-256 `pair_rule_diagnostic.py` | `78b42fee595729174412bb9731cbbad14b0d6be4291bd9b0d5fa3f953604d85a` |
| SHA-256 `percolation_thresholds.py` | `6ba5d6ef1f4ed376063c30ec0e0f541fe08259a6c50a5b279b14ae82ca5125d2` |
| SHA-256 `phase_dynamics.py` | `faf6fb06cb484f473d6409a513daf43bd0ab3737d446efa3f0f5b7286ea9b78d` |
| SHA-256 `plant_tissue.py` | `e9dac3d0f0c2c9baa8e813f65ea71615e65a027edd4d3115e86e556203ece030` |
| SHA-256 `provenance.py` | `c2d147f298a0ecc43e72d2704a3fda67913847cbbc03e7525394df1677c27e6f` |
| SHA-256 `reciprocity_estimate.py` | `46d188f2b3fc275ef5df5bd162b03eda3a67d34a10f75464ef9421e504bed1b0` |
| SHA-256 `reporting.py` | `6e6a07609b80574406c4893bc9b2ea8eecd6ea6c7f13b08ecbdc147e2b55ea88` |
| SHA-256 `round3_study/__init__.py` | `00aa9455701c44e6c2eda71b8a0e2164ecc5d1705e124a9d5a8519f4fe2082fc` |
| SHA-256 `round3_study/crossings.py` | `aadc2b42cbf76703d69a317b0a3665c3f6b9c00b96462bc6f5beccbcd3094597` |
| SHA-256 `round3_study/reciprocity.py` | `c8dc58ba58d4f0c8f9d952b567a6b850d93bb5f606e67f0a0846e0693bd6a577` |
| SHA-256 `round3_study/seeds.py` | `cfac3da892116212648efabe600036c8be21d5ad5de3805e88fd43ddbba3929f` |

Post hoc static estimates requested by referees, reported without a verdict. No oscillator dynamics; either-direction rule
(Appendix C.12); NMDA-antagonist-like agent at three times the EC50; 10 assignments of direction of
20 timing draws per value; seeds [20268317, 20268318]. Arc on time with probability
0.0242 at the reference maximal timing error of 40 ms.

### Mean giant component against the reciprocal share r

| reciprocal share r | Mean giant-component share |
|---|---|
| 1 | 0.654 |
| 0.95 | 0.642 |
| 0.9 | 0.618 |
| 0.85 | 0.606 |
| 0.8 | 0.587 |
| 0.75 | 0.563 |
| 0.7 | 0.542 |
| 0.65 | 0.518 |
| 0.6 | 0.490 |
| 0.55 | 0.462 |
| 0.5 | 0.423 |
| 0.45 | 0.396 |
| 0.4 | 0.356 |
| 0.35 | 0.324 |
| 0.3 | 0.267 |
| 0.25 | 0.240 |
| 0.2 | 0.200 |
| 0.15 | 0.170 |
| 0.1 | 0.133 |
| 0.05 | 0.108 |
| 0 | 0.085 |

First falls below q* = 0.5 at reciprocal share r = 0.618 (linear interpolation).

### Mean giant component against the maximal added timing error (ms)

| maximal added timing error (ms) | Mean giant-component share |
|---|---|
| 20 | 0.903 |
| 25 | 0.854 |
| 30 | 0.795 |
| 35 | 0.728 |
| 40 | 0.656 |
| 45 | 0.573 |
| 50 | 0.492 |
| 55 | 0.393 |
| 60 | 0.306 |
| 65 | 0.218 |
| 70 | 0.146 |
| 75 | 0.117 |
| 80 | 0.084 |

First falls below q* = 0.5 at maximal added timing error (ms) = 49.521 (linear interpolation).
