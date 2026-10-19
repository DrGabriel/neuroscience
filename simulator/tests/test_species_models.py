"""Tests for the cross-species models: connectome loading, phase dynamics, analysis and plant tissue.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
Tests that need a downloaded dataset are skipped when it is absent.
"""

from __future__ import annotations

import tempfile
import unittest.mock
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

import calibration as cal
import connectomes
import dpc_simulator as dpc
import phase_dynamics as dynamics
import plant_tissue

RING_SIZE = 40
SMALL_GRID = dpc.ConcentrationGrid(maximum=3.0, step=0.25)
SHORT_INTEGRATION = dynamics.IntegrationSettings(time_step=0.05, relaxation_steps=150, measurement_steps=150)


def all_to_all(node_count: int) -> connectomes.Connectome:
    sources, targets = np.nonzero(~np.eye(node_count, dtype=bool))
    return connectomes.Connectome(
        name="all-to-all",
        organism="synthetic",
        node_count=node_count,
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=np.ones(sources.size, dtype=np.float32),
        modules=(np.arange(node_count) % 4).astype(np.int32),
        module_basis="synthetic",
        sensory_nodes=np.arange(4, dtype=np.int32),
        sensory_description="first four nodes",
    )


# Sensory node 0 feeds 1, which feeds 2 and 3; 2 -> 1 and 1 -> 0 run back towards the senses,
# 2 -> 3 is lateral (both two steps out), and node 4, which nothing reaches, projects into 1.
CHAIN_CONNECTIONS = ((0, 1), (1, 2), (2, 1), (1, 0), (1, 3), (2, 3), (4, 1))
CHAIN_FEEDBACK = (False, False, True, True, False, False, False)


def chain() -> connectomes.Connectome:
    sources, targets = (np.array(column, dtype=np.int32) for column in zip(*CHAIN_CONNECTIONS))
    return replace(
        all_to_all(5),
        name="chain",
        sources=sources,
        targets=targets,
        weights=np.ones(sources.size, dtype=np.float32),
        sensory_nodes=np.array([0], dtype=np.int32),
    )


def design(**overrides: object) -> dynamics.SweepDesign:
    base = replace(cal.base_sweep_design(SHORT_INTEGRATION, seed=1), grid=SMALL_GRID)
    return replace(base, **overrides)


def measurement(concentration: float, coherence: float) -> dynamics.StateMeasurement:
    return dynamics.StateMeasurement(concentration, coherence, susceptibility=0.0, local_coherence=coherence)


def record(induction: list[float], emergence: list[float]) -> dynamics.InductionEmergenceRecord:
    concentrations = [index * 0.5 for index in range(len(induction))]
    return dynamics.InductionEmergenceRecord(
        awake_coherence=induction[0],
        quorum_fraction=0.5,
        chance=dynamics.ChanceCoherence(0.0, 0.0),
        induction=tuple(measurement(c, r) for c, r in zip(concentrations, induction)),
        emergence=tuple(measurement(c, r) for c, r in zip(reversed(concentrations), emergence)),
    )


class AnalysisTests(unittest.TestCase):
    def test_thresholds_and_hysteresis_from_a_known_record(self) -> None:
        sweep = record(induction=[1.0, 0.9, 0.2, 0.1], emergence=[0.1, 0.2, 0.3, 0.9])
        self.assertEqual(dynamics.loss_concentration(sweep), 0.5)
        self.assertEqual(dynamics.recovery_concentration(sweep), 0.0)
        self.assertEqual(dynamics.hysteresis_width(sweep), 0.5)

    def test_never_losing_quorum_gives_no_thresholds(self) -> None:
        sweep = record(induction=[1.0, 0.9, 0.8], emergence=[0.8, 0.9, 1.0])
        self.assertIsNone(dynamics.loss_concentration(sweep))
        self.assertIsNone(dynamics.hysteresis_width(sweep))

    def test_above_chance_maps_chance_to_zero_and_synchrony_to_one(self) -> None:
        self.assertAlmostEqual(dynamics.above_chance(0.2, 0.2), 0.0)
        self.assertAlmostEqual(dynamics.above_chance(1.0, 0.2), 1.0)

    def test_chance_coherence_matches_random_phase_expectation(self) -> None:
        rng = np.random.default_rng(1)
        simulated = np.abs(np.exp(1j * rng.uniform(0, 2 * np.pi, (20_000, 100))).mean(axis=1)).mean()
        expected = dynamics.ChanceCoherence.of(100, np.array([100])).global_level
        self.assertAlmostEqual(simulated, expected, places=2)

    def test_broadcast_ratio_needs_a_stimulus(self) -> None:
        self.assertIsNone(dynamics.broadcast_ratio(measurement(0.0, 1.0)))
        stimulated = replace(measurement(0.0, 1.0), sensory_entrainment=0.8, broadcast_entrainment=0.4)
        self.assertAlmostEqual(dynamics.broadcast_ratio(stimulated), 0.5)


class DriveTests(unittest.TestCase):
    def test_synchronised_populations_receive_no_synaptic_drive(self) -> None:
        connectome = all_to_all(RING_SIZE)
        no_timing_error = np.zeros(connectome.edge_count)
        connectivity = dynamics.ImpairedConnectivity(
            connectome.sources, connectome.targets, connectome.weights, no_timing_error, no_timing_error
        )
        jitter = dynamics.TimingJitter(no_timing_error, 0.0, np.random.default_rng(1))
        drive = dynamics.SynapticDrive(connectome, 4.0, connectivity, jitter)
        self.assertTrue(np.allclose(drive(np.zeros(RING_SIZE), 1.0 + 0j, 0.0), 0.0))

    def test_fluctuating_jitter_weakens_effective_coupling_by_the_gaussian_factor(self) -> None:
        sd = 1.0
        rng = np.random.default_rng(1)
        mean_drive = np.mean(np.sin(0.5 - sd * rng.standard_normal(400_000)))
        self.assertAlmostEqual(mean_drive, np.sin(0.5) * np.exp(-sd**2 / 2), places=2)

    def test_correlated_jitter_keeps_its_standard_deviation(self) -> None:
        sd = np.full(20_000, 0.7)
        jitter = dynamics.TimingJitter(sd, persistence=0.9, rng=np.random.default_rng(1))
        samples = np.concatenate([jitter.next() for _ in range(5)])
        self.assertAlmostEqual(float(np.std(samples)), 0.7, places=2)

    def test_correlated_jitter_persists_between_steps(self) -> None:
        jitter = dynamics.TimingJitter(np.ones(20_000), persistence=0.9, rng=np.random.default_rng(1))
        first = jitter.next().copy()
        second = jitter.next()
        self.assertAlmostEqual(float(np.corrcoef(first, second)[0, 1]), 0.9, places=1)

    def test_correlated_jitter_statistics_do_not_depend_on_the_step(self) -> None:
        coarse, fine = design(), replace(design(), integration=replace(design().integration, time_step=design().integration.time_step / 4))
        sd = np.ones(4)
        coarse_jitter = dynamics.TimingJitter.for_design(sd, coarse, np.random.default_rng(1))
        fine_jitter = dynamics.TimingJitter.for_design(sd, fine, np.random.default_rng(1))
        self.assertAlmostEqual(coarse_jitter.persistence, fine_jitter.persistence**4)

    def test_fixed_jitter_produces_no_fluctuation(self) -> None:
        connectome = all_to_all(RING_SIZE)
        fixed = design(jitter_dynamics=dynamics.JitterDynamics.FIXED)
        connectivity = dynamics.ConnectionImpairment(connectome, fixed, np.random.default_rng(1)).at(1.0)
        self.assertTrue(np.all(connectivity.jitter_sd == 0))

    def test_reference_pulls_a_lagging_population_forward(self) -> None:
        drive = dynamics.PhaseReferenceDrive(feedback=1.0, arousal=0.0)
        self.assertGreater(drive(np.array([-0.5]), 1.0 + 0j, 0.0)[0], 0.0)

    def test_arousal_sustains_the_reference_when_coherence_is_low(self) -> None:
        weak_mean_field = 0.1 + 0j
        without = dynamics.PhaseReferenceDrive(feedback=1.0, arousal=0.0)(np.array([-0.5]), weak_mean_field, 0.0)[0]
        with_arousal = dynamics.PhaseReferenceDrive(feedback=1.0, arousal=0.5)(np.array([-0.5]), weak_mean_field, 0.0)[0]
        self.assertGreater(with_arousal, without)

    def test_conduction_delay_becomes_a_phase_lag(self) -> None:
        connectome = replace(all_to_all(2), lengths_mm=np.array([39.0, 39.0], dtype=np.float32))
        delays = dynamics.conduction_delays_ms(connectome, design(conduction_velocity_m_per_s=3.9))
        lags = dynamics.milliseconds_to_radians(delays, frequency_hz=40.0)
        ten_milliseconds_at_forty_hertz = 2 * np.pi * 40.0 * 10.0 / 1000.0
        self.assertTrue(np.allclose(lags, ten_milliseconds_at_forty_hertz))

    def test_fallback_slows_the_reference_as_the_agent_takes_effect(self) -> None:
        adaptive = replace(cal.POPULATION_DYNAMICS, fallback_frequency_hz=10.0)
        awake = dynamics.reference_frequency_hz(adaptive, cal.GABAERGIC_AGENT, 0.0)
        deep = dynamics.reference_frequency_hz(adaptive, cal.GABAERGIC_AGENT, 3.0)
        self.assertEqual(awake, adaptive.oscillation_frequency_hz)
        self.assertLess(deep, awake)
        self.assertGreater(deep, adaptive.fallback_frequency_hz)

    def test_same_jitter_costs_less_phase_at_a_slower_rhythm(self) -> None:
        self.assertAlmostEqual(
            dynamics.milliseconds_to_radians(5.0, 10.0) * 4, dynamics.milliseconds_to_radians(5.0, 40.0)
        )

    def test_pathway_jitter_acts_only_on_connections_leaving_sensory_populations(self) -> None:
        connectome = all_to_all(RING_SIZE)
        _, agent_weights = dynamics.jitter_weights(connectome, dynamics.JitterScaling.SENSORY_PATHWAYS, seed=1)
        leaves_sensory = np.isin(connectome.sources, connectome.sensory_nodes)
        self.assertTrue(np.all(agent_weights[leaves_sensory] == 1.0))
        self.assertTrue(np.all(agent_weights[~leaves_sensory] == 0.0))

    def test_feedback_connections_run_towards_the_sensory_populations(self) -> None:
        self.assertEqual(tuple(chain().feedback_connections().tolist()), CHAIN_FEEDBACK)

    def test_feedback_jitter_acts_only_on_feedback_connections(self) -> None:
        _, agent_weights = dynamics.jitter_weights(chain(), dynamics.JitterScaling.FEEDBACK_CONNECTIONS, seed=1)
        self.assertEqual(tuple(agent_weights.tolist()), tuple(float(f) for f in CHAIN_FEEDBACK))

    def test_matched_random_jitter_acts_on_as_many_connections_as_are_feedback(self) -> None:
        connectome = all_to_all(RING_SIZE)
        feedback = int(connectome.feedback_connections().sum())
        _, agent_weights = dynamics.jitter_weights(connectome, dynamics.JitterScaling.MATCHED_RANDOM_CONNECTIONS, seed=1)
        self.assertEqual(int(agent_weights.sum()), feedback)
        self.assertGreater(feedback, 0)

    def test_matched_random_connections_depend_on_the_seed_only(self) -> None:
        scaling = dynamics.JitterScaling.MATCHED_RANDOM_CONNECTIONS
        first, again, other = (dynamics.jitter_weights(all_to_all(RING_SIZE), scaling, seed)[1] for seed in (1, 1, 2))
        self.assertTrue(np.array_equal(first, again))
        self.assertFalse(np.array_equal(first, other))

    def test_failed_connections_stay_failed_at_higher_concentrations(self) -> None:
        connectome = all_to_all(RING_SIZE)
        impairment = dynamics.ConnectionImpairment(connectome, design(), np.random.default_rng(1))
        low, high = impairment.at(0.8), impairment.at(1.5)
        low_edges = set(zip(low.sources.tolist(), low.targets.tolist()))
        high_edges = set(zip(high.sources.tolist(), high.targets.tolist()))
        self.assertTrue(high_edges <= low_edges)
        self.assertLess(len(high_edges), len(low_edges))

    def test_conduction_length_jitter_requires_tract_lengths(self) -> None:
        with self.assertRaises(ValueError):
            dynamics.jitter_weights(all_to_all(RING_SIZE), dynamics.JitterScaling.CONDUCTION_LENGTH, seed=1)


class ReviewFixTests(unittest.TestCase):
    """Defects found by the hostile review of 19 October 2026."""

    def test_baseline_and_agent_timing_errors_add_in_quadrature_regression(self) -> None:
        connectome = all_to_all(RING_SIZE)
        timing = design(agent=cal.NMDA_ANTAGONIST_AGENT)
        concentration = 1.0
        connectivity = dynamics.ConnectionImpairment(connectome, timing, np.random.default_rng(1)).at(concentration)
        baseline = timing.dynamics.baseline_jitter_ms
        added = cal.NMDA_ANTAGONIST_AGENT.added_jitter_ms(concentration)
        frequency = dynamics.reference_frequency_hz(timing.dynamics, cal.NMDA_ANTAGONIST_AGENT, concentration)
        expected = dynamics.milliseconds_to_radians(np.hypot(baseline, added), frequency)
        self.assertTrue(np.allclose(connectivity.jitter_sd, expected))

    def test_a_population_not_following_the_stimulus_averages_to_zero_over_whole_cycles_regression(self) -> None:
        def entrainment(steps: int) -> float:
            is_sensory = np.zeros(RING_SIZE, dtype=bool)
            is_sensory[0] = True
            recorder = dynamics.ObservableRecorder(all_to_all(RING_SIZE), is_sensory, cal.SENSORY_STIMULUS)
            phases = np.zeros(RING_SIZE)
            for step in range(steps):
                recorder.record(phases, 1.0 + 0j, step * cal.FULL_TIME_STEP)
            return recorder.measurement(0.0).broadcast_entrainment
        first_window_steps = 600
        self.assertGreater(entrainment(first_window_steps), 0.2)
        self.assertLess(entrainment(cal.FULL_MEASUREMENT_STEPS), 0.01)


class SignedConnectionTests(unittest.TestCase):
    def test_inhibitory_connections_get_negative_weight(self) -> None:
        connectome = all_to_all(4)
        signs = np.where(connectome.sources == 0, -1, 1).astype(np.int8)
        signed = replace(connectome, signs={"rule": signs})
        weights = dynamics.signed_weights(signed, design(sign_rule="rule"))
        self.assertTrue(np.all(weights[connectome.sources == 0] < 0))
        self.assertTrue(np.all(weights[connectome.sources != 0] > 0))

    def test_unknown_sign_rule_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            dynamics.signed_weights(all_to_all(4), design(sign_rule="missing"))

    def test_dominant_transmitter_decides_the_sign(self) -> None:
        pairs = connectomes.NeuronPairs(
            pair_of_row=np.array([0, 0, 1]), kept=np.array([True, True]),
            sources=np.array([0, 1]), targets=np.array([1, 0]), synapses=np.array([10.0, 5.0]),
        )
        synapses = np.array([6.0, 4.0, 5.0])
        probabilities = {name: np.zeros(3) for name in connectomes.FLYWIRE_TRANSMITTERS}
        probabilities["gaba"] = np.array([0.9, 0.1, 0.0])
        probabilities["ach"] = np.array([0.1, 0.9, 0.0])
        probabilities["glut"] = np.array([0.0, 0.0, 1.0])
        signs = connectomes.connection_signs(pairs, synapses, probabilities)
        self.assertEqual(signs[connectomes.SIGN_RULE_GABA].tolist(), [-1, 1])
        self.assertEqual(signs[connectomes.SIGN_RULE_GABA_AND_GLUTAMATE].tolist(), [-1, -1])


class PhaseSweepIntegrationTests(unittest.TestCase):
    def test_awake_network_is_coherent_and_agent_abolishes_quorum(self) -> None:
        sweep = dynamics.run_induction_emergence(all_to_all(RING_SIZE), design())
        self.assertGreater(sweep.awake_coherence, 0.9)
        self.assertIsNotNone(dynamics.loss_concentration(sweep))

    def test_stimulus_entrains_the_sensory_populations(self) -> None:
        sweep = dynamics.run_induction_emergence(all_to_all(RING_SIZE), design(stimulus=cal.SENSORY_STIMULUS))
        self.assertIsNotNone(sweep.induction[0].sensory_entrainment)
        self.assertGreater(sweep.induction[-1].sensory_entrainment, sweep.induction[-1].broadcast_entrainment)


class PlantTissueTests(unittest.TestCase):
    def tissue(self, **overrides: object) -> plant_tissue.TissueDesign:
        base = replace(cal.PLANT_TISSUE, geometry=plant_tissue.TissueGeometry(20, 20), duration_steps=1500)
        return replace(base, **overrides)

    def test_square_grid_has_the_expected_number_of_junctions(self) -> None:
        first, _ = plant_tissue.TissueGeometry(3, 4).junctions()
        self.assertEqual(first.size, 3 * 3 + 2 * 4)

    def test_resting_state_is_the_fitzhugh_fixed_point(self) -> None:
        v, w = plant_tissue.RESTING_VOLTAGE, plant_tissue.RESTING_RECOVERY
        self.assertAlmostEqual(v - v**3 / 3 - w, 0.0, places=3)
        self.assertAlmostEqual(v + plant_tissue.FITZHUGH_A - plant_tissue.FITZHUGH_B * w, 0.0, places=3)

    def test_action_potential_crosses_intact_tissue(self) -> None:
        self.assertGreater(plant_tissue.ExcitableTissue(self.tissue()).propagate(0.0).reached_fraction, 0.95)

    def test_closing_every_junction_confines_activity_to_the_stimulated_cells(self) -> None:
        sealed = replace(cal.GABAERGIC_AGENT, max_transmission_failure=1.0)
        result = plant_tissue.ExcitableTissue(self.tissue(agent=sealed)).propagate(100.0)
        self.assertAlmostEqual(result.reached_fraction, 20 / 400, places=6)


class ConnectomeTests(unittest.TestCase):
    def test_corrupted_download_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = replace(connectomes.CELEGANS, key="corrupt", sha256="0" * 64)
            path = Path(directory) / "file.csv"
            path.write_text("Source,Target,Weight,Type\n")
            with unittest.mock.patch.object(type(source), "path", property(lambda _: path)):
                with self.assertRaises(connectomes.IntegrityError):
                    connectomes.fetch(source)

    @unittest.skipUnless(connectomes.CELEGANS.path.exists(), "C. elegans data not downloaded")
    def test_celegans_has_amphid_sensory_neurons(self) -> None:
        worm = connectomes.load_celegans(cal.CONNECTOME_SEED)
        self.assertEqual(worm.sensory_nodes.size, 24)
        self.assertEqual(worm.node_count, 448)

    @unittest.skipUnless(connectomes.HUMAN.path.exists(), "Human data not downloaded")
    def test_human_has_66_areas_and_auditory_cortex(self) -> None:
        human = connectomes.load_human(cal.CONNECTOME_SEED)
        self.assertEqual(human.module_count, 66)
        self.assertEqual(human.sensory_nodes.size, 7)
        self.assertEqual(human.lengths_mm.size, human.edge_count)


class ConvergenceSettingsTests(unittest.TestCase):
    def test_longer_fly_runs_are_not_capped_back_to_the_fly_settling_time_regression(self) -> None:
        import convergence_study

        task = next(t for t in convergence_study.tasks_for({"drosophila": 1}, cal.FULL_INTEGRATION) if t.variant == "twice the simulated time")
        design = convergence_study.variant_design(task)
        self.assertEqual(design.integration.relaxation_steps, 2 * cal.DROSOPHILA_RELAXATION_STEPS)
        self.assertEqual(design.grid.step, cal.DROSOPHILA_CONCENTRATION_STEP)

    def test_finer_integration_covers_the_same_simulated_time(self) -> None:
        import convergence_study

        reference = design().integration
        finer = convergence_study.finer(reference)
        self.assertAlmostEqual(finer.time_step * finer.measurement_steps, reference.time_step * reference.measurement_steps)
        self.assertAlmostEqual(finer.time_step, reference.time_step / 2)

    def test_longer_integration_doubles_the_simulated_time(self) -> None:
        import convergence_study

        reference = design().integration
        longer = convergence_study.longer(reference)
        self.assertEqual(longer.time_step, reference.time_step)
        self.assertEqual(longer.measurement_steps, 2 * reference.measurement_steps)


if __name__ == "__main__":
    unittest.main()
