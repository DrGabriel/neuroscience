"""The DPC readout (dpc_readout.py): counting connections, giant components and quorum on hand-built cases with known
answers, the readout leaving the dynamics unchanged, and a regression showing it can disagree with the coherence
criterion it replaces.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import unittest
from dataclasses import replace

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

import calibration as cal
import connectomes
import dpc_readout as readout
import dpc_simulator as dpc
import phase_dynamics as dynamics

# 3 ms at 40 Hz is 0.754 rad, so W / 2 is 0.377 rad.
HALF_WINDOW = readout.ReadoutSettings(dpc.REFERENCE_INTEGRATION_WINDOW_MS, cal.QUORUM_FRACTION, 1.0).half_window(cal.OSCILLATION_FREQUENCY_HZ)
ON_TIME = 0.0
LATE = 2 * HALF_WINDOW
LOCKED = 1.0 + 0j


def ring(population_count: int) -> tuple[np.ndarray, np.ndarray]:
    sources = np.arange(population_count)
    return sources, (sources + 1) % population_count


def snapshot(sources: np.ndarray, targets: np.ndarray, phase_error: float, phases: np.ndarray | None = None) -> readout.CycleSnapshot:
    population_count = int(max(sources.max(), targets.max())) + 1
    phases = np.zeros(population_count) if phases is None else phases
    mean_field = complex(np.exp(1j * phases).mean())
    return readout.CycleSnapshot(phases, mean_field, sources, targets, np.full(sources.size, phase_error), sources.size)


def two_rings(size: int) -> tuple[np.ndarray, np.ndarray]:
    """Two directed rings of size populations each, not joined to each other."""
    sources, targets = ring(size)
    return np.concatenate([sources, sources + size]), np.concatenate([targets, targets + size])


class WindowTests(unittest.TestCase):
    def test_half_window_is_half_of_two_pi_f_w(self) -> None:
        self.assertAlmostEqual(HALF_WINDOW, 0.5 * 2 * np.pi * 40.0 * 3.0 / 1000.0)

    def test_at_a_slower_reference_the_same_window_is_a_smaller_phase(self) -> None:
        settings = readout.ReadoutSettings(3.0, 0.5, 1.0)
        self.assertAlmostEqual(settings.half_window(10.0), HALF_WINDOW / 4)

    def test_one_cycle_is_sampled_per_interval(self) -> None:
        self.assertEqual(readout.ReadoutSettings(3.0, 0.5, 1.0).interval_steps(0.05), 20)


class HandBuiltCycleTests(unittest.TestCase):
    def test_all_connections_on_time_form_one_component_of_every_population(self) -> None:
        cycle = readout.read_cycle(snapshot(*ring(6), ON_TIME), HALF_WINDOW)
        self.assertEqual(cycle.giant_share, 1.0)
        self.assertEqual(cycle.strongly_connected_share, 1.0)
        self.assertEqual(cycle.counting_share, 1.0)

    def test_all_connections_late_leave_every_population_alone_and_no_quorum(self) -> None:
        cycle = readout.read_cycle(snapshot(*ring(6), LATE), HALF_WINDOW)
        self.assertAlmostEqual(cycle.giant_share, 1 / 6)
        self.assertEqual(cycle.counting_share, 0.0)
        self.assertFalse(readout.ComponentSummary.of([cycle.giant_share] * 3, cal.QUORUM_FRACTION).holds_quorum)

    def test_a_split_network_forms_two_components(self) -> None:
        graph = snapshot(*two_rings(3), ON_TIME).counting_graph(np.ones(6, dtype=bool))
        self.assertEqual(graph.largest_component_share(readout.ComponentKind.UNDIRECTED), 0.5)
        adjacency = coo_matrix((np.ones(6), (graph.sources, graph.targets)), shape=(6, 6))
        self.assertEqual(connected_components(adjacency, directed=False)[0], 2)

    def test_half_the_populations_is_exactly_quorum(self) -> None:
        cycle = readout.read_cycle(snapshot(*two_rings(3), ON_TIME), HALF_WINDOW)
        self.assertTrue(readout.ComponentSummary.of([cycle.giant_share], 0.5).holds_quorum)
        self.assertFalse(readout.ComponentSummary.of([cycle.giant_share], 0.6).holds_quorum)

    def test_one_late_link_splits_the_strongly_connected_ring_but_not_the_undirected_one(self) -> None:
        sources, targets = ring(4)
        state = snapshot(sources, targets, ON_TIME)
        state = replace(state, phase_errors=np.array([ON_TIME, ON_TIME, ON_TIME, LATE]))
        cycle = readout.read_cycle(state, HALF_WINDOW)
        self.assertEqual(cycle.giant_share, 1.0)
        self.assertEqual(cycle.strongly_connected_share, 0.25)

    def test_the_window_edge_counts(self) -> None:
        self.assertTrue(readout.counting_connections(np.array([HALF_WINDOW, -HALF_WINDOW]), HALF_WINDOW).all())
        self.assertFalse(readout.counting_connections(np.array([1.0001 * HALF_WINDOW]), HALF_WINDOW).any())


class TimingErrorTests(unittest.TestCase):
    def test_a_population_just_behind_the_rhythm_wraps_to_a_small_lag(self) -> None:
        state = snapshot(np.array([0]), np.array([1]), ON_TIME, phases=np.array([2 * np.pi - 0.1, 0.0]))
        state = replace(state, mean_field=LOCKED)
        self.assertAlmostEqual(float(readout.arrival_timing_errors(state, readout.TimingReference.SHARED_RHYTHM)[0]), -0.1)

    def test_a_signal_one_whole_cycle_late_is_late_not_on_time(self) -> None:
        state = replace(snapshot(np.array([0]), np.array([1]), dynamics.FULL_CYCLE_RADIANS), mean_field=LOCKED)
        errors = readout.arrival_timing_errors(state, readout.TimingReference.SHARED_RHYTHM)
        self.assertFalse(readout.counting_connections(errors, HALF_WINDOW).any())

    def test_the_two_references_differ_when_sender_and_receiver_drift_together(self) -> None:
        state = replace(snapshot(np.array([0]), np.array([1]), ON_TIME, phases=np.array([1.0, 1.0])), mean_field=LOCKED)
        shared = readout.arrival_timing_errors(state, readout.TimingReference.SHARED_RHYTHM)
        receiver = readout.arrival_timing_errors(state, readout.TimingReference.RECEIVER_PHASE)
        self.assertFalse(readout.counting_connections(shared, HALF_WINDOW).any())
        self.assertTrue(readout.counting_connections(receiver, HALF_WINDOW).all())

    def test_timed_at_the_receiver_a_whole_cycle_late_wraps_on_time_the_chance_floor(self) -> None:
        state = replace(snapshot(np.array([0]), np.array([1]), dynamics.FULL_CYCLE_RADIANS), mean_field=LOCKED)
        receiver = readout.arrival_timing_errors(state, readout.TimingReference.RECEIVER_PHASE)
        self.assertTrue(readout.counting_connections(receiver, HALF_WINDOW).all())

    def test_the_jitter_only_reading_ignores_how_far_the_sender_has_drifted(self) -> None:
        state = replace(snapshot(np.array([0]), np.array([1]), ON_TIME, phases=np.array([2.0, 0.0])), mean_field=LOCKED)
        self.assertTrue(readout.counting_connections(readout.arrival_timing_errors(state, readout.TimingReference.JITTER_ONLY), HALF_WINDOW).all())
        self.assertFalse(readout.counting_connections(readout.arrival_timing_errors(state, readout.TimingReference.SHARED_RHYTHM), HALF_WINDOW).any())

    def test_a_lag_is_subtracted_from_the_senders_lead(self) -> None:
        state = replace(snapshot(np.array([0]), np.array([1]), 0.3, phases=np.array([0.5, 0.0])), mean_field=LOCKED)
        self.assertAlmostEqual(float(readout.arrival_timing_errors(state, readout.TimingReference.SHARED_RHYTHM)[0]), 0.2)


def connectivity(transmitting: int, jitter_sd: float, lag: float = 0.0) -> dynamics.ImpairedConnectivity:
    sources = np.arange(transmitting)
    return dynamics.ImpairedConnectivity(
        sources=sources, targets=(sources + 1) % max(transmitting, 1), weights=np.ones(transmitting, dtype=np.float32),
        fixed_lags=np.full(transmitting, lag), jitter_sd=np.full(transmitting, jitter_sd), edges=sources,
    )


class StaticPredictionTests(unittest.TestCase):
    def test_static_share_is_section_4_1s_pi(self) -> None:
        # 3 ms of jitter at 40 Hz, all of 10 connections transmitting out of 20: (1 − p) erf(W / (2√2 σ)) with p = 0.5.
        sd = float(dynamics.milliseconds_to_radians(3.0, 40.0))
        share = readout.static_counting_share(connectivity(10, sd), 20, HALF_WINDOW)
        self.assertAlmostEqual(share, 0.5 * dpc.within_window(3.0, 3.0))

    def test_without_spread_a_connection_counts_exactly_when_its_lag_is_inside_the_window(self) -> None:
        self.assertEqual(readout.static_counting_share(connectivity(4, 0.0, lag=0.9 * HALF_WINDOW), 4, HALF_WINDOW), 1.0)
        self.assertEqual(readout.static_counting_share(connectivity(4, 0.0, lag=1.1 * HALF_WINDOW), 4, HALF_WINDOW), 0.0)

    def test_effective_coupling_is_k_times_transmitting_weight_times_the_gaussian_factor(self) -> None:
        self.assertAlmostEqual(readout.effective_coupling(connectivity(5, 0.6), 10.0, 4.0), 4.0 * 0.5 * np.exp(-0.18))


class KuramotoThresholdTests(unittest.TestCase):
    def test_without_noise_it_is_kuramotos_two_over_pi_g0(self) -> None:
        self.assertAlmostEqual(readout.kuramoto_critical_coupling(0.5, 0.0), 0.5 * np.sqrt(8 / np.pi))

    def test_the_closed_form_matches_the_integral(self) -> None:
        from scipy.integrate import quad
        spread, noise = 0.5, 0.05
        def integrand(w: float) -> float:
            return np.exp(-0.5 * (w / spread) ** 2) / (spread * np.sqrt(2 * np.pi)) * noise / (noise**2 + w**2)
        weight = sum(quad(integrand, a, b, limit=400)[0] for a, b in ((-np.inf, -1), (-1, 0), (0, 1), (1, np.inf)))
        self.assertAlmostEqual(readout.kuramoto_critical_coupling(spread, noise), 2 / weight, places=6)

    def test_noise_raises_the_threshold(self) -> None:
        self.assertGreater(readout.kuramoto_critical_coupling(0.5, 0.05), readout.kuramoto_critical_coupling(0.5, 0.0))


class SummaryTests(unittest.TestCase):
    def test_quorum_at_a_concentration_needs_at_least_half_the_cycles(self) -> None:
        self.assertTrue(readout.ComponentSummary.of([0.9, 0.9, 0.1, 0.1], 0.5).holds_quorum)
        self.assertFalse(readout.ComponentSummary.of([0.9, 0.1, 0.1, 0.1], 0.5).holds_quorum)
        self.assertEqual(readout.ComponentSummary.of([0.9, 0.1], 0.5).mean_share, 0.5)

    def test_independent_uniform_phases_give_one_half_and_locked_phases_none(self) -> None:
        self.assertEqual(readout.independent_phase_susceptibility(0.0, 0.0), 0.5)
        self.assertEqual(readout.independent_phase_susceptibility(1.0, 1.0), 0.0)

    def test_autocorrelation_of_a_ramp_is_one_and_of_a_constant_undefined(self) -> None:
        self.assertAlmostEqual(readout.lagged_autocorrelation(np.arange(10.0), 1), 1.0)
        self.assertIsNone(readout.lagged_autocorrelation(np.ones(10), 1))
        self.assertIsNone(readout.lagged_autocorrelation(np.arange(2.0), 1))

    def test_loss_and_recovery_follow_the_cycles_with_quorum(self) -> None:
        def point(concentration: float, with_quorum: int) -> readout.ConcentrationReadout:
            summary = readout.ComponentSummary(0.5, with_quorum, 4)
            budget = readout.ConnectionBudget(0.1, 1.0, 0.2)
            return readout.ConcentrationReadout(concentration, summary, summary, summary, summary, 0.1, budget, readout.FluctuationMeasurement(0.1, 0.1, None))
        induction = [point(0.0, 4), point(1.0, 2), point(2.0, 1)]
        emergence = [point(2.0, 0), point(1.0, 1), point(0.0, 3)]
        self.assertEqual(readout.dpc_loss_concentration(induction), 1.0)
        self.assertEqual(readout.dpc_recovery_concentration(emergence), 0.0)


def lattice(population_count: int, neighbours: int) -> connectomes.Connectome:
    """Each population sends to its nearest neighbours on either side of a ring."""
    offsets = [o for k in range(1, neighbours + 1) for o in (k, -k)]
    sources = np.repeat(np.arange(population_count), len(offsets))
    targets = (sources + np.tile(offsets, population_count)) % population_count
    return connectomes.Connectome(
        name="lattice", organism="synthetic", node_count=population_count,
        sources=sources.astype(np.int32), targets=targets.astype(np.int32), weights=np.ones(sources.size, dtype=np.float32),
        modules=(np.arange(population_count) % 4).astype(np.int32), module_basis="synthetic",
        sensory_nodes=np.arange(2, dtype=np.int32), sensory_description="first two populations",
    )


SMALL_INTEGRATION = dynamics.IntegrationSettings(time_step=0.05, relaxation_steps=60, measurement_steps=60)
SETTINGS = readout.ReadoutSettings(dpc.REFERENCE_INTEGRATION_WINDOW_MS, cal.QUORUM_FRACTION, cal.JITTER_CORRELATION_TIME)


def small_design(**changes: object) -> dynamics.SweepDesign:
    base = replace(cal.base_sweep_design(SMALL_INTEGRATION, seed=7), grid=dpc.ConcentrationGrid(maximum=3.0, step=1.0))
    return replace(base, **changes)


class ObservationTests(unittest.TestCase):
    """The readout watches the simulation; it must not change a single number of it."""

    def test_the_readout_leaves_every_measurement_unchanged(self) -> None:
        network = lattice(40, 3)
        for design in (small_design(), small_design(agent=cal.NMDA_ANTAGONIST_AGENT), small_design(jitter_dynamics=dynamics.JitterDynamics.FIXED)):
            plain = dynamics.run_induction_emergence(network, design)
            observed = readout.run_with_readout(network, design, SETTINGS).record
            self.assertEqual(observed, plain)

    def test_one_readout_per_concentration_held_with_one_cycle_per_interval(self) -> None:
        sweep = readout.run_with_readout(lattice(40, 3), small_design(), SETTINGS)
        self.assertEqual(len(sweep.induction), len(sweep.record.induction))
        self.assertEqual(len(sweep.emergence), len(sweep.record.emergence))
        self.assertEqual([p.concentration for p in sweep.emergence], [p.concentration for p in sweep.record.emergence])
        self.assertEqual(sweep.induction[0].undirected.cycles, 3)

    def test_the_fluctuation_recorder_matches_the_models_susceptibility(self) -> None:
        sweep = readout.run_with_readout(lattice(40, 3), small_design(), SETTINGS)
        for plain, observed in zip(sweep.record.induction, sweep.induction):
            self.assertAlmostEqual(observed.fluctuations.susceptibility, plain.susceptibility, places=12)

    def test_the_awake_network_holds_dpc_quorum(self) -> None:
        sweep = readout.run_with_readout(lattice(40, 3), small_design(), SETTINGS)
        self.assertTrue(sweep.induction[0].holds_quorum)

    def test_learned_arrival_offsets_are_refused(self) -> None:
        design = small_design(dynamics=replace(cal.POPULATION_DYNAMICS, arrival_learning_time=cal.ARRIVAL_LEARNING_TIME))
        with self.assertRaises(ValueError):
            readout.DpcReadoutNetwork(lattice(40, 3), design, SETTINGS)


def synaptic(population_count: int, wiring: tuple[list[int], list[int]], transmitting: list[int] | None = None) -> dynamics.SynapticDrive:
    """A drive on a hand-built network with no timing error; transmitting lists the connections that have not failed."""
    sources, targets = (np.array(side, dtype=np.int32) for side in wiring)
    network = connectomes.Connectome(
        name="hand-built", organism="synthetic", node_count=population_count, sources=sources, targets=targets,
        weights=np.ones(sources.size, dtype=np.float32), modules=np.zeros(population_count, dtype=np.int32), module_basis="synthetic",
        sensory_nodes=np.arange(1, dtype=np.int32), sensory_description="first population",
    )
    kept = np.arange(sources.size) if transmitting is None else np.array(transmitting)
    impaired = dynamics.ImpairedConnectivity(
        sources=sources[kept], targets=targets[kept], weights=network.weights[kept], fixed_lags=np.zeros(kept.size), jitter_sd=np.zeros(kept.size), edges=kept,
    )
    jitter = dynamics.TimingJitter(np.zeros(kept.size), 0.0, np.random.default_rng(0))
    return dynamics.SynapticDrive(network, 1.0, dynamics.SynapticInputs(impaired, dynamics.ConnectionTiming(jitter)))


class WiredReferenceTests(unittest.TestCase):
    def test_each_population_is_pulled_towards_its_inputs_and_one_without_inputs_is_not_pulled(self) -> None:
        drive = synaptic(2, ([0], [1]))
        phases = np.array([0.5, 0.0])
        drive(phases, LOCKED, 0.0)
        pull = dynamics.WiredReferenceDrive(0.8, 0.5, drive)(phases, LOCKED, 0.0)
        np.testing.assert_allclose(pull, [0.0, 0.8 * np.sin(0.5)])

    def test_a_failed_input_weakens_the_reference_as_it_weakens_coupling(self) -> None:
        # Population 1 has two inputs at phase 0.5; with one failed, its reference coherence R is 0.5, not 1.
        phases = np.array([0.5, 0.0, 0.5])
        pulls = []
        for transmitting in (None, [0]):
            drive = synaptic(3, ([0, 2], [1, 1]), transmitting)
            drive(phases, LOCKED, 0.0)
            pulls.append(dynamics.WiredReferenceDrive(1.0, 0.0, drive)(phases, LOCKED, 0.0)[1])
        self.assertAlmostEqual(pulls[0], np.sin(0.5))
        self.assertAlmostEqual(pulls[1], 0.5 * np.sin(0.5))

    def test_the_wired_condition_changes_the_run_and_the_default_does_not(self) -> None:
        network, design = lattice(40, 3), small_design()
        wired = replace(design, reference_wiring=dynamics.ReferenceWiring.TRANSMITTING_INPUTS)
        self.assertEqual(design.reference_wiring, dynamics.ReferenceWiring.GLOBAL_MEAN_FIELD)
        self.assertNotEqual(dynamics.run_induction_emergence(network, wired), dynamics.run_induction_emergence(network, design))
        self.assertTrue(readout.run_with_readout(network, wired, SETTINGS).induction[0].holds_quorum)


class MatchedRandomSensoryOutputTests(unittest.TestCase):
    def test_as_many_connections_as_leave_the_sensory_populations_drawn_reproducibly(self) -> None:
        network = lattice(40, 3)
        scaling = dynamics.JitterScaling.MATCHED_RANDOM_SENSORY_OUTPUTS
        _, chosen = dynamics.jitter_weights(network, scaling, seed=3)
        self.assertEqual(chosen.sum(), dynamics.sensory_outputs(network).sum())
        np.testing.assert_array_equal(chosen, dynamics.jitter_weights(network, scaling, seed=3)[1])


class CriterionDisagreementTests(unittest.TestCase):
    def test_coherence_criterion_and_dpc_readout_can_disagree_Regression(self) -> None:
        # The phase model judged quorum by global coherence alone (phase_dynamics.py, is_conscious). A network held in
        # step while every signal arrives outside the window is conscious by that criterion and has no DPC quorum.
        locked = dynamics.StateMeasurement(concentration=3.0, global_coherence=1.0, susceptibility=0.0, local_coherence=1.0)
        record = dynamics.InductionEmergenceRecord(1.0, cal.QUORUM_FRACTION, dynamics.ChanceCoherence(0.1, 0.1), (locked,), (locked,))
        cycle = readout.read_cycle(snapshot(*ring(6), LATE), HALF_WINDOW)
        self.assertTrue(record.is_conscious(locked))
        self.assertFalse(readout.ComponentSummary.of([cycle.giant_share], cal.QUORUM_FRACTION).holds_quorum)

    def test_in_the_model_a_strong_reference_keeps_coherence_after_dpc_quorum_is_lost_Regression(self) -> None:
        # The same disagreement produced by the dynamics: with reference feedback above the locking threshold, the
        # reference holds the populations in step at three times the EC50, where 94% of transmissions fail.
        strong_reference = replace(cal.POPULATION_DYNAMICS, reference_feedback=2.0)
        sweep = readout.run_with_readout(lattice(40, 3), small_design(dynamics=strong_reference), SETTINGS)
        deepest_coherence, deepest_readout = sweep.record.induction[-1], sweep.induction[-1]
        self.assertTrue(sweep.record.is_conscious(deepest_coherence))
        self.assertFalse(deepest_readout.holds_quorum)


if __name__ == "__main__":
    unittest.main()
