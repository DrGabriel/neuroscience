"""Phase-oscillator model of the DPC hypothesis on empirical connectomes.

Each node is a neural population, represented by the phase of its oscillation. Phases
follow the Kuramoto-Sakaguchi model (Kuramoto, 1984; Sakaguchi & Kuramoto, 1986), the
standard reduced description of large-scale brain synchrony (Cabral et al., 2011;
Breakspear, 2017), integrated with the Euler-Maruyama scheme:

    dθ_i = [ω_i + synaptic_i + reference_i + sensory_i] dt + sqrt(2 D dt) ξ_i

    synaptic_i  = (K / s_i) Σ_j w_ji m_ji sin(θ_j − θ_i − α_ji)
                  m_ji: 1 if connection j→i transmits, 0 if it has failed   (failure p(c), P4a)
                  α_ji: phase error = fixed conduction lag (if delays are modelled) plus timing
                        jitter, Gaussian with SD 2π f σ(c), redrawn at every step by default
                        (trial-to-trial variability) or fixed per connection          (P4b)
    reference_i = λ [R + A(c)(1 − R)] sin(ψ − θ_i)
                                          shared phase reference whose strength grows with global
                                          coherence R (P5), partly sustained by arousal A (P7),
                                          which the agent suppresses
    sensory_i   = F sin(Ω t − θ_i)       periodic stimulus on sensory populations only

The anaesthetic agent is the same AnaestheticAgent used by the percolation model.
Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, Sequence

import numpy as np

from connectomes import Connectome
import dpc_simulator as dpc
from dpc_simulator import AnaestheticAgent, ConcentrationGrid

MILLISECONDS_PER_SECOND = 1000.0
FULL_CYCLE_RADIANS = 2 * np.pi


# ---------------------------------------------------------------------------
# Parameters (values and their sources live in calibration.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PopulationDynamics:
    """Intrinsic and coupling properties of the oscillating neural populations."""

    synaptic_coupling: float
    natural_frequency_spread: float
    noise_intensity: float
    reference_feedback: float
    oscillation_frequency_hz: float
    baseline_jitter_ms: float
    arousal_level: float = 0.0
    # P8 (adaptive reference rate): when set, the reference rhythm slows from
    # oscillation_frequency_hz towards this value as the agent takes effect. None keeps it fixed.
    fallback_frequency_hz: float | None = None


@dataclass(frozen=True)
class IntegrationSettings:
    time_step: float
    relaxation_steps: int
    measurement_steps: int


class JitterScaling(Enum):
    """How timing error is distributed across connections."""

    UNIFORM = "uniform"
    # Timing error accumulates along the conduction path like a random walk, so its SD
    # grows with the square root of tract length (relative to the mean length).
    CONDUCTION_LENGTH = "conduction length"
    # The agent's added jitter acts only on connections leaving the sensory populations
    # (the ketamine pathway hypothesis); baseline jitter still acts everywhere.
    SENSORY_PATHWAYS = "sensory pathways"


class JitterDynamics(Enum):
    """Whether timing error varies over time or is a fixed offset of each connection."""

    # Redrawn at every integration step: trial-to-trial timing variability, the quantity measured
    # by Mainen & Sejnowski (1995): the "latency variance" of the consensus analogy.
    FLUCTUATING = "fluctuating"
    # Drawn once per connection: a systematic timing offset, the "clock skew" of the consensus analogy.
    FIXED = "fixed"


@dataclass(frozen=True)
class SensoryStimulus:
    """Periodic forcing of the sensory populations at a frequency offset from the network rhythm."""

    strength: float
    angular_frequency: float


@dataclass(frozen=True)
class SweepDesign:
    """Everything one induction-emergence sweep needs, grouped to keep call sites small."""

    agent: AnaestheticAgent
    dynamics: PopulationDynamics
    integration: IntegrationSettings
    grid: ConcentrationGrid
    quorum_fraction: float
    seed: int
    jitter_scaling: JitterScaling = JitterScaling.UNIFORM
    jitter_dynamics: JitterDynamics = JitterDynamics.FLUCTUATING
    stimulus: SensoryStimulus | None = None
    # When set, constant conduction delays (tract length / velocity) enter as fixed phase lags.
    conduction_velocity_m_per_s: float | None = None
    # When set, connections are signed by this rule (connectomes.FLYWIRE_INHIBITORY_TRANSMITTERS):
    # inhibitory connections (sign -1) push phases apart instead of together.
    sign_rule: str | None = None


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StateMeasurement:
    """Observables averaged over the measurement window at one effect-site concentration."""

    concentration: float
    global_coherence: float
    susceptibility: float
    local_coherence: float
    sensory_entrainment: float | None = None
    broadcast_entrainment: float | None = None
    locking_to_mean_field: float = 0.0


@dataclass(frozen=True)
class ChanceCoherence:
    """Expected order parameter of uniformly random phases, E|mean e^{iθ}| ≈ sqrt(π / 4n)."""

    global_level: float
    local_level: float

    @classmethod
    def of(cls, node_count: int, module_sizes: np.ndarray) -> ChanceCoherence:
        local = float((module_sizes * np.sqrt(np.pi / (4 * module_sizes))).sum() / module_sizes.sum())
        return cls(float(np.sqrt(np.pi / (4 * node_count))), local)


@dataclass(frozen=True)
class InductionEmergenceRecord:
    """One sweep: concentration raised from zero (induction), then lowered again (emergence)."""

    awake_coherence: float
    quorum_fraction: float
    chance: ChanceCoherence
    induction: tuple[StateMeasurement, ...]
    emergence: tuple[StateMeasurement, ...]

    def is_conscious(self, measurement: StateMeasurement) -> bool:
        """Quorum: global coherence at least a fixed fraction of its awake value."""
        return measurement.global_coherence >= self.quorum_fraction * self.awake_coherence

    @property
    def first_unconscious(self) -> StateMeasurement | None:
        return next((point for point in self.induction if not self.is_conscious(point)), None)

    def at(self, concentration: float) -> StateMeasurement:
        """The induction measurement closest to a given concentration."""
        return min(self.induction, key=lambda point: abs(point.concentration - concentration))


# ---------------------------------------------------------------------------
# Drives acting on the populations (one class per term of the equation)
# ---------------------------------------------------------------------------


class PhaseDrive(Protocol):
    def __call__(self, phases: np.ndarray, mean_field: complex, time: float) -> np.ndarray: ...


@dataclass(frozen=True)
class ImpairedConnectivity:
    """Connections that still transmit at a given concentration, with their timing properties."""

    sources: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    fixed_lags: np.ndarray
    jitter_sd: np.ndarray


class ConnectionImpairment:
    """Applies an anaesthetic agent to the connectome using fixed (quenched) random draws.

    Drawing once per realisation, not once per concentration, means a connection that
    fails at a low concentration stays failed at every higher one.
    """

    def __init__(self, connectome: Connectome, design: SweepDesign, rng: np.random.Generator) -> None:
        self._connectome = connectome
        self._agent = design.agent
        self._dynamics = design.dynamics
        self._failure_draws = rng.random(connectome.edge_count)
        self._jitter_draws = rng.standard_normal(connectome.edge_count)
        self._baseline_weights, self._agent_weights = jitter_weights(connectome, design.jitter_scaling)
        self._delays_ms = conduction_delays_ms(connectome, design)
        self._jitter_dynamics = design.jitter_dynamics
        self._weights = signed_weights(connectome, design)

    def at(self, concentration: float) -> ImpairedConnectivity:
        """Timing errors are converted to phase at the reference rate in force at this concentration."""
        transmits = self._failure_draws >= self._agent.transmission_failure(concentration)
        jitter_ms = (
            self._dynamics.baseline_jitter_ms * self._baseline_weights
            + self._agent.added_jitter_ms(concentration) * self._agent_weights
        )
        frequency_hz = reference_frequency_hz(self._dynamics, self._agent, concentration)
        jitter_sd = milliseconds_to_radians(jitter_ms, frequency_hz)
        fixed_lags = milliseconds_to_radians(self._delays_ms, frequency_hz)
        if self._jitter_dynamics is JitterDynamics.FIXED:
            fixed_lags, jitter_sd = fixed_lags + self._jitter_draws * jitter_sd, np.zeros_like(jitter_sd)
        return ImpairedConnectivity(
            sources=self._connectome.sources[transmits],
            targets=self._connectome.targets[transmits],
            weights=self._weights[transmits],
            fixed_lags=fixed_lags[transmits],
            jitter_sd=np.broadcast_to(jitter_sd, transmits.shape)[transmits],
        )


def signed_weights(connectome: Connectome, design: SweepDesign) -> np.ndarray:
    """Connection weights, negative for inhibitory connections when a sign rule is used."""
    if design.sign_rule is None:
        return connectome.weights
    if design.sign_rule not in connectome.signs:
        raise ValueError(f"{connectome.name} has no connection signs for rule {design.sign_rule!r}")
    return connectome.weights * connectome.signs[design.sign_rule]


def reference_frequency_hz(dynamics: PopulationDynamics, agent: AnaestheticAgent, concentration: float) -> float:
    """Reference rate at this concentration: fixed, or slowing towards the fallback rate (P8)."""
    if dynamics.fallback_frequency_hz is None:
        return dynamics.oscillation_frequency_hz
    slowing = (dynamics.oscillation_frequency_hz - dynamics.fallback_frequency_hz) * agent.effect_fraction(concentration)
    return dynamics.oscillation_frequency_hz - slowing


def milliseconds_to_radians(milliseconds: np.ndarray | float, frequency_hz: float) -> np.ndarray | float:
    """A timing error in ms as a phase error at the given rhythm: the same delay costs less at a slower rhythm."""
    return FULL_CYCLE_RADIANS * frequency_hz * milliseconds / MILLISECONDS_PER_SECOND


def conduction_delays_ms(connectome: Connectome, design: SweepDesign) -> np.ndarray:
    """Constant conduction delay of each connection; mm divided by m/s gives ms. Zero when delays are not modelled."""
    if design.conduction_velocity_m_per_s is None:
        return np.zeros(connectome.edge_count)
    if connectome.lengths_mm is None:
        raise ValueError(f"{connectome.name} has no tract lengths for conduction delays")
    return connectome.lengths_mm.astype(float) / design.conduction_velocity_m_per_s


def jitter_weights(connectome: Connectome, scaling: JitterScaling) -> tuple[np.ndarray, np.ndarray]:
    """Per-connection multipliers for the baseline jitter and for the agent's added jitter."""
    uniform = np.ones(connectome.edge_count)
    if scaling is JitterScaling.UNIFORM:
        return uniform, uniform
    if scaling is JitterScaling.SENSORY_PATHWAYS:
        leaves_sensory = np.isin(connectome.sources, connectome.sensory_nodes).astype(float)
        return uniform, leaves_sensory
    if connectome.lengths_mm is None:
        raise ValueError(f"{connectome.name} has no tract lengths for {scaling.value} jitter")
    lengths = connectome.lengths_mm.astype(float)
    by_length = np.sqrt(lengths / lengths.mean())
    return by_length, by_length


class SynapticDrive:
    """Input from connected populations, normalised by each population's intact in-strength.

    Fluctuating jitter is redrawn at every call, so each step sees a new timing error.
    """

    def __init__(
        self, connectome: Connectome, coupling: float, connectivity: ImpairedConnectivity, rng: np.random.Generator
    ) -> None:
        # Normalised by the total strength of all intact inputs, excitatory and inhibitory alike.
        in_strength = np.bincount(connectome.targets, weights=connectome.weights, minlength=connectome.node_count)
        self._gain = np.divide(coupling, in_strength, out=np.zeros_like(in_strength), where=in_strength > 0)
        self._connectivity = connectivity
        # Converted once here rather than at every step; float32 to float64 is exact.
        self._weights = connectivity.weights.astype(np.float64)
        self._rng = rng
        self._fluctuates = bool(np.any(connectivity.jitter_sd > 0))
        self._has_lags = bool(np.any(connectivity.fixed_lags != 0))

    def __call__(self, phases: np.ndarray, mean_field: complex, time: float) -> np.ndarray:
        c = self._connectivity
        phase_differences = phases[c.sources] - phases[c.targets]
        phase_errors = self._phase_errors()
        if phase_errors is not None:
            phase_differences = phase_differences - phase_errors
        influence = self._weights * np.sin(phase_differences)
        return self._gain * np.bincount(c.targets, weights=influence, minlength=phases.size)

    def _phase_errors(self) -> np.ndarray | None:
        """Fixed lags plus this step's jitter; None when both are zero, so no work is done for them."""
        c = self._connectivity
        if not self._fluctuates:
            return c.fixed_lags if self._has_lags else None
        jitter = c.jitter_sd * self._rng.standard_normal(c.jitter_sd.size)
        return c.fixed_lags + jitter if self._has_lags else jitter


class PhaseReferenceDrive:
    """Shared thalamocortical phase reference: its pull grows with global coherence (P5), and the
    arousal share of it is sustained independently of coherence (P7)."""

    def __init__(self, feedback: float, arousal: float) -> None:
        self._feedback = feedback
        self._arousal = arousal

    def __call__(self, phases: np.ndarray, mean_field: complex, time: float) -> np.ndarray:
        coherence = np.abs(mean_field)
        strength = self._feedback * (coherence + self._arousal * (1 - coherence))
        return strength * np.sin(np.angle(mean_field) - phases)


class SensoryDrive:
    """Periodic stimulus applied to the sensory populations only."""

    def __init__(self, is_sensory: np.ndarray, stimulus: SensoryStimulus) -> None:
        self._gain = is_sensory * stimulus.strength
        self._angular_frequency = stimulus.angular_frequency

    def __call__(self, phases: np.ndarray, mean_field: complex, time: float) -> np.ndarray:
        return self._gain * np.sin(self._angular_frequency * time - phases)


# ---------------------------------------------------------------------------
# Recording observables
# ---------------------------------------------------------------------------


class ObservableRecorder:
    """Accumulates coherence and entrainment over the measurement window."""

    def __init__(self, connectome: Connectome, is_sensory: np.ndarray, stimulus: SensoryStimulus | None) -> None:
        self._modules = connectome.modules
        self._population_count = connectome.node_count
        self._is_sensory = is_sensory
        self._stimulus = stimulus
        self._global: list[float] = []
        self._local: list[float] = []
        self._relative_to_mean_field = np.zeros(connectome.node_count, dtype=complex)
        self._sensory: list[complex] = []
        self._broadcast: list[complex] = []

    def record(self, phases: np.ndarray, mean_field: complex, time: float) -> None:
        self._global.append(float(np.abs(mean_field)))
        self._local.append(self._module_coherence(phases))
        self._relative_to_mean_field += np.exp(1j * (phases - np.angle(mean_field)))
        if self._stimulus is not None:
            relative = np.exp(1j * (phases - self._stimulus.angular_frequency * time))
            self._sensory.append(relative[self._is_sensory].mean())
            self._broadcast.append(relative[~self._is_sensory].mean())

    def measurement(self, concentration: float) -> StateMeasurement:
        coherence = np.asarray(self._global)
        return StateMeasurement(
            concentration=concentration,
            global_coherence=float(coherence.mean()),
            susceptibility=float(self._population_count * coherence.var()),
            local_coherence=float(np.mean(self._local)),
            sensory_entrainment=phase_locking_value(self._sensory),
            broadcast_entrainment=phase_locking_value(self._broadcast),
            locking_to_mean_field=float(np.abs(self._relative_to_mean_field / len(self._global)).mean()),
        )

    def _module_coherence(self, phases: np.ndarray) -> float:
        """Size-weighted mean of the order parameter computed inside each module."""
        cosines = np.bincount(self._modules, weights=np.cos(phases))
        sines = np.bincount(self._modules, weights=np.sin(phases))
        return float(np.hypot(cosines, sines).sum() / self._population_count)


def phase_locking_value(relative_phasors: list[complex]) -> float | None:
    """Modulus of the time-averaged phasor relative to the stimulus; None without a stimulus."""
    return None if not relative_phasors else float(np.abs(np.mean(relative_phasors)))


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


class PhaseNetwork:
    """One realisation of the network: quenched draws shared by every concentration in a sweep."""

    def __init__(self, connectome: Connectome, design: SweepDesign) -> None:
        self._connectome = connectome
        self._design = design
        self._rng = np.random.default_rng(design.seed)
        self._impairment = ConnectionImpairment(connectome, design, self._rng)
        self._natural_frequencies = self._rng.normal(0.0, design.dynamics.natural_frequency_spread, connectome.node_count)
        self._is_sensory = np.zeros(connectome.node_count, dtype=bool)
        self._is_sensory[connectome.sensory_nodes] = True
        self._time = 0.0

    @property
    def chance(self) -> ChanceCoherence:
        module_sizes = np.bincount(self._connectome.modules)
        return ChanceCoherence.of(self._connectome.node_count, module_sizes[module_sizes > 0])

    def hold_at(self, phases: np.ndarray, concentration: float) -> tuple[np.ndarray, StateMeasurement]:
        """Relax at a fixed concentration, then measure. Phases carry over between concentrations."""
        drives = self._drives_at(concentration)
        recorder = ObservableRecorder(self._connectome, self._is_sensory, self._design.stimulus)
        integration = self._design.integration
        for step in range(integration.relaxation_steps + integration.measurement_steps):
            mean_field = np.exp(1j * phases).mean()
            phases = self._euler_maruyama_step(phases, mean_field, drives)
            if step >= integration.relaxation_steps:
                recorder.record(phases, mean_field, self._time)
        return phases, recorder.measurement(concentration)

    def _drives_at(self, concentration: float) -> list[PhaseDrive]:
        dynamics = self._design.dynamics
        drives: list[PhaseDrive] = [
            SynapticDrive(self._connectome, dynamics.synaptic_coupling, self._impairment.at(concentration), self._rng),
            PhaseReferenceDrive(dynamics.reference_feedback, self._arousal_at(concentration)),
        ]
        if self._design.stimulus is not None:
            drives.append(SensoryDrive(self._is_sensory, self._design.stimulus))
        return drives

    def _arousal_at(self, concentration: float) -> float:
        return dpc.sustained_arousal(self._design.dynamics.arousal_level, self._design.agent, concentration)

    def _euler_maruyama_step(self, phases: np.ndarray, mean_field: complex, drives: Sequence[PhaseDrive]) -> np.ndarray:
        time_step = self._design.integration.time_step
        velocity = self._natural_frequencies + sum(drive(phases, mean_field, self._time) for drive in drives)
        noise = np.sqrt(2 * self._design.dynamics.noise_intensity * time_step) * self._rng.standard_normal(phases.size)
        self._time += time_step
        return phases + time_step * velocity + noise


def run_induction_emergence(connectome: Connectome, design: SweepDesign) -> InductionEmergenceRecord:
    """Start fully synchronised (awake), raise the concentration step by step, then lower it again."""
    network = PhaseNetwork(connectome, design)
    ascending = design.grid.ascending()
    induction, phases = follow_concentrations(network, np.zeros(connectome.node_count), ascending)
    emergence, _ = follow_concentrations(network, phases, list(reversed(ascending)))
    return InductionEmergenceRecord(
        awake_coherence=induction[0].global_coherence,
        quorum_fraction=design.quorum_fraction,
        chance=network.chance,
        induction=tuple(induction),
        emergence=tuple(emergence),
    )


def follow_concentrations(
    network: PhaseNetwork, phases: np.ndarray, concentrations: Sequence[float]
) -> tuple[list[StateMeasurement], np.ndarray]:
    measurements = []
    for concentration in concentrations:
        phases, measurement = network.hold_at(phases, concentration)
        measurements.append(measurement)
    return measurements, phases


# ---------------------------------------------------------------------------
# Analysis of a sweep (pure functions)
# ---------------------------------------------------------------------------


def loss_concentration(record: InductionEmergenceRecord) -> float | None:
    return dpc.loss_concentration(record.induction, record.is_conscious)


def recovery_concentration(record: InductionEmergenceRecord) -> float | None:
    return dpc.recovery_concentration(record.emergence, record.is_conscious)


def hysteresis_width(record: InductionEmergenceRecord) -> float | None:
    return dpc.hysteresis_width(loss_concentration(record), recovery_concentration(record))


def susceptibility_peak(record: InductionEmergenceRecord) -> StateMeasurement:
    return max(record.induction, key=lambda point: point.susceptibility)


def susceptibility_surge(record: InductionEmergenceRecord) -> float:
    """Peak susceptibility during induction relative to its awake value."""
    awake = max(record.induction[0].susceptibility, np.finfo(float).tiny)
    return susceptibility_peak(record).susceptibility / awake


def above_chance(coherence: float, chance_level: float) -> float:
    """Coherence rescaled so that 0 is the level of random phases and 1 is full synchrony."""
    return (coherence - chance_level) / (1 - chance_level)


def local_global_dissociation(record: InductionEmergenceRecord) -> float | None:
    """Above-chance local minus above-chance global coherence at the first unconscious point."""
    point = record.first_unconscious
    if point is None:
        return None
    local = above_chance(point.local_coherence, record.chance.local_level)
    global_ = above_chance(point.global_coherence, record.chance.global_level)
    return local - global_


def broadcast_ratio(point: StateMeasurement) -> float | None:
    """How far a stimulus reaches beyond the stimulated populations (rest over sensory entrainment)."""
    if point.sensory_entrainment is None or point.broadcast_entrainment is None or point.sensory_entrainment == 0:
        return None
    return point.broadcast_entrainment / point.sensory_entrainment
