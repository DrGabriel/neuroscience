"""DPC readout of the phase-oscillator model: which connections count in a cycle, and whether they form a quorum.

The phase model's own quorum criterion (phase_dynamics.InductionEmergenceRecord.is_conscious) is global coherence at
least half its awake value. That is a statement about oscillator synchrony; it uses neither the integration window
of P2 nor the connected component of P3. This module reads the same simulation the way the postulates are worded,
without changing the dynamics: it only looks at quantities the model already computes.

Timing error of a connection (P2), primary reading. At a sampled step, connection j -> i, if it transmits
(m_ji = 1), carries a signal whose timing error relative to the shared rhythm is, in radians of the reference cycle,

    δ_ji = wrap(θ_j − ψ) − α_ji

    θ_j     phase of the sending population at the start of the step
    ψ       phase of the network's mean field at that moment, the shared rhythm (P5's reference)
    α_ji    the connection's phase error in that same step: its fixed conduction lag (zero unless delays are
            modelled) plus its current jitter draw, exactly the α_ji that enters the coupling sin(θ_j − θ_i − α_ji)
    wrap    maps an angle to [−π, π): a population can lead or lag the rhythm by at most half a cycle

The population's offset from the rhythm is circular, but α_ji is not wrapped: a signal one whole cycle late is late,
not on time for the next cycle, as in the percolation model and in P2 ("signals outside the window are not
integrated"). The connection COUNTS in that cycle when it transmits and |δ_ji| ≤ W/2, with W the integration window
converted to phase at the reference rate in force at that concentration (2π f(c) W).

Secondary readings, recorded beside it:
    receiver phase   wrap(θ_j − θ_i − α_ji) within ±π f W: timing measured at the receiver, everything wrapped, the
                     quantity whose sine the coupling term takes (communication through coherence). Because α_ji is
                     wrapped too, an error far beyond a cycle leaves a chance floor of W·f (12% at 3 ms and 40 Hz) of
                     transmitting connections counting.
    jitter only      δ_ji = −α_ji: the populations' offsets from the rhythm are ignored, so the reading is static bond
                     percolation on the model's own timing draws. Where the primary reading departs from it, the
                     oscillator dynamics, not the timing draws, decide which connections count.
P2's wording ("relative to a shared phase reference") and Section 4.1 ("relative to the phase reference") favour the
shared rhythm, which is therefore primary. The analytic static prediction of Section 4.1, π(c) = (1 − p(c)) erf(W /
(2√2 σ_eff)), is recorded for each concentration, generalised to each connection's own timing error and lag.

Quorum (P3). In each sampled cycle the counting connections are taken as undirected links, as the percolation model
does, and the share of populations in their largest connected component is computed (a population with no counting
connection is a component of one). Quorum holds in that cycle when the share is at least q*. The largest strongly
connected component of the directed counting connections is recorded as a secondary measure; it is meaningful only on
connectomes whose wiring is directed.

Pair rules (Appendix C.13). Taking every directed arc as its own connection, as above, gives two populations linked
both ways two chances to be joined in a cycle, and every human fibre is stored as two arcs. The giant component is
therefore also read under the three pair rules of connection_pairs, with the same on-time arcs: one timing draw per
anatomical connection (primary in C.13), both directions on time, and either direction on time (the reading above).

Cycles. The model's time is dimensionless: only timing errors are converted from milliseconds to phase, so nothing in
the model fixes how many time units one 25 ms cycle of the 40 Hz rhythm lasts. One cycle is therefore sampled per
ReadoutSettings.cycle_interval, set by the study to the jitter correlation time τ, the time over which a
connection's timing error renews, so that successive cycles see largely fresh errors. If one time unit is read as
one reference cycle (which puts the natural-frequency spread of 0.5 at 0.5 / 2π × 40 Hz, about 3 Hz), this is also
one sample per cycle.

Summary per concentration: the mean share of the giant component across cycles and the number of cycles holding
quorum. Quorum holds at a concentration when it holds in at least half of its cycles.

Synchronisation or percolation. For each concentration the coupling the network still receives is also recorded:
the synaptic effective coupling K Σ_transmitting |w| exp(−s²/2) / Σ_all |w|, with s each connection's phase-error SD
(the mean-field factor by which Gaussian timing error weakens sin coupling, Section 4.5; a fixed lag only shifts the
phase and is ignored), and the coherence-dependent strength of the reference, λ (1 − A(c)). They are compared with
Kuramoto's critical coupling for the natural-frequency spread and noise used (kuramoto_critical_coupling).

Dependencies: numpy, scipy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from fractions import Fraction
from typing import Mapping, Sequence

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.special import erf, erfcx

import comparisons
import dpc_simulator as dpc
from connection_pairs import AnatomicalConnections, PairRule
import phase_dynamics as dynamics
from connectomes import Connectome

# Quorum holds at a concentration when it holds in at least this share of the sampled cycles.
CYCLE_MAJORITY = Fraction(1, 2)
HALF = 0.5
LEARNING_NOT_READ = "the DPC readout does not include learned arrival offsets (P4b); run it without arrival learning"


class TimingReference(Enum):
    """What a signal's arrival is timed against."""

    # P2 as worded: the shared phase reference, the phase of the network's mean rhythm.
    SHARED_RHYTHM = "shared rhythm"
    # Communication through coherence: the receiving population's own phase, everything wrapped.
    RECEIVER_PHASE = "receiving population's own phase"
    # Static percolation on the model's timing draws: the populations' offsets from the rhythm are ignored.
    JITTER_ONLY = "timing draws alone"


class ComponentKind(StrEnum):
    """How counting connections join populations; the values are scipy's names for the two kinds of component."""

    UNDIRECTED = "weak"
    STRONGLY_CONNECTED = "strong"


@dataclass(frozen=True)
class ReadoutSettings:
    integration_window_ms: float
    quorum_fraction: float
    # Model time between sampled cycles.
    cycle_interval: float

    def interval_steps(self, time_step: float) -> int:
        return max(1, round(self.cycle_interval / time_step))

    def half_window(self, frequency_hz: float) -> float:
        """W / 2 as phase at the reference rate in force, π f W."""
        return HALF * float(dynamics.milliseconds_to_radians(self.integration_window_ms, frequency_hz))


def kuramoto_critical_coupling(frequency_spread: float, noise_intensity: float) -> float:
    """Critical coupling of the all-to-all Kuramoto model with Gaussian natural frequencies and phase noise.

    K_c = 2 / ∫ g(ω) D / (D² + ω²) dω (Strogatz and Mirollo, 1991), with g Gaussian of SD σ = frequency_spread and D
    the noise intensity of dθ = ... + sqrt(2 D dt) ξ. For Gaussian g the integral is the Voigt profile at zero,
    π erfcx(D / (σ√2)) / (σ√(2π)), so K_c = 2σ√(2π) / (π erfcx(D / (σ√2))); without noise it is Kuramoto's
    σ √(8 / π) (Kuramoto, 1984). It assumes all-to-all coupling, infinitely many oscillators and unimodal frequencies;
    the connectomes are sparse and finite, so it is a reference value, not the model's own threshold.
    """
    scaled_noise = noise_intensity / (frequency_spread * math.sqrt(2))
    return 2 * frequency_spread * math.sqrt(2 * math.pi) / (math.pi * float(erfcx(scaled_noise)))


# ---------------------------------------------------------------------------
# One cycle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CountingGraph:
    """The connections that count in one cycle, over every population of the network."""

    population_count: int
    sources: np.ndarray
    targets: np.ndarray

    def largest_component_share(self, kind: ComponentKind) -> float:
        """Share of populations in the largest component; a population without counting connections stands alone."""
        if self.sources.size == 0:
            return 1 / self.population_count
        links = np.ones(self.sources.size, dtype=np.int8)
        graph = coo_matrix((links, (self.sources, self.targets)), shape=(self.population_count,) * 2).tocsr()
        _, labels = connected_components(graph, directed=True, connection=kind.value)
        return int(np.bincount(labels).max()) / self.population_count


@dataclass(frozen=True)
class CycleSnapshot:
    """What the readout sees at one sampled step: the transmitting connections and the state they act on."""

    phases: np.ndarray
    mean_field: complex
    sources: np.ndarray
    targets: np.ndarray
    # α_ji of each transmitting connection in this step, unwrapped.
    phase_errors: np.ndarray
    # Every connection of the connectome, transmitting or not.
    connection_count: int
    # Index in the connectome of each transmitting connection, and the connectome's anatomical connections; the pair
    # rules are read only when both are given.
    edges: np.ndarray | None = None
    anatomical: AnatomicalConnections | None = None

    def counting_graph(self, counts: np.ndarray) -> CountingGraph:
        return CountingGraph(self.phases.size, self.sources[counts], self.targets[counts])

    def on_time_arcs(self, counts: np.ndarray) -> np.ndarray:
        """Over every arc of the connectome: whether it transmits and counts in this cycle."""
        arcs = np.zeros(self.connection_count, dtype=bool)
        arcs[self.edges[counts]] = True
        return arcs


def wrapped_phase(angles: np.ndarray) -> np.ndarray:
    """Angles mapped to [−π, π)."""
    return (angles + np.pi) % dynamics.FULL_CYCLE_RADIANS - np.pi


def arrival_timing_errors(snapshot: CycleSnapshot, reference: TimingReference) -> np.ndarray:
    """δ_ji of each transmitting connection, in radians of the reference cycle (module docstring)."""
    if reference is TimingReference.JITTER_ONLY:
        return -snapshot.phase_errors
    sending = snapshot.phases[snapshot.sources]
    if reference is TimingReference.RECEIVER_PHASE:
        return wrapped_phase(sending - snapshot.phases[snapshot.targets] - snapshot.phase_errors)
    return wrapped_phase(sending - np.angle(snapshot.mean_field)) - snapshot.phase_errors


def counting_connections(timing_errors: np.ndarray, half_window: float) -> np.ndarray:
    """P2: a transmitting connection counts when its signal arrives within half the window either side."""
    return np.abs(timing_errors) <= half_window


@dataclass(frozen=True)
class PairRuleCycle:
    """One cycle read under one pair rule, timed against the shared rhythm."""

    giant_share: float
    # Share of the anatomical connections that count.
    counting_share: float


@dataclass(frozen=True)
class CycleReadout:
    giant_share: float
    strongly_connected_share: float
    receiver_phase_giant_share: float
    jitter_only_giant_share: float
    # Share of all connections of the connectome that count, timed against the shared rhythm.
    counting_share: float
    pair_rules: Mapping[PairRule, PairRuleCycle] = field(default_factory=dict)


def read_pair_rule(anatomical: AnatomicalConnections, on_time_arcs: np.ndarray, rule: PairRule) -> PairRuleCycle:
    counts = anatomical.counting(on_time_arcs, rule)
    graph = CountingGraph(anatomical.population_count, anatomical.lower[counts], anatomical.higher[counts])
    return PairRuleCycle(graph.largest_component_share(ComponentKind.UNDIRECTED), int(counts.sum()) / anatomical.count)


def read_pair_rules(snapshot: CycleSnapshot, on_time: np.ndarray) -> dict[PairRule, PairRuleCycle]:
    """The giant component under every pair rule, from the connections on time for the shared rhythm."""
    if snapshot.anatomical is None or snapshot.edges is None:
        return {}
    arcs = snapshot.on_time_arcs(on_time)
    return {rule: read_pair_rule(snapshot.anatomical, arcs, rule) for rule in PairRule}


def giant_share_for(snapshot: CycleSnapshot, half_window: float, reference: TimingReference) -> float:
    counts = counting_connections(arrival_timing_errors(snapshot, reference), half_window)
    return snapshot.counting_graph(counts).largest_component_share(ComponentKind.UNDIRECTED)


def read_cycle(snapshot: CycleSnapshot, half_window: float) -> CycleReadout:
    on_time = counting_connections(arrival_timing_errors(snapshot, TimingReference.SHARED_RHYTHM), half_window)
    counting = snapshot.counting_graph(on_time)
    return CycleReadout(
        giant_share=counting.largest_component_share(ComponentKind.UNDIRECTED),
        strongly_connected_share=counting.largest_component_share(ComponentKind.STRONGLY_CONNECTED),
        receiver_phase_giant_share=giant_share_for(snapshot, half_window, TimingReference.RECEIVER_PHASE),
        jitter_only_giant_share=giant_share_for(snapshot, half_window, TimingReference.JITTER_ONLY),
        counting_share=int(on_time.sum()) / snapshot.connection_count,
        pair_rules=read_pair_rules(snapshot, on_time),
    )


# ---------------------------------------------------------------------------
# What each concentration leaves the network: static prediction and coupling
# ---------------------------------------------------------------------------


def within_window_probability(lags: np.ndarray, jitter_sd: np.ndarray, half_window: float) -> np.ndarray:
    """P(|lag + N(0, sd)| ≤ W/2) for each connection; an exact indicator where the timing error has no spread."""
    spread = np.where(jitter_sd > 0, jitter_sd, 1.0) * math.sqrt(2)
    gaussian = HALF * (erf((half_window - lags) / spread) - erf((-half_window - lags) / spread))
    return np.where(jitter_sd > 0, gaussian, (np.abs(lags) <= half_window).astype(float))


def static_counting_share(connectivity: dynamics.ImpairedConnectivity, connection_count: int, half_window: float) -> float:
    """Section 4.1's π(c) = (1 − p(c)) erf(W / (2√2 σ_eff)), per connection, as a share of all connections."""
    return float(within_window_probability(connectivity.fixed_lags, connectivity.jitter_sd, half_window).sum()) / connection_count


def effective_coupling(connectivity: dynamics.ImpairedConnectivity, total_weight: float, coupling: float) -> float:
    """K Σ_transmitting |w| exp(−s²/2) / Σ_all |w|: the mean-field coupling left after failures and timing error."""
    retained = np.abs(connectivity.weights.astype(float)) * np.exp(-HALF * connectivity.jitter_sd**2)
    return coupling * float(retained.sum()) / total_weight


@dataclass(frozen=True)
class ConnectionBudget:
    static_counting_share: float
    effective_coupling: float
    # λ (1 − A(c)): the part of the reference that depends on coherence, Kuramoto coupling of this strength.
    reference_coupling: float


# ---------------------------------------------------------------------------
# One concentration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentSummary:
    """A giant-component share across the cycles held at one concentration."""

    mean_share: float
    cycles_with_quorum: int
    cycles: int

    @classmethod
    def of(cls, shares: Sequence[float], quorum_fraction: float) -> ComponentSummary:
        with_quorum = sum(comparisons.at_most(quorum_fraction, share) for share in shares)
        return cls(float(np.mean(shares)), with_quorum, len(shares))

    @property
    def quorum_cycle_share(self) -> float:
        return self.cycles_with_quorum / self.cycles

    @property
    def holds_quorum(self) -> bool:
        return comparisons.at_least_share(self.cycles_with_quorum, self.cycles, CYCLE_MAJORITY)


@dataclass(frozen=True)
class PairRuleSummary:
    """One pair rule across the cycles held at one concentration."""

    component: ComponentSummary
    # Mean share of the anatomical connections that count.
    counting_share: float

    @classmethod
    def of(cls, cycles: Sequence[PairRuleCycle], quorum_fraction: float) -> PairRuleSummary:
        shares = [cycle.giant_share for cycle in cycles]
        return cls(ComponentSummary.of(shares, quorum_fraction), float(np.mean([cycle.counting_share for cycle in cycles])))


@dataclass(frozen=True)
class FluctuationMeasurement:
    """Fluctuations of global coherence R over the measurement window.

    independent_susceptibility is what N var(R) would be if the populations' phases were drawn independently from
    the distribution observed, with the same mean coherence: (1 + ⟨cos 2(θ − ψ)⟩) / 2 − ⟨R⟩², the variance of one
    population's projection on the mean rhythm. Their ratio is about 1 + (N − 1) times the mean correlation between
    populations' fluctuations: it separates collective fluctuations from the rise of N var(R) that any fall in
    coherence brings. Valid while ⟨R⟩ is well above chance (1 / √N).
    """

    susceptibility: float
    independent_susceptibility: float
    # Correlation of R with itself one sampled cycle later.
    coherence_autocorrelation: float | None

    @property
    def susceptibility_excess(self) -> float | None:
        return None if self.independent_susceptibility <= 0 else self.susceptibility / self.independent_susceptibility


@dataclass(frozen=True)
class ConcentrationReadout:
    concentration: float
    undirected: ComponentSummary
    strongly_connected: ComponentSummary
    receiver_phase: ComponentSummary
    jitter_only: ComponentSummary
    counting_share: float
    budget: ConnectionBudget
    fluctuations: FluctuationMeasurement
    pair_rules: Mapping[PairRule, PairRuleSummary] = field(default_factory=dict)

    @property
    def holds_quorum(self) -> bool:
        """P3 in the primary reading: undirected giant component of connections on time for the shared rhythm."""
        return self.undirected.holds_quorum


# ---------------------------------------------------------------------------
# Observing the simulation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CycleSampling:
    """How cycles are read at one concentration."""

    half_window: float
    interval_steps: int
    # Every connection of the connectome, transmitting or not.
    connection_count: int
    anatomical: AnatomicalConnections | None = None


class CycleRecorder:
    """Reads one cycle every interval_steps steps of the measurement window."""

    def __init__(self, drive: dynamics.SynapticDrive, sampling: CycleSampling) -> None:
        self._drive = drive
        self._sampling = sampling
        self._steps_seen = 0
        self.cycles: list[CycleReadout] = []

    def observe(self, phases: np.ndarray, mean_field: complex) -> None:
        if self._steps_seen % self._sampling.interval_steps == 0:
            self.cycles.append(read_cycle(self._snapshot(phases, mean_field), self._sampling.half_window))
        self._steps_seen += 1

    def _snapshot(self, phases: np.ndarray, mean_field: complex) -> CycleSnapshot:
        c = self._drive.connectivity
        sampling = self._sampling
        return CycleSnapshot(
            phases, mean_field, c.sources, c.targets, self._drive.latest_phase_errors, sampling.connection_count, c.edges, sampling.anatomical
        )


def independent_phase_susceptibility(mean_coherence: float, mean_second_harmonic: float) -> float:
    return HALF * (1 + mean_second_harmonic) - mean_coherence**2


def lagged_autocorrelation(series: np.ndarray, lag: int) -> float | None:
    """Pearson correlation of the series with itself lag samples later; None when undefined."""
    if series.size <= lag + 1:
        return None
    earlier, later = series[:-lag], series[lag:]
    if np.std(earlier) == 0 or np.std(later) == 0:
        return None
    return float(np.corrcoef(earlier, later)[0, 1])


class FluctuationRecorder:
    """Records global coherence and its second harmonic at every step of the measurement window."""

    def __init__(self, population_count: int, lag_steps: int) -> None:
        self._population_count = population_count
        self._lag_steps = lag_steps
        self._coherence: list[float] = []
        self._second_harmonic: list[float] = []

    def observe(self, phases: np.ndarray, mean_field: complex) -> None:
        self._coherence.append(float(np.abs(mean_field)))
        self._second_harmonic.append(float(np.cos(2 * (phases - np.angle(mean_field))).mean()))

    def measurement(self) -> FluctuationMeasurement:
        coherence = np.asarray(self._coherence)
        return FluctuationMeasurement(
            susceptibility=float(self._population_count * coherence.var()),
            independent_susceptibility=independent_phase_susceptibility(float(coherence.mean()), float(np.mean(self._second_harmonic))),
            coherence_autocorrelation=lagged_autocorrelation(coherence, self._lag_steps),
        )


@dataclass(frozen=True)
class ConcentrationObservers:
    concentration: float
    budget: ConnectionBudget
    cycles: CycleRecorder
    fluctuations: FluctuationRecorder

    def readout(self, quorum_fraction: float) -> ConcentrationReadout:
        cycles = self.cycles.cycles

        def summary(share_of: str) -> ComponentSummary:
            return ComponentSummary.of([getattr(c, share_of) for c in cycles], quorum_fraction)

        rules = cycles[0].pair_rules if cycles else {}

        return ConcentrationReadout(
            concentration=self.concentration,
            undirected=summary("giant_share"),
            strongly_connected=summary("strongly_connected_share"),
            receiver_phase=summary("receiver_phase_giant_share"),
            jitter_only=summary("jitter_only_giant_share"),
            counting_share=float(np.mean([c.counting_share for c in cycles])),
            budget=self.budget,
            fluctuations=self.fluctuations.measurement(),
            pair_rules={rule: PairRuleSummary.of([c.pair_rules[rule] for c in cycles], quorum_fraction) for rule in rules},
        )


class DpcReadoutNetwork(dynamics.PhaseNetwork):
    """The phase network, with the same draws and dynamics, read out cycle by cycle as P2 and P3 state."""

    def __init__(self, connectome: Connectome, design: dynamics.SweepDesign, settings: ReadoutSettings) -> None:
        if design.dynamics.arrival_learning_time is not None:
            raise ValueError(LEARNING_NOT_READ)
        super().__init__(connectome, design)
        self._settings = settings
        self._total_weight = float(np.abs(connectome.weights.astype(float)).sum())
        self._anatomical = AnatomicalConnections.of(connectome)
        self._observed: list[ConcentrationObservers] = []

    def _step_observers(self, concentration: float, drives: Sequence[dynamics.PhaseDrive]) -> Sequence[dynamics.StepObserver]:
        drive = next(d for d in drives if isinstance(d, dynamics.SynapticDrive))
        interval = self._settings.interval_steps(self._design.integration.time_step)
        half_window = self._settings.half_window(dynamics.reference_frequency_hz(self._design.dynamics, self._design.agent, concentration))
        cycles = CycleRecorder(drive, CycleSampling(half_window, interval, self._connectome.edge_count, self._anatomical))
        observers = ConcentrationObservers(
            concentration, self._budget(concentration, drive, half_window), cycles, FluctuationRecorder(self._connectome.node_count, interval)
        )
        self._observed.append(observers)
        return observers.cycles, observers.fluctuations

    def _budget(self, concentration: float, drive: dynamics.SynapticDrive, half_window: float) -> ConnectionBudget:
        connectivity, dynamics_ = drive.connectivity, self._design.dynamics
        return ConnectionBudget(
            static_counting_share=static_counting_share(connectivity, self._connectome.edge_count, half_window),
            effective_coupling=effective_coupling(connectivity, self._total_weight, dynamics_.synaptic_coupling),
            reference_coupling=dynamics_.reference_feedback * (1 - self._arousal_at(concentration)),
        )

    def readouts(self) -> list[ConcentrationReadout]:
        """One readout per concentration held, in the order held: induction, then emergence."""
        return [observers.readout(self._settings.quorum_fraction) for observers in self._observed]


@dataclass(frozen=True)
class ReadoutSweep:
    """One induction-emergence sweep with both readouts: global coherence and the DPC readout."""

    record: dynamics.InductionEmergenceRecord
    induction: tuple[ConcentrationReadout, ...]
    emergence: tuple[ConcentrationReadout, ...]


def run_with_readout(connectome: Connectome, design: dynamics.SweepDesign, settings: ReadoutSettings) -> ReadoutSweep:
    network = DpcReadoutNetwork(connectome, design, settings)
    record = network.induction_emergence()
    readouts = network.readouts()
    induction_count = len(record.induction)
    return ReadoutSweep(record, tuple(readouts[:induction_count]), tuple(readouts[induction_count:]))


# ---------------------------------------------------------------------------
# Analysis of a sweep (pure functions)
# ---------------------------------------------------------------------------


def holds_quorum(readout: ConcentrationReadout) -> bool:
    return readout.holds_quorum


def dpc_loss_concentration(induction: Sequence[ConcentrationReadout]) -> float | None:
    """Last concentration of induction at which DPC quorum still held; None if never lost or never held."""
    return dpc.loss_concentration(induction, holds_quorum)


def dpc_recovery_concentration(emergence: Sequence[ConcentrationReadout]) -> float | None:
    """Highest concentration of emergence at which DPC quorum has returned."""
    return dpc.recovery_concentration(emergence, holds_quorum)


def pair_rule_loss_concentration(induction: Sequence[ConcentrationReadout], rule: PairRule) -> float | None:
    """Last concentration of induction at which quorum under the pair rule still held; None if never lost or held."""
    return dpc.loss_concentration(induction, lambda point: point.pair_rules[rule].component.holds_quorum)
