"""Every number the open-data tests depend on, fixed before any confirmatory run (prespecification of 21 October 2026).

Changing a value here after the authors commit the prespecification makes the affected test exploratory; the
prespecification document says how such a change must be reported.
"""

from __future__ import annotations

from dataclasses import dataclass

SEED = 20261021


@dataclass(frozen=True)
class Band:
    name: str
    low_hz: float
    high_hz: float

    @property
    def centre_hz(self) -> float:
        return (self.low_hz + self.high_hz) / 2


GAMMA = Band("gamma", 30.0, 45.0)
SECONDARY_BANDS = (Band("theta", 4.0, 8.0), Band("alpha", 8.0, 13.0), Band("beta", 13.0, 30.0))


@dataclass(frozen=True)
class FmriNetwork:
    """Functional network from parcellated BOLD (Michigan dataset, ds006623)."""

    tr_seconds: float = 0.8
    window_trs: int = 75
    step_trs: int = 25
    edge_alpha: float = 0.01
    edge_alpha_sensitivity: tuple[float, ...] = (0.001, 0.05)
    surrogates_per_window: int = 20
    cofluctuation_volumes_per_surrogate: int = 20
    awake_max_concentration: float = 0.0
    framewise_displacement_limit_mm: float = 0.5
    max_censored_share: float = 0.2


@dataclass(frozen=True)
class ThresholdShape:
    """Prediction 1, test H1: is the collapse sharper than thresholding a smooth decline produces?"""

    null_realisations: int = 200
    min_width_ug_per_ml: float = 0.05
    max_width_ug_per_ml: float = 20.0
    bic_margin: float = 10.0
    smallest_steepness_ratio: float = 1.5
    smallest_local_slope_ratio: float = 1.5
    lor_coincidence_ug_per_ml: float = 0.4
    deep_top_share: float = 0.2
    intact_share: float = 0.9
    coupling_fall_gate: float = 0.9


@dataclass(frozen=True)
class EarlyWarning:
    """Prediction 2, tests H2a and H2b: rising variance and lag-1 autocorrelation before loss of responsiveness."""

    rolling_share: float = 0.5
    detrend_bandwidth_share: float = 0.1
    surrogates: int = 1000
    smallest_kendall_tau: float = 0.2
    min_points: int = 40


@dataclass(frozen=True)
class EcogNetwork:
    """Macaque ECoG (Neurotycho): bipolar derivations, long-range pairs, phase-based measures."""

    sampling_hz: float = 1000.0
    filter_order: int = 4
    filter_margin_seconds: float = 2.0
    line_noise_hz: tuple[float, ...] = (50.0, 100.0, 150.0)
    notch_quality: float = 30.0
    long_range_quantile: float = 0.5
    window_seconds: float = 1.0
    block_seconds: float = 30.0
    order_parameter_window_seconds: float = 2.0
    edge_alpha: float = 0.01
    surrogates_per_window: int = 20
    min_shift_seconds: float = 1.0
    muscle_band: tuple[float, float] = (70.0, 150.0)
    muscle_mad_limit: float = 5.0
    muscle_mad_floor: float = 0.05


@dataclass(frozen=True)
class LagVariability:
    """Prediction 3, test H3: lag variability against mean lag and local power, across agents."""

    bootstrap_resamples: int = 2000
    smallest_auc_difference: float = 0.05
    confidence: float = 0.95


@dataclass(frozen=True)
class Hysteresis:
    """Test H4: induction against emergence, with the pharmacokinetic sensitivity analysis."""

    smallest_ratio: float = 1.05
    ke0_per_minute: tuple[float, ...] = (0.2, 0.26, 0.456, 0.8, 1.21)


@dataclass(frozen=True)
class EvokedLatency:
    """Prediction 8, test H5 (partial): trial-to-trial latency variability of responses between areas."""

    artefact_end_ms: float = 9.0
    response_end_ms: float = 100.0
    baseline_ms: tuple[float, float] = (-500.0, -10.0)
    max_shift_ms: float = 20.0
    response_z: float = 3.4
    smallest_log_ratio: float = 0.18232155679395462  # log(1.2)
    unit_window_ms: tuple[float, float] = (2.0, 50.0)
    min_distance_mm: float = 20.0
    min_trials: int = 6


@dataclass(frozen=True)
class Family:
    alpha: float = 0.05
    primary_tests: tuple[str, ...] = ("H1", "H2a", "H2b", "H3", "H4")


FMRI = FmriNetwork()
SHAPE = ThresholdShape()
WARNING = EarlyWarning()
ECOG = EcogNetwork()
LAG = LagVariability()
HYSTERESIS = Hysteresis()
EVOKED = EvokedLatency()
FAMILY = Family()
