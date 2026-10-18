### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T21:37:42+00:00 |
| Finished (UTC) | 2026-10-17T21:52:34+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; standard library only |
| Git commit | `b6a4fca845093eaf193fb5bc966f44c4660d2aa2` (working tree dirty: True) |
| SHA-256 `dpc_simulator.py` | `a0967c8fd20968eb7dfd2b1c3a739c2302f484e6f7aec801f600320e5d17ea64` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `c65f99684bc737a223916dbf97f6e891874b78e0e7561914851f3aeecef37593` |
| SHA-256 `validation_study.py` | `cf20f07233fb9c74718a7cc959e88899d0ba42a823377cef5a7d36df6a68f066` |
| Wall time | 892.3 s |
| Worker processes | 10 |
| Seeds per size | 20 (base seed 20261017) |

### Claims (seeds in which the claim holds)

| ID | Statement | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|
| C1 | Crash-like and noise-like agents both abolish quorum (Section 6.2) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C2 | Without reference feedback (lambda = 0) there is no hysteresis (Section 4.3) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C3 | Hysteresis (neural inertia) grows with lambda; no recovery counts as unbounded (prediction 5) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C4 | Reference feedback sharpens the loss-of-consciousness transition (prediction 1) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C5 | Hub lesions lower the loss concentration more than random lesions (prediction 6) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C6 | Reduced arousal delays emergence more than it shifts induction (Kelz et al., 2008) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |
| C7 | Without the agent's action on arousal circuits, quorum is still lost but at a higher concentration (Moore et al., 2012; Eikermann et al., 2011) | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |

### Observations (seeds in which the observation occurs; not part of the verdict)

| ID | Statement | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|
| O1 | Trapped unconscious at zero concentration, lambda = 14.51 ms at the reference arousal level | 0/20 | 1/20 | 0/20 | 0/20 | 0/20 |
| O2 | Trapped unconscious at zero concentration after hub lesion, lambda = 6.99 ms | 0/20 | 0/20 | 0/20 | 0/20 | 0/20 |

### Extension tests (seeds in which the pre-specified test passes; not part of the verdict)

| ID | Statement | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|---|
| E1 | Sleep (no arousal, down-state fraction 0.095, rat) has a wakeable stable unconscious state | 4/20 | 2/20 | 0/20 | 0/20 | 0/20 |
| E2 | Deeper sleep (down-state fraction 0.25, human upper estimate) has a wakeable stable unconscious state | 16/20 | 17/20 | 20/20 | 20/20 | 20/20 |
| E3 | Deep anaesthesia has only an unconscious state, so no perturbation restores quorum | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 |

### Thresholds (mean ± SD across seeds, relative concentration units)

| Quantity | N = 302 | N = 1,000 | N = 10,000 | N = 100,000 | N = 1,000,000 |
|---|---|---|---|---|---|
| c_off, GABAergic-like | 0.989 ± 0.023 | 0.975 ± 0.015 | 0.964 ± 0.007 | 0.962 ± 0.004 | 0.960 ± 0.000 |
| c_on, GABAergic-like | 0.869 ± 0.046 | 0.872 ± 0.032 | 0.867 ± 0.013 | 0.870 ± 0.008 | 0.871 ± 0.004 |
| Hysteresis, GABAergic-like | 0.120 ± 0.041 | 0.103 ± 0.039 | 0.097 ± 0.015 | 0.092 ± 0.010 | 0.089 ± 0.004 |
| Transition width, GABAergic-like | 0.051 ± 0.030 | 0.034 ± 0.011 | 0.030 ± 0.006 | 0.029 ± 0.004 | 0.027 ± 0.005 |
| c_off, NMDA-antagonist-like | 0.570 ± 0.020 | 0.567 ± 0.010 | 0.563 ± 0.005 | 0.564 ± 0.005 | 0.560 ± 0.002 |
| c_off, hub graph intact | 0.962 ± 0.033 | 0.964 ± 0.017 | 0.950 ± 0.008 | 0.950 ± 0.000 | 0.950 ± 0.000 |
| c_off, random lesion | 0.942 ± 0.030 | 0.921 ± 0.016 | 0.912 ± 0.010 | 0.910 ± 0.000 | 0.910 ± 0.000 |
| c_off, hub lesion | 0.746 ± 0.042 | 0.713 ± 0.022 | 0.683 ± 0.008 | 0.681 ± 0.004 | 0.680 ± 0.000 |
| c_on, hub lesion | 0.658 ± 0.068 | 0.617 ± 0.041 | 0.619 ± 0.014 | 0.627 ± 0.010 | 0.631 ± 0.006 |
| Seconds per seed | 0.048 ± 0.006 | 0.126 ± 0.010 | 1.584 ± 0.058 | 29.017 ± 1.170 | 412.038 ± 8.938 |

**Verdict:** All claims hold for every seed at every size.
