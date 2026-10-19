"""Test of the congestion account of induction-phase excitation (Section 5.1).

The congestion account proposes that, as connections fail, the same sensory input is forced
through fewer pathways, raising activity on the survivors before the network collapses.
Neurons do not queue or retransmit signals, so a failed connection simply removes input.
Congestion therefore requires something that keeps the load up on the surviving pathways.
The candidate tested here is homeostatic inhibitory synaptic plasticity (ISP), which lowers
local inhibition when excitatory activity falls below a target (Vogels et al., 2011;
Abeysuriya et al., 2018).

Each brain region is a Wilson-Cowan pair of excitatory (E) and inhibitory (I) populations
(Wilson & Cowan, 1972), in the formulation and with the local parameters of Abeysuriya et al.
(2018, Eqs 1-4, Table 1):

    τe dE_k/dt = −E_k + S(c_ee E_k + c_ie,k I_k + P_k + ξ + C Σ_j W_jk m_jk E_j(t − τ_jk))
    τi dI_k/dt = −I_k + S(c_ei E_k + ξ)
    τisp dc_ie,k/dt = −I_k (E_k − ρ)      (c_ie is negative: activity above ρ strengthens inhibition)
    S(x) = 1 / (1 + exp(−(x − μ) / σ))

m_jk is 1 if the long-range connection transmits and 0 if the agent has failed it. Delays
τ_jk are tract lengths divided by the measured conduction velocity. Global synchrony is the
Golomb-Rinzel index χ, the square root of var(mean E) / mean(var E_k) (Golomb & Rinzel, 1993).
Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np

from connectomes import Connectome
from dpc_simulator import AnaestheticAgent, ConcentrationGrid

MILLISECONDS_PER_SECOND = 1000.0


@dataclass(frozen=True)
class LocalCircuit:
    """Local parameters of each Wilson-Cowan unit (Abeysuriya et al., 2018, Table 1)."""

    excitatory_to_excitatory: float = 3.5
    excitatory_to_inhibitory: float = 3.75
    initial_inhibitory_to_excitatory: float = -2.5
    firing_threshold: float = 1.0
    threshold_variability: float = 0.25
    constant_input: float = 0.31
    excitatory_time_constant_s: float = 0.01
    inhibitory_time_constant_s: float = 0.02
    target_excitatory_activity: float = 0.15
    # Standard deviation of the noise added at each step (Abeysuriya et al., 2018, Methods).
    noise_sd: float = 0.01


class Compensation(Enum):
    """How fast homeostatic plasticity rebalances inhibition during induction."""

    NONE = "none"
    # The slowest learning time constant used by Abeysuriya et al. (2018); biological ISP is slower.
    SLOW = "slow"
    # Hypothetical: fast enough to compensate within each concentration step.
    FAST = "fast"


COMPENSATION_TIME_CONSTANT_S = {Compensation.SLOW: 20.0, Compensation.FAST: 0.05}
# The first half of each concentration step is discarded as the transient after the change.
TRANSIENT_FRACTION = 0.5
# A burst is an excursion of network-average activity more than this many awake standard
# deviations above the awake mean; the threshold is fixed from the awake state for every step.
BURST_THRESHOLD_SDS = 2.0
# Time constant used to balance inhibition at the awake state before every sweep.
BALANCING_TIME_CONSTANT_S = 0.05


@dataclass(frozen=True)
class CongestionDesign:
    agent: AnaestheticAgent
    circuit: LocalCircuit
    compensation: Compensation
    global_coupling: float
    sensory_extra_input: float
    conduction_velocity_m_per_s: float
    grid: ConcentrationGrid
    time_step_s: float
    balancing_s: float
    hold_s: float
    seed: int


@dataclass(frozen=True)
class ActiveConnections:
    """Long-range connections that still transmit at one concentration, with their delays in steps."""

    sources: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    delay_steps: np.ndarray


@dataclass(frozen=True)
class CongestionMeasurement:
    concentration: float
    hub_activity: float
    mean_activity: float
    synchrony: float
    # Coefficient of variation of network-average activity: how clustered in time activity is.
    burstiness: float
    # Mean time between bursts; None when no burst occurred in the measurement window.
    inter_burst_interval_s: float | None


class WilsonCowanNetwork:
    """One realisation: quenched connection failures, delay buffer and plastic inhibition."""

    def __init__(self, connectome: Connectome, design: CongestionDesign) -> None:
        if connectome.lengths_mm is None:
            raise ValueError(f"{connectome.name} has no tract lengths for conduction delays")
        self._design = design
        self._circuit = design.circuit
        self._rng = np.random.default_rng(design.seed)
        self._sources, self._targets = connectome.sources, connectome.targets
        self._weights = connectome.weights / connectome.weights.max()
        delays_s = connectome.lengths_mm.astype(float) / design.conduction_velocity_m_per_s / MILLISECONDS_PER_SECOND
        self._delay_steps = np.maximum(1, np.round(delays_s / design.time_step_s).astype(int))
        self._failure_draws = self._rng.random(connectome.edge_count)
        node_count = connectome.node_count
        self._input = np.full(node_count, self._circuit.constant_input)
        self._input[connectome.sensory_nodes] += design.sensory_extra_input
        strength = np.bincount(self._targets, weights=self._weights, minlength=node_count)
        self._is_hub = strength >= np.quantile(strength, HUB_QUANTILE)
        self._history = np.zeros((self._delay_steps.max() + 1, node_count))
        self._cursor = 0
        self._excitatory = np.zeros(node_count)
        self._inhibitory = np.zeros(node_count)
        self._inhibitory_coupling = np.full(node_count, self._circuit.initial_inhibitory_to_excitatory)
        self._burst_threshold: float | None = None

    def balance_awake_state(self) -> None:
        """Let fast plasticity set each region's inhibition for the awake state, as in every condition."""
        active = self._active_at(0.0)
        for _ in range(self._steps(self._design.balancing_s)):
            self._step(active, BALANCING_TIME_CONSTANT_S)

    def hold_at(self, concentration: float) -> CongestionMeasurement:
        plasticity_s = COMPENSATION_TIME_CONSTANT_S.get(self._design.compensation)
        trace = self._record(concentration, self._design.hold_s, plasticity_s)
        measured = trace[int(len(trace) * TRANSIENT_FRACTION) :]
        population_variance = measured.var(axis=0).mean()
        synchrony = measured.mean(axis=1).var() / population_variance if population_variance > 0 else 0.0
        network_activity = measured.mean(axis=1)
        if self._burst_threshold is None:
            # The first step held is the awake state; its statistics define a burst for every later step.
            self._burst_threshold = float(network_activity.mean() + BURST_THRESHOLD_SDS * network_activity.std())
        return CongestionMeasurement(
            concentration=concentration,
            hub_activity=float(measured[:, self._is_hub].mean()),
            mean_activity=float(measured.mean()),
            synchrony=float(np.sqrt(synchrony)),
            burstiness=coefficient_of_variation(network_activity),
            inter_burst_interval_s=self._inter_burst_interval_s(network_activity),
        )

    def _inter_burst_interval_s(self, network_activity: np.ndarray) -> float | None:
        above = network_activity > self._burst_threshold
        burst_onsets = int(np.sum(above[1:] & ~above[:-1]))
        if burst_onsets == 0:
            return None
        return network_activity.size * self._design.time_step_s / burst_onsets

    def _steps(self, duration_s: float) -> int:
        return int(round(duration_s / self._design.time_step_s))

    def _active_at(self, concentration: float) -> ActiveConnections:
        transmits = self._failure_draws >= self._design.agent.transmission_failure(concentration)
        return ActiveConnections(
            self._sources[transmits], self._targets[transmits], self._weights[transmits], self._delay_steps[transmits]
        )

    def _record(self, concentration: float, duration_s: float, plasticity_s: float | None) -> np.ndarray:
        active = self._active_at(concentration)
        trace = np.empty((self._steps(duration_s), self._excitatory.size))
        for step in range(trace.shape[0]):
            self._step(active, plasticity_s)
            trace[step] = self._excitatory
        return trace

    def _step(self, active: ActiveConnections, plasticity_s: float | None) -> None:
        c, dt = self._circuit, self._design.time_step_s
        delayed = self._history[(self._cursor - active.delay_steps) % self._history.shape[0], active.sources]
        long_range = np.bincount(active.targets, weights=active.weights * delayed, minlength=self._excitatory.size)
        noise_e, noise_i = c.noise_sd * self._rng.standard_normal((2, self._excitatory.size))
        drive_e = (
            c.excitatory_to_excitatory * self._excitatory
            + self._inhibitory_coupling * self._inhibitory
            + self._input
            + noise_e
            + self._design.global_coupling * long_range
        )
        drive_i = c.excitatory_to_inhibitory * self._excitatory + noise_i
        excitatory = self._excitatory + dt / c.excitatory_time_constant_s * (-self._excitatory + self._sigmoid(drive_e))
        inhibitory = self._inhibitory + dt / c.inhibitory_time_constant_s * (-self._inhibitory + self._sigmoid(drive_i))
        if plasticity_s is not None:
            # Abeysuriya et al. (2018), Eq 4, with the sign written so that, as their text states,
            # activity above target strengthens inhibition: c_ie is negative, so it becomes more negative.
            self._inhibitory_coupling -= dt / plasticity_s * self._inhibitory * (self._excitatory - c.target_excitatory_activity)
        self._excitatory, self._inhibitory = excitatory, inhibitory
        self._cursor = (self._cursor + 1) % self._history.shape[0]
        self._history[self._cursor] = self._excitatory

    def _sigmoid(self, drive: np.ndarray) -> np.ndarray:
        c = self._circuit
        return 1 / (1 + np.exp(-(drive - c.firing_threshold) / c.threshold_variability))


# The top decile of regions by connection strength are treated as hubs.
HUB_QUANTILE = 0.9


def coefficient_of_variation(values: np.ndarray) -> float:
    mean = float(values.mean())
    return float(values.std() / mean) if mean > 0 else 0.0


@dataclass(frozen=True)
class InductionRecord:
    measurements: tuple[CongestionMeasurement, ...]
    collapse_fraction: float

    @property
    def awake(self) -> CongestionMeasurement:
        return self.measurements[0]

    @property
    def collapse_concentration(self) -> float | None:
        """First concentration from which global synchrony stays below the collapse fraction of its awake value at
        every later step: the network has broken apart, rather than dipped in one noisy measurement window."""
        threshold = self.collapse_fraction * self.awake.synchrony
        collapse = None
        for measurement in reversed(self.measurements[1:]):
            if measurement.synchrony >= threshold:
                break
            collapse = measurement.concentration
        return collapse

    @property
    def before_collapse(self) -> tuple[CongestionMeasurement, ...]:
        collapse = self.collapse_concentration
        return tuple(m for m in self.measurements if collapse is None or m.concentration < collapse)

    @property
    def peak_hub_activity_ratio(self) -> float:
        """Highest hub activity before collapse, relative to the awake value."""
        return max(m.hub_activity for m in self.before_collapse) / self.awake.hub_activity

    @property
    def surge(self) -> CongestionMeasurement:
        """The step with the highest global synchrony before collapse."""
        return max(self.before_collapse, key=lambda m: m.synchrony)

    @property
    def synchrony_surge(self) -> float:
        """Highest global synchrony before collapse, relative to the awake value."""
        return self.surge.synchrony / self.awake.synchrony

    @property
    def burstiness_rise_after_surge(self) -> float:
        """Highest burstiness at or beyond the surge, relative to the awake value."""
        after = [m.burstiness for m in self.measurements if m.concentration >= self.surge.concentration]
        return max(after) / self.awake.burstiness if self.awake.burstiness > 0 else 0.0

    @property
    def burst_gaps_lengthen(self) -> bool | None:
        """Whether bursts are further apart at the deepest step that still has them than at the surge.

        None when the surge has no bursts or no deeper step does, so the comparison is undefined.
        """
        surge_interval = self.surge.inter_burst_interval_s
        deeper = [m for m in self.measurements if m.concentration > self.surge.concentration and m.inter_burst_interval_s is not None]
        if surge_interval is None or not deeper:
            return None
        return deeper[-1].inter_burst_interval_s > surge_interval


def run_induction(connectome: Connectome, design: CongestionDesign, collapse_fraction: float) -> InductionRecord:
    network = WilsonCowanNetwork(connectome, design)
    network.balance_awake_state()
    return InductionRecord(tuple(network.hold_at(c) for c in design.grid.ascending()), collapse_fraction)
