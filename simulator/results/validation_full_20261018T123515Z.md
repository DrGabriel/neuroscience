### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-18T12:35:15+00:00 |
| Finished (UTC) | 2026-10-18T12:44:33+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; standard library only |
| Git commit | `5c7512c46abc11bc56b1dfc5fe78c529892aab97` (working tree dirty: True) |
| SHA-256 `dpc_simulator.py` | `9080470f6134967e13b6f6bee7b295c1f04cbac75f545a5bbd89d7e5aca8da25` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `de80a53d63e90383ed325db5098aea06b71b3f846d8368ddeb12347ce3c4470b` |
| SHA-256 `validation_study.py` | `4976de996a1f416704fa61e91ce6bbfb5ffbae97a705764f3d0ced01503a1159` |
| Wall time | 558.1 s |
| Worker processes | 10 |
| Seeds per size | 20 (base seed 20261017) |

### Claims (seeds in which the claim holds)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| C1 | Crash-like and noise-like agents both abolish quorum (Section 6.2) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C2 | Without reference feedback (lambda = 0) there is no hysteresis (Section 4.3) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C3 | Hysteresis (neural inertia) grows with lambda; no recovery counts as unbounded (prediction 5) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C4 | Reference feedback sharpens the loss-of-consciousness transition (prediction 1) | test | 19/20 (76–99%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C5 | Hub lesions lower the loss concentration more than random lesions (prediction 6) | test | 16/20 (58–92%) | 17/20 (64–95%) | 9/20 (26–66%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C6 | Reduced arousal delays emergence more than it shifts induction (Kelz et al., 2008) | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| C7 | Without the agent's action on arousal circuits, quorum is still lost but at a higher concentration (Moore et al., 2012; Eikermann et al., 2011) | consistency check | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Observations (seeds in which the observation occurs; not part of the verdict)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| O1 | Trapped unconscious at zero concentration, lambda = 16.52 ms at the reference arousal level | test | 4/20 (8–42%) | 2/20 (3–30%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) |
| O2 | Trapped unconscious at zero concentration after hub lesion, lambda = 10.06 ms | test | 5/20 (11–47%) | 10/20 (30–70%) | 7/20 (18–57%) | 5/20 (11–47%) | 1/20 (1–24%) |
| O3 | Sleep with population-level down-states at the rat share (0.095) loses quorum | test | 1/20 (1–24%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) | 0/20 (0–16%) |
| O4 | Sleep with population-level down-states at the human share (0.25) loses quorum | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Extension tests (seeds in which the pre-specified test passes; not part of the verdict)

| ID | Statement | Kind | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|---|
| E1 | Sleep (no arousal, connection-level down-states, share 0.095, rat) has a wakeable stable unconscious state | test | 18/20 (70–97%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |
| E2 | Deeper sleep (connection-level down-states, share 0.25, human upper estimate) has a wakeable stable unconscious state | test | 12/20 (39–78%) | 8/20 (22–61%) | 1/20 (1–24%) | 0/20 (0–16%) | 0/20 (0–16%) |
| E3 | Deep anaesthesia has only an unconscious state, so no perturbation restores quorum | test | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) | 20/20 (84–100%) |

### Thresholds (mean ± SD across seeds, relative concentration units)

| Quantity | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|
| c_off, GABAergic-like | 0.882 ± 0.037 | 0.868 ± 0.019 | 0.856 ± 0.008 | 0.859 ± 0.003 | 0.860 ± 0.002 |
| c_on, GABAergic-like | 0.776 ± 0.055 | 0.779 ± 0.039 | 0.775 ± 0.015 | 0.774 ± 0.008 | 0.777 ± 0.005 |
| Hysteresis, GABAergic-like | 0.106 ± 0.041 | 0.089 ± 0.047 | 0.081 ± 0.015 | 0.084 ± 0.008 | 0.083 ± 0.005 |
| Transition width, GABAergic-like | 0.265 ± 0.107 | 0.220 ± 0.029 | 0.213 ± 0.013 | 0.218 ± 0.004 | 0.219 ± 0.002 |
| Transmission failure p at c_off, GABAergic-like | 0.359 ± 0.037 | 0.344 ± 0.019 | 0.332 ± 0.008 | 0.335 ± 0.003 | 0.335 ± 0.002 |
| Effective jitter (ms) at c_off, GABAergic-like | 3.912 ± 0.352 | 3.930 ± 0.207 | 3.805 ± 0.206 | 3.862 ± 0.113 | 3.906 ± 0.085 |
| Coherence probability π at c_off, GABAergic-like | 0.193 ± 0.023 | 0.196 ± 0.012 | 0.205 ± 0.011 | 0.201 ± 0.006 | 0.199 ± 0.005 |
| Share of populations silent at once for sleep to lose quorum | 0.136 ± 0.022 | 0.126 ± 0.013 | 0.121 ± 0.006 | 0.116 ± 0.002 | 0.117 ± 0.000 |
| c_off, NMDA-antagonist-like | 0.621 ± 0.022 | 0.619 ± 0.010 | 0.617 ± 0.006 | 0.620 ± 0.000 | 0.620 ± 0.000 |
| c_off, hub graph intact | 0.881 ± 0.041 | 0.885 ± 0.021 | 0.870 ± 0.008 | 0.870 ± 0.002 | 0.870 ± 0.000 |
| c_off, random lesion | 0.860 ± 0.038 | 0.831 ± 0.022 | 0.824 ± 0.010 | 0.821 ± 0.003 | 0.820 ± 0.000 |
| c_off, hub lesion | 0.530 ± 0.129 (16/20) | 0.448 ± 0.069 (17/20) | 0.326 ± 0.031 (9/20) | 0.254 ± 0.053 | 0.253 ± 0.014 |
| c_on, hub lesion | 0.466 ± 0.147 (11/20) | 0.359 ± 0.059 (7/20) | 0.210 ± 0.042 (2/20) | 0.245 ± 0.050 (15/20) | 0.251 ± 0.015 (19/20) |
| Seconds per seed | 0.035 ± 0.008 | 0.072 ± 0.010 | 0.885 ± 0.045 | 15.550 ± 0.428 | 256.309 ± 11.798 |

**Verdict:** At least one claim failed; see the claims table.
