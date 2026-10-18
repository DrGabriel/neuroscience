### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-17T22:23:09.732294+00:00 |
| Finished (UTC) | 2026-10-17T22:46:01.783526+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `f9d4ba1152281dc5d583dfc1ca6f56acbff3a54e` (working tree dirty: True) |
| SHA-256 `calibration.py` | `f2004f8beadb94de151a8d176cce884e3cd927678d2e855024b01a11932662db` |
| SHA-256 `connectomes.py` | `28a0fc40a77bfeca508a0a1abc288a89ffbbc9d74a02e6771fc0e893b87d5e9e` |
| SHA-256 `dpc_simulator.py` | `a0967c8fd20968eb7dfd2b1c3a739c2302f484e6f7aec801f600320e5d17ea64` |
| SHA-256 `phase_dynamics.py` | `b12417d2578f071d33e00cfad9b586435c621aaae9d3210a29f32a987497b529` |
| SHA-256 `plant_tissue.py` | `a50afa829fd68ec4d78524ff7e34fb7b9f7a6615b9108eb0f6906054e81a7041` |
| SHA-256 `provenance.py` | `94071e252347139bab3c5f113d52a38f65feaeaa0c03738ec8d81090c9139cb2` |
| SHA-256 `reporting.py` | `c65f99684bc737a223916dbf97f6e891874b78e0e7561914851f3aeecef37593` |
| SHA-256 `sensitivity_study.py` | `ac6c2e5bc7c3fe54c3ea1ec9b7892cba2e5b412627a8d3af268ddd18faea1e3c` |
| SHA-256 `species_study.py` | `d52d137f6ea396e3b79aef0b9a80e0ac1d970bfe3864d5653550c308f44c220b` |
| SHA-256 `validation_study.py` | `cf20f07233fb9c74718a7cc959e88899d0ba42a823377cef5a7d36df6a68f066` |

### Percolation model: claims holding across seeds (N = 10,000)

| Variation | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| Quorum fraction = 0.3 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Quorum fraction = 0.5 (reference) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Quorum fraction = 0.7 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Arousal level (λ recalibrated) = 0 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | n/a | n/a |
| Arousal level (λ recalibrated) = 0.3 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Arousal level (λ recalibrated) = 0.5 (reference) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Arousal level (λ recalibrated) = 0.7 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Hill coefficient = 2 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Hill coefficient = 4 (reference) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Hill coefficient = 8 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Mean degree = 4 | 10/10 | 10/10 | 0/10 | 0/10 | 0/10 | 0/10 | 10/10 |
| Mean degree = 8 (reference) | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| Mean degree = 16 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |

### Phase-oscillator model, human connectome: pillars holding across seeds

| Variation | P2a | P2b | P3 |
|---|---|---|---|
| Synaptic coupling K = 2 | 5/5 | 5/5 | 5/5 |
| Synaptic coupling K = 4 (reference) | 5/5 | 5/5 | 5/5 |
| Synaptic coupling K = 8 | 5/5 | 5/5 | 5/5 |
| Natural-frequency spread = 0.25 | 0/5 | 5/5 | 0/5 |
| Natural-frequency spread = 0.5 (reference) | 5/5 | 5/5 | 5/5 |
| Natural-frequency spread = 1 | 5/5 | 5/5 | 5/5 |
| Noise intensity D = 0.02 | 5/5 | 5/5 | 5/5 |
| Noise intensity D = 0.05 (reference) | 5/5 | 5/5 | 5/5 |
| Noise intensity D = 0.1 | 5/5 | 5/5 | 5/5 |
| Quorum fraction = 0.3 | 5/5 | 5/5 | 5/5 |
| Quorum fraction = 0.5 (reference) | 5/5 | 5/5 | 5/5 |
| Quorum fraction = 0.7 | 5/5 | 5/5 | 5/5 |
