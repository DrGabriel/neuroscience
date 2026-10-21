### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-21T20:16:44+00:00 |
| Finished (UTC) | 2026-10-21T20:28:45+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; standard library only |
| Git commit | `74f9cb009f6e5096b0fcea8f23b798a9d941eb60` (working tree dirty: False) |
| SHA-256 `calibration.py` | `da8a964155ad650d0c5cbdf570f95a5334a8fc3e8eacbcc83d59d9e5c60c5b3a` |
| SHA-256 `comparisons.py` | `340b044083ffa2e8f98988da8fb400fa25c961db5f08c4bce42e5681441b92c8` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `dpc_simulator.py` | `621859b0bca3cc34cedd82e1559e1097bf90142d698e8c7d95b3e0907417c452` |
| SHA-256 `fresh_seed_validation.py` | `6beecc211ebc8e0cbd198f594b8363eb0f58402738ca307d54e2b62cbb34d38d` |
| SHA-256 `phase_dynamics.py` | `faf6fb06cb484f473d6409a513daf43bd0ab3737d446efa3f0f5b7286ea9b78d` |
| SHA-256 `plant_tissue.py` | `e9dac3d0f0c2c9baa8e813f65ea71615e65a027edd4d3115e86e556203ece030` |
| SHA-256 `provenance.py` | `c2d147f298a0ecc43e72d2704a3fda67913847cbbc03e7525394df1677c27e6f` |
| SHA-256 `reporting.py` | `6e6a07609b80574406c4893bc9b2ea8eecd6ea6c7f13b08ecbdc147e2b55ea88` |
| SHA-256 `round3_study/__init__.py` | `00aa9455701c44e6c2eda71b8a0e2164ecc5d1705e124a9d5a8519f4fe2082fc` |
| SHA-256 `round3_study/fresh_validation.py` | `b797d9a1a75f991a1a3c0250d5b1f2b8e74be4679564f9a70a89d8b44fe0a839` |
| SHA-256 `round3_study/seeds.py` | `cfac3da892116212648efabe600036c8be21d5ad5de3805e88fd43ddbba3929f` |
| SHA-256 `validation_study.py` | `faddc88ec38d252920949636b924b6f10a89e1ec2c8f1c6355543150b2e92eb8` |
| Wall time | 721.1 s |
| Worker processes | 10 |
| Seeds per size | 20 (base seed 20268617) |

### Claims (seeds in which the claim holds)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| C1 | Omission-fault and timing-fault agents both abolish quorum (Section 6.2) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C2 | Without reference feedback (lambda = 0) there is no hysteresis (Section 4.3) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C3 | Hysteresis (neural inertia) grows with lambda; no recovery counts as unbounded (prediction 5) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C4 | Reference feedback sharpens the loss-of-consciousness transition (prediction 1) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C5 | Hub lesions lower the loss concentration more than random lesions (prediction 6) | test | 19/20 (76–99%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C6 | Reduced arousal delays emergence more than it shifts induction (Kelz et al., 2008) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C7 | Without the agent's action on arousal circuits, quorum is still lost but at a higher concentration (Moore et al., 2012; Eikermann et al., 2011) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Observations (seeds in which the observation occurs; not part of the verdict)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| O1 | Trapped unconscious at zero concentration, lambda = 16.52 ms at the reference arousal level | test | 2/20 (3–30%) | 1/20 (1–24%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) |
| O2 | Trapped unconscious at zero concentration after hub lesion, lambda = 8.85 ms | test | 6/20 (15–52%) | 3/20 (5–36%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) |
| O3 | Sleep with population-level down-states at the rat share (0.095) loses quorum | test | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) |
| O4 | Sleep with population-level down-states at the human share (0.25) loses quorum | test | 19/20 (76–99%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| O5 | Sleep with one typical human slow wave silencing its measured share of regions (0.271) loses quorum (Nir et al., 2011) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Extension tests (seeds in which the pre-specified test passes; not part of the verdict)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| E1 | Sleep (no arousal, connection-level down-states, share 0.095, rat) has a wakeable stable unconscious state | test | 13/20 (43–82%) | 12/20 (39–78%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| E2 | Deeper sleep (connection-level down-states, share 0.25, human upper estimate) has a wakeable stable unconscious state | test | 18/20 (70–97%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| E3 | Deep anaesthesia has only an unconscious state, so no perturbation restores quorum | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Thresholds (mean ± SD across seeds, relative concentration units)

| Quantity | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|
| c_off, GABAergic-like | 0.909 ± 0.030 | 0.900 ± 0.014 | 0.887 ± 0.006 | 0.884 ± 0.005 | 0.880 ± 0.002 |
| c_on, GABAergic-like | 0.827 ± 0.039 | 0.840 ± 0.032 | 0.828 ± 0.010 | 0.827 ± 0.007 | 0.826 ± 0.005 |
| Hysteresis, GABAergic-like | 0.082 ± 0.031 | 0.060 ± 0.031 | 0.058 ± 0.011 | 0.057 ± 0.007 | 0.054 ± 0.005 |
| Transition width, GABAergic-like | 0.291 ± 0.080 | 0.250 ± 0.044 | 0.237 ± 0.013 | 0.237 ± 0.007 | 0.232 ± 0.004 |
| Transmission failure p at c_off, GABAergic-like | 0.385 ± 0.030 | 0.376 ± 0.014 | 0.363 ± 0.006 | 0.360 ± 0.005 | 0.357 ± 0.002 |
| Effective jitter (ms) at c_off, GABAergic-like | 3.866 ± 0.267 | 3.890 ± 0.264 | 3.810 ± 0.119 | 3.764 ± 0.149 | 3.672 ± 0.090 |
| Coherence probability π at c_off, GABAergic-like | 0.187 ± 0.019 | 0.188 ± 0.014 | 0.195 ± 0.006 | 0.199 ± 0.009 | 0.204 ± 0.005 |
| Share of populations silent at once for sleep to lose quorum | 0.179 ± 0.031 | 0.161 ± 0.015 | 0.153 ± 0.006 | 0.152 ± 0.002 | 0.152 ± 0.001 |
| c_off, NMDA-antagonist-like | 0.627 ± 0.018 | 0.625 ± 0.008 | 0.623 ± 0.005 | 0.621 ± 0.004 | 0.620 ± 0.000 |
| c_off, hub graph intact | 0.919 ± 0.039 | 0.916 ± 0.019 | 0.905 ± 0.005 | 0.903 ± 0.005 | 0.900 ± 0.000 |
| c_off, random lesion | 0.870 ± 0.041 | 0.867 ± 0.021 | 0.855 ± 0.009 | 0.858 ± 0.004 | 0.859 ± 0.003 |
| c_off, hub lesion | 0.584 ± 0.096 (19/20) | 0.499 ± 0.068 | 0.449 ± 0.030 | 0.453 ± 0.010 | 0.449 ± 0.004 |
| c_on, hub lesion | 0.587 ± 0.055 (13/20) | 0.451 ± 0.099 (17/20) | 0.438 ± 0.042 | 0.452 ± 0.010 | 0.449 ± 0.004 |
| Seconds per seed | 0.048 ± 0.010 | 0.096 ± 0.013 | 1.358 ± 0.069 | 21.597 ± 2.468 | 324.712 ± 26.702 |

**Verdict:** At least one claim failed; see the claims table.

### Loss-to-recovery concentration ratio c_off / c_on, GABAergic-like agent (no verdict)

| Quantity | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|
| c_off / c_on, mean ± SD | 1.101 ± 0.042 | 1.072 ± 0.040 | 1.071 ± 0.014 | 1.069 ± 0.009 | 1.066 ± 0.007 |

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| R1 | The loss-to-recovery ratio lies within the published range 1.07 to 1.63 | test | 15/20 (53–89%) | 10/20 (30–70%) | 11/20 (34–74%) | 13/20 (43–82%) | 9/20 (26–66%) |
