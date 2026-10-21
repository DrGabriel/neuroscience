### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-21T20:15:13.375058+00:00 |
| Finished (UTC) | 2026-10-21T20:15:22.266059+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1, pyarrow 26.0.0 |
| Git commit | `74f9cb009f6e5096b0fcea8f23b798a9d941eb60` (working tree dirty: False) |
| SHA-256 `calibration.py` | `da8a964155ad650d0c5cbdf570f95a5334a8fc3e8eacbcc83d59d9e5c60c5b3a` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `directed_threshold_estimate.py` | `68f4c1b27077fe91196aa9a70b936d6ef1b45933196979aeb24fcc3519d90eac` |
| SHA-256 `dpc_simulator.py` | `621859b0bca3cc34cedd82e1559e1097bf90142d698e8c7d95b3e0907417c452` |
| SHA-256 `percolation_thresholds.py` | `6ba5d6ef1f4ed376063c30ec0e0f541fe08259a6c50a5b279b14ae82ca5125d2` |
| SHA-256 `phase_dynamics.py` | `faf6fb06cb484f473d6409a513daf43bd0ab3737d446efa3f0f5b7286ea9b78d` |
| SHA-256 `plant_tissue.py` | `e9dac3d0f0c2c9baa8e813f65ea71615e65a027edd4d3115e86e556203ece030` |
| SHA-256 `provenance.py` | `c2d147f298a0ecc43e72d2704a3fda67913847cbbc03e7525394df1677c27e6f` |
| SHA-256 `reporting.py` | `6e6a07609b80574406c4893bc9b2ea8eecd6ea6c7f13b08ecbdc147e2b55ea88` |
| SHA-256 `round3_study/__init__.py` | `00aa9455701c44e6c2eda71b8a0e2164ecc5d1705e124a9d5a8519f4fe2082fc` |
| SHA-256 `round3_study/directed_estimate.py` | `7a858b7de7fb92d70921e2a4358d4d7b643047323883f34dfda8adb5a7be9bd3` |

Measured thresholds from `percolation_full_20261020T011339Z.json` (Appendix B.5). Deterministic estimate, reported without a verdict;
it assumes an uncorrelated directed network and so ignores degree correlations, reciprocity among them.

### Giant strongly connected component: generating-function estimate against the directed measurement

| Organism | Populations | Arcs | Mean degree <k> | <k_in k_out> | Onset π_c = <k>/<k_in k_out> | Quorum π_q, q* = 0.5 (estimate) | Quorum π_q, directed (B.5, measured) | Estimate / measured | Critical failure p_q (estimate) | Critical jitter σ_q, ms (estimate) |
|---|---|---|---|---|---|---|---|---|---|---|
| C. elegans | 300 | 5,764 | 19.21 | 510.0 | 0.0377 | 0.0967 | 0.1058 ± 0.0079 | 0.91 | 0.747 | 12.3 |
| Drosophila | 138,639 | 2,700,513 | 19.48 | 2059.9 | 0.0095 | 0.1441 | 0.1503 ± 0.0006 | 0.96 | 0.624 | 8.3 |
| Human | 998 | 35,730 | 35.80 | 1536.3 | 0.0233 | 0.0474 | 0.0495 ± 0.0015 | 0.96 | 0.876 | 25.2 |
