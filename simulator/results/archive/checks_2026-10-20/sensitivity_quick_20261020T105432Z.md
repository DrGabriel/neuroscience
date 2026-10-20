### Run metadata

| Field | Value |
|---|---|
| Started (UTC) | 2026-10-20T10:54:32.098918+00:00 |
| Finished (UTC) | 2026-10-20T10:55:57.289537+00:00 |
| Machine | Mac14,9, Apple M2 Pro |
| CPU cores | 10 (6 performance, 4 efficiency) |
| Memory | 32 GiB |
| Operating system | macOS 26.7.1 (build 25G241), arm64 |
| Python | CPython 3.13.2; numpy 2.5.4, scipy 1.18.1 |
| Git commit | `ca2968fa252b68b06ddf08bfc97ee530bb2939ef` (working tree dirty: True) |
| SHA-256 `calibration.py` | `5cdcad39d08837ed395d1f6dbd4c5d935fe24b8632b9814c1b672ee8c4146bb1` |
| SHA-256 `comparisons.py` | `340b044083ffa2e8f98988da8fb400fa25c961db5f08c4bce42e5681441b92c8` |
| SHA-256 `connectomes.py` | `b13446025b96ad86be7f4121b4c2b227dc58a4f38dc1c4db866c8b3bff86f3d1` |
| SHA-256 `dpc_simulator.py` | `621859b0bca3cc34cedd82e1559e1097bf90142d698e8c7d95b3e0907417c452` |
| SHA-256 `phase_dynamics.py` | `7470f3f061d933b64e51bb060752914bbcfa166b3653d1dc89beeb4fc032241a` |
| SHA-256 `plant_tissue.py` | `e9dac3d0f0c2c9baa8e813f65ea71615e65a027edd4d3115e86e556203ece030` |
| SHA-256 `provenance.py` | `f320d7cc34706f1a0a92ea109c270872557e999139b9832304eef1fc5032b122` |
| SHA-256 `reporting.py` | `78a8c5e399d134fdcf01a2af3be99396ff3a3eb25ebb62915bcb27ec8635fc37` |
| SHA-256 `sensitivity_study.py` | `c3f6fbb824dc2afd710ba16e1d2c126e120545f64eaf18956768c3039b0b710f` |
| SHA-256 `species_study.py` | `423902f7037b6735db60c2826cfe212cf0c664859aeeda83317d9ea3421217ba` |
| SHA-256 `validation_study.py` | `70b5ecf19ef90acbd8d2b4729a130debe15094411a6c01f8bdbd2ca69a21f050` |

### Percolation model: claims holding across seeds (N = 10,000)

| Variation | C1 | C2 | C3 | C4 | C5 | C6 | C7 |
|---|---|---|---|---|---|---|---|
| Quorum fraction = 0.3 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Quorum fraction = 0.5 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Quorum fraction = 0.7 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 0/2 (0–66%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Arousal level (λ recalibrated) = 0 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 0/2 (0–66%) | n/a | n/a |
| Arousal level (λ recalibrated) = 0.3 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 1/2 (9–91%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Arousal level (λ recalibrated) = 0.5 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Arousal level (λ recalibrated) = 0.7 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Feedback λ (ms), one per reproduced inertia ratio = 8.49 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Feedback λ (ms), one per reproduced inertia ratio = 8.85 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Feedback λ (ms), one per reproduced inertia ratio = 10.06 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 1/2 (9–91%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Feedback λ (ms), one per reproduced inertia ratio = 16.52 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 0/2 (0–66%) | 0/2 (0–66%) | 2/2 (34–100%) |
| Hill coefficient = 2 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Hill coefficient = 4 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Hill coefficient = 8 | 2/2 (34–100%) | 2/2 (34–100%) | 1/2 (9–91%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Mean degree = 4 | 0/2 (0–66%) | 2/2 (34–100%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) |
| Mean degree = 8 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Mean degree = 16 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Integration window W (ms) = 1 | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) |
| Integration window W (ms) = 3 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Integration window W (ms) = 10 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Baseline jitter (ms) = 1 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Baseline jitter (ms) = 3 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Baseline jitter (ms) = 10 | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) | 0/2 (0–66%) |
| Maximal transmission failure, GABAergic-like = 0.6 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 0/2 (0–66%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Maximal transmission failure, GABAergic-like = 0.8 | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |
| Maximal transmission failure, GABAergic-like = 0.95 (reference) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) | 2/2 (34–100%) |

### Phase-oscillator model, human connectome: pillars holding across seeds

| Variation | P2a | P2b | P3 |
|---|---|---|---|
| Synaptic coupling K = 2 | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Synaptic coupling K = 4 (reference) | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Synaptic coupling K = 8 | 1/1 (21–100%) | 1/1 (21–100%) | 1/1 (21–100%) |
| Natural-frequency spread = 0.25 | 0/1 (0–79%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Natural-frequency spread = 0.5 (reference) | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Natural-frequency spread = 1 | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Noise intensity D = 0.02 | 1/1 (21–100%) | 1/1 (21–100%) | 1/1 (21–100%) |
| Noise intensity D = 0.05 (reference) | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Noise intensity D = 0.1 | 1/1 (21–100%) | 1/1 (21–100%) | 1/1 (21–100%) |
| Quorum fraction = 0.3 | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Quorum fraction = 0.5 (reference) | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Quorum fraction = 0.7 | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Jitter correlation time τ = 0.25 | 1/1 (21–100%) | 1/1 (21–100%) | 1/1 (21–100%) |
| Jitter correlation time τ = 1 (reference) | 1/1 (21–100%) | 1/1 (21–100%) | 0/1 (0–79%) |
| Jitter correlation time τ = 4 | 1/1 (21–100%) | 1/1 (21–100%) | 1/1 (21–100%) |
