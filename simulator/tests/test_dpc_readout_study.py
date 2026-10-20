"""The pre-specified DPC readout study (readout_study package): pass rule, seeds, conditions and every test's verdict."""

from __future__ import annotations

import math
import unittest
from dataclasses import replace

import calibration as cal
import disconnection_study
import dpc_readout as readout
import learned_timing_study
import phase_dynamics as dynamics
import prespecified_study
import reporting
import species_study as species
from readout_study import (
    agents, calibrated_values, conditions, disconnection, fluctuations, pass_rule, phase_inertia, plans, running, settings,
    static_baseline, transitions, weaker_coupling,
)
from tests.test_prespecified_study import run as coherence_run

Name = conditions.ConditionName
NO_FLUCTUATIONS = readout.FluctuationMeasurement(0.1, 0.1, 0.1)


BUDGET = readout.ConnectionBudget(0.35, 2.0, 0.2)


def point(concentration: float, quorum: bool, fluctuations: readout.FluctuationMeasurement = NO_FLUCTUATIONS) -> readout.ConcentrationReadout:
    summary = readout.ComponentSummary(0.9 if quorum else 0.1, 4 if quorum else 0, 4)
    return readout.ConcentrationReadout(concentration, summary, summary, summary, summary, 0.3, BUDGET, fluctuations)


def readout_run(condition: str, quorum_until: float | None, returns_at: float | None = None, **coherence: object) -> running.ReadoutRun:
    """Induction on 0, 0.05, ..., 3 with DPC quorum up to quorum_until; emergence with it back from returns_at down."""
    grid = [round(0.05 * index, 2) for index in range(61)]
    induction = tuple(point(c, quorum_until is not None and c <= quorum_until) for c in grid)
    emergence = tuple(point(c, returns_at is not None and c <= returns_at) for c in reversed(grid))
    return running.ReadoutRun(coherence_run(condition, **coherence), induction, emergence)


def with_threshold(run: running.ReadoutRun, threshold: readout.FluctuationMeasurement, awake: readout.FluctuationMeasurement = NO_FLUCTUATIONS) -> running.ReadoutRun:
    loss = run.dpc_loss_concentration
    induction = tuple(
        replace(p, fluctuations=threshold if p.concentration == loss else awake if p.concentration == 0 else p.fluctuations) for p in run.induction
    )
    return replace(run, induction=induction)


class SmokeModeTests(unittest.TestCase):
    def test_the_smoke_mode_keeps_only_c_elegans_and_two_concentrations(self) -> None:
        plan = plans.smoke_plan(plans.AGENT_PLAN)
        self.assertEqual(plan.organisms, settings.SMOKE_ORGANISMS)
        for condition in plan.conditions(settings.SMOKE_INTEGRATION):
            self.assertEqual(condition.design.grid.ascending(), [0.0, cal.CONCENTRATION_GRID.maximum])
            self.assertTrue(set(condition.organisms) <= set(settings.SMOKE_ORGANISMS))
        design = plans.study_design(plan, plans.StudyMode.SMOKE)
        self.assertEqual((design.integration, design.seeds_per_organism, design.label), (settings.SMOKE_INTEGRATION, {"celegans": 1}, reporting.RunLabel.QUICK))

    def test_awake_only_calibration_conditions_keep_their_single_concentration(self) -> None:
        for condition in plans.smoke_plan(plans.COUPLING_CALIBRATION_PLAN).conditions(settings.SMOKE_INTEGRATION):
            self.assertEqual(condition.design.grid.ascending(), [0.0])

    def test_the_smoke_mode_runs_the_percolation_model_on_c_elegans_only(self) -> None:
        self.assertEqual(plans.percolation_design(plans.StudyMode.SMOKE).organisms, settings.SMOKE_ORGANISMS)
        self.assertEqual(len(plans.percolation_design(plans.StudyMode.FULL).held_out_seeds), settings.PERCOLATION_HELD_OUT_SEEDS)


class ProvenanceTests(unittest.TestCase):
    def test_package_modules_are_hashed_under_their_path_and_top_level_ones_under_their_name(self) -> None:
        import provenance
        import readout_study.plans
        names = {provenance.source_name(path) for path in provenance.loaded_sources()}
        self.assertIn("readout_study/plans.py", names)
        self.assertIn("dpc_readout.py", names)


class PassRuleTests(unittest.TestCase):
    def outcome(self, holding: int, applicable: int) -> reporting.CheckOutcome:
        return reporting.CheckOutcome("T2a-D", "statement", "C. elegans", holding, applicable)

    def test_the_wilson_lower_bound_must_lie_above_one_half(self) -> None:
        for holding, applicable, passes in ((15, 20, True), (14, 20, False), (9, 10, True), (8, 10, False), (6, 6, True), (5, 6, False)):
            self.assertEqual(pass_rule.holds_reliably(self.outcome(holding, applicable)), passes, (holding, applicable))

    def test_nothing_to_count_fails(self) -> None:
        self.assertFalse(pass_rule.holds_reliably(self.outcome(0, 0)))


class SeedTests(unittest.TestCase):
    def test_both_blocks_are_fresh_and_disjoint_from_each_other(self) -> None:
        used = {0, 1000, prespecified_study.SEED_OFFSET, learned_timing_study.SEED_OFFSET, disconnection_study.SEED_OFFSET}
        blocks = {settings.SEED_OFFSET: 20, settings.CALIBRATION_SEED_OFFSET: 10, settings.COUPLING_CALIBRATION_SEED_OFFSET: 4}
        for offset, count in blocks.items():
            self.assertTrue(all(not (u <= offset < u + 100 or offset <= u < offset + count) for u in used), offset)
        self.assertGreaterEqual(settings.CALIBRATION_SEED_OFFSET - settings.SEED_OFFSET, max(settings.VALIDATION_SEEDS.values()))
        self.assertGreaterEqual(settings.COUPLING_CALIBRATION_SEED_OFFSET - settings.CALIBRATION_SEED_OFFSET, settings.PERCOLATION_CALIBRATION_SEEDS)

    def test_the_scan_runs_on_the_calibration_block_and_the_validation_on_the_test_block(self) -> None:
        self.assertEqual(plans.INERTIA_SCAN_PLAN.seed_offset, settings.CALIBRATION_SEED_OFFSET)
        self.assertEqual(plans.validation_plan([calibrated_values.Calibrated("celegans", 0.8, 1.0)]).seed_offset, settings.SEED_OFFSET)
        self.assertEqual(plans.metastable_plan([calibrated_values.Calibrated("celegans", 1.0, 0.6)]).seed_offset, settings.SEED_OFFSET)
        self.assertEqual(plans.COUPLING_CALIBRATION_PLAN.seed_offset, settings.COUPLING_CALIBRATION_SEED_OFFSET)

    def test_the_inertia_scan_has_at_least_ten_seeds(self) -> None:
        self.assertTrue(all(seeds >= 10 for seeds in settings.INERTIA_SCAN_SEEDS.values()))


class ConditionTests(unittest.TestCase):
    def test_the_random_control_differs_from_k1c_only_in_where_the_timing_error_falls(self) -> None:
        applied, phantom, random, random_phantom = conditions.disconnection_conditions(cal.FULL_INTEGRATION)
        self.assertEqual(replace(random.design, jitter_scaling=dynamics.JitterScaling.SENSORY_PATHWAYS), applied.design)
        self.assertEqual(replace(random_phantom.design, jitter_scaling=dynamics.JitterScaling.SENSORY_PATHWAYS), phantom.design)
        self.assertEqual(random.design.integration.measurement_steps, cal.measurement_steps_for(settings.WINDOW_CYCLES))

    def test_the_feedback_scan_reaches_one_and_a_half_times_the_noisy_locking_threshold(self) -> None:
        self.assertAlmostEqual(settings.LOCKING_THRESHOLD, readout.kuramoto_critical_coupling(cal.NATURAL_FREQUENCY_SPREAD, cal.NOISE_INTENSITY))
        self.assertGreater(settings.LOCKING_THRESHOLD, 0.5 * math.sqrt(8 / math.pi))
        self.assertAlmostEqual(max(settings.SCANNED_FEEDBACK), 1.5 * settings.LOCKING_THRESHOLD)
        self.assertEqual(len(set(settings.SCANNED_FEEDBACK)), len(settings.LOCKING_THRESHOLD_MULTIPLES))

    def test_the_null_model_is_rewired_and_otherwise_the_same(self) -> None:
        by_name = {c.name: c for c in conditions.agent_conditions(cal.QUICK_INTEGRATION)}
        self.assertTrue(by_name[Name.NMDA_ANTAGONIST_REWIRED].rewired)
        self.assertEqual(by_name[Name.NMDA_ANTAGONIST_REWIRED].design, by_name[Name.NMDA_ANTAGONIST].design)

    def test_the_wired_conditions_differ_from_the_reference_only_in_the_wiring_of_the_reference(self) -> None:
        by_name = {c.name: c for c in conditions.agent_conditions(cal.QUICK_INTEGRATION)}
        wired = by_name[Name.GABAERGIC_WIRED].design
        self.assertEqual(wired.reference_wiring, dynamics.ReferenceWiring.TRANSMITTING_INPUTS)
        self.assertEqual(replace(wired, reference_wiring=dynamics.ReferenceWiring.GLOBAL_MEAN_FIELD), by_name[Name.GABAERGIC].design)
        self.assertTrue(by_name[Name.GABAERGIC_WIRED_REWIRED].rewired)

    def test_the_coupling_calibration_holds_the_network_awake_only(self) -> None:
        for condition in conditions.coupling_calibration_conditions(cal.QUICK_INTEGRATION):
            self.assertEqual(condition.design.grid.ascending(), [0.0])

    def test_the_human_connectome_has_no_directed_reading(self) -> None:
        self.assertNotIn("human", settings.DIRECTED_ORGANISMS)


class AgentTests(unittest.TestCase):
    def test_quorum_lost_within_the_range_holds_and_never_lost_fails(self) -> None:
        self.assertTrue(agents.abolishes_dpc_quorum(readout_run(Name.GABAERGIC, quorum_until=1.5)))
        self.assertFalse(agents.abolishes_dpc_quorum(readout_run(Name.GABAERGIC, quorum_until=3.0)))

    def test_quorum_never_held_counts_as_failing(self) -> None:
        self.assertFalse(agents.abolishes_dpc_quorum(readout_run(Name.GABAERGIC, quorum_until=None)))


class FluctuationTests(unittest.TestCase):
    def test_t1d_needs_twice_the_independent_phase_susceptibility_at_the_threshold(self) -> None:
        base = readout_run(Name.GABAERGIC, quorum_until=1.5)
        self.assertTrue(fluctuations.collective_fluctuations_at_threshold(with_threshold(base, readout.FluctuationMeasurement(0.6, 0.3, 0.5))))
        self.assertFalse(fluctuations.collective_fluctuations_at_threshold(with_threshold(base, readout.FluctuationMeasurement(0.59, 0.3, 0.5))))
        self.assertFalse(fluctuations.collective_fluctuations_at_threshold(readout_run(Name.GABAERGIC, quorum_until=3.0)))

    def test_t1e_needs_more_autocorrelation_than_awake(self) -> None:
        base = readout_run(Name.GABAERGIC, quorum_until=1.5)
        awake = readout.FluctuationMeasurement(0.1, 0.1, 0.2)
        self.assertTrue(fluctuations.slower_fluctuations_at_threshold(with_threshold(base, readout.FluctuationMeasurement(0.1, 0.1, 0.21), awake)))
        self.assertFalse(fluctuations.slower_fluctuations_at_threshold(with_threshold(base, readout.FluctuationMeasurement(0.1, 0.1, 0.2), awake)))
        self.assertFalse(fluctuations.slower_fluctuations_at_threshold(with_threshold(base, readout.FluctuationMeasurement(0.1, 0.1, None), awake)))

    def test_t1f_pairs_each_connectome_with_the_next_smaller_on_the_same_seed(self) -> None:
        def sized(organism: str, seed: int, excess: float) -> running.ReadoutRun:
            run = with_threshold(readout_run(Name.GABAERGIC, quorum_until=1.5, seed=seed), readout.FluctuationMeasurement(excess, 1.0, 0.5))
            return replace(run, coherence=replace(run.coherence, organism=organism))
        runs = [sized("celegans", 1, 2.0), sized("human", 1, 3.0), sized("drosophila", 1, 2.5), sized("human", 2, 9.0)]
        outcomes = {o.group: (o.runs_holding, o.runs_applicable) for o in fluctuations.evaluate_size(runs, list(cal.ORGANISMS))}
        self.assertEqual(outcomes, {"Human": (1, 1), "Drosophila": (0, 1)})


def stimulus(condition: str, seed: int, awake: float, deepest: float, quorum_kept: bool) -> running.ReadoutRun:
    return readout_run(condition, quorum_until=3.0 if quorum_kept else 1.0, seed=seed, awake_broadcast_entrainment=awake, deepest_broadcast_entrainment=deepest)


def stimulus_runs(seed: int, sensory_deepest: float, random_deepest: float) -> list[running.ReadoutRun]:
    """Awake locking 0.13 against a floor of 0.03 in every condition; the deepest locking varies."""
    return [
        stimulus(Name.SENSORY_APPLIED, seed, 0.13, sensory_deepest, quorum_kept=True),
        stimulus(Name.SENSORY_PHANTOM, seed, 0.03, 0.03, quorum_kept=True),
        stimulus(Name.RANDOM_APPLIED, seed, 0.13, random_deepest, quorum_kept=True),
        stimulus(Name.RANDOM_PHANTOM, seed, 0.03, 0.03, quorum_kept=True),
    ]


def with_budget(run: running.ReadoutRun, concentration: float, counting: float, coupling: float) -> running.ReadoutRun:
    induction = tuple(
        replace(p, counting_share=counting, budget=replace(p.budget, effective_coupling=coupling)) if p.concentration == concentration else p
        for p in run.induction
    )
    return replace(run, induction=induction)


class StaticAndTransitionTests(unittest.TestCase):
    def test_t0_holds_when_the_oscillator_readout_loses_quorum_below_the_static_reading(self) -> None:
        run = readout_run(Name.GABAERGIC, quorum_until=1.5)
        static_later = replace(run, induction=tuple(replace(p, jitter_only=readout.ComponentSummary(0.9, 4, 4)) if p.concentration <= 1.7 else p for p in run.induction))
        self.assertTrue(static_baseline.dynamics_lower_the_loss(static_later))
        self.assertFalse(static_baseline.dynamics_lower_the_loss(run))
        never_static = replace(run, induction=tuple(replace(p, jitter_only=readout.ComponentSummary(0.9, 4, 4)) for p in run.induction))
        self.assertTrue(static_baseline.dynamics_lower_the_loss(never_static))

    def test_sp1_compares_counting_shares_and_couplings_on_a_log_scale(self) -> None:
        gabaergic = with_budget(readout_run(Name.GABAERGIC, quorum_until=1.5), 1.5, counting=0.02, coupling=0.2)
        nmda = with_budget(readout_run(Name.NMDA_ANTAGONIST, quorum_until=1.0), 1.0, counting=0.021, coupling=1.5)
        self.assertTrue(transitions.percolation_like(running.RunPair(gabaergic, nmda)))
        self.assertFalse(transitions.percolation_like(running.RunPair(gabaergic, with_budget(nmda, 1.0, counting=0.2, coupling=0.21))))

    def test_sp2_reads_the_budgets_at_the_coherence_criterions_losses(self) -> None:
        gabaergic = with_budget(readout_run(Name.GABAERGIC, quorum_until=1.5, loss_concentration=1.2), 1.2, counting=0.1, coupling=0.9)
        nmda = with_budget(readout_run(Name.NMDA_ANTAGONIST, quorum_until=1.5, loss_concentration=0.6), 0.6, counting=0.3, coupling=0.95)
        self.assertTrue(transitions.synchronisation_like(running.RunPair(gabaergic, nmda)))

    def test_sp_is_undefined_where_an_agent_never_loses_quorum(self) -> None:
        pair = running.RunPair(readout_run(Name.GABAERGIC, quorum_until=1.5), readout_run(Name.NMDA_ANTAGONIST, quorum_until=3.0))
        self.assertIsNone(transitions.percolation_like(pair))

    def test_wiring_matters_beyond_one_step_or_where_only_one_loses_quorum(self) -> None:
        def pair(loss: float | None, null_loss: float | None) -> running.RunPair:
            return running.RunPair(readout_run(Name.GABAERGIC_WIRED, quorum_until=loss), readout_run(Name.GABAERGIC_WIRED_REWIRED, quorum_until=null_loss))
        self.assertTrue(agents.wiring_matters(pair(1.5, 1.35)))
        self.assertFalse(agents.wiring_matters(pair(1.5, 1.45)))
        self.assertTrue(agents.wiring_matters(pair(1.5, 3.0)))


class CouplingCalibrationTests(unittest.TestCase):
    def awake(self, coupling: float, coherence: float, seed: int = 1) -> species.RunSummary:
        return coherence_run(conditions.coupling_condition_name(coupling), seed=seed, induction_coherence=(coherence,))

    def test_the_coupling_closest_to_the_target_inside_the_range_is_chosen(self) -> None:
        runs = [self.awake(0.5, 0.45), self.awake(0.75, 0.56), self.awake(1.0, 0.69), self.awake(1.25, 0.8)]
        chosen = weaker_coupling.calibrate_coupling(runs, "celegans")
        self.assertEqual((chosen.value, chosen.achieved), (0.75, 0.56))

    def test_no_coupling_in_range_leaves_the_organism_uncalibrated_and_untested(self) -> None:
        chosen = weaker_coupling.calibrate_coupling([self.awake(0.5, 0.4), self.awake(1.0, 0.75)], "celegans")
        self.assertIsNone(chosen.value)
        self.assertEqual(plans.metastable_plan([chosen]).organisms, ())

    def test_each_calibrated_organism_runs_both_agents_at_its_own_coupling(self) -> None:
        built = plans.metastable_plan([calibrated_values.Calibrated("celegans", 1.0, 0.6), calibrated_values.Calibrated("human", 0.5, 0.55)]).conditions(cal.QUICK_INTEGRATION)
        self.assertEqual(sorted((c.organisms[0], c.design.dynamics.synaptic_coupling, c.design.agent.name) for c in built), sorted(
            (o, k, a.name) for o, k in (("celegans", 1.0), ("human", 0.5)) for a in (cal.GABAERGIC_AGENT, cal.NMDA_ANTAGONIST_AGENT)
        ))


class DisconnectionTests(unittest.TestCase):
    def test_k1d_needs_dpc_quorum_at_the_highest_concentration_and_the_excess_halved(self) -> None:
        kept = disconnection.ReadoutStimulusPair(stimulus(Name.SENSORY_APPLIED, 1, 0.13, 0.08, True), stimulus(Name.SENSORY_PHANTOM, 1, 0.03, 0.03, True))
        self.assertTrue(disconnection.disconnected_with_dpc_quorum(kept))
        lost = replace(kept, applied=stimulus(Name.SENSORY_APPLIED, 1, 0.13, 0.08, False))
        self.assertFalse(disconnection.disconnected_with_dpc_quorum(lost))
        spreading = replace(kept, applied=stimulus(Name.SENSORY_APPLIED, 1, 0.13, 0.09, True))
        self.assertFalse(disconnection.disconnected_with_dpc_quorum(spreading))

    def test_k1d_is_not_applicable_without_awake_broadcast_above_twice_the_floor(self) -> None:
        pair = disconnection.ReadoutStimulusPair(stimulus(Name.SENSORY_APPLIED, 1, 0.05, 0.03, True), stimulus(Name.SENSORY_PHANTOM, 1, 0.03, 0.03, True))
        self.assertIsNone(disconnection.disconnected_with_dpc_quorum(pair))

    def test_k1e_holds_only_when_random_placement_does_not_also_disconnect(self) -> None:
        specific = disconnection.placement_controls(stimulus_runs(1, sensory_deepest=0.04, random_deepest=0.12))
        generic = disconnection.placement_controls(stimulus_runs(1, sensory_deepest=0.04, random_deepest=0.04))
        self.assertTrue(disconnection.specific_to_sensory_pathways(specific[0]))
        self.assertFalse(disconnection.specific_to_sensory_pathways(generic[0]))

    def test_tests_are_judged_only_where_half_the_seeds_pass_the_gate(self) -> None:
        runs = [r for seed in range(4) for r in stimulus_runs(seed, 0.04, 0.12)]
        verdict = disconnection.disconnection_verdict(runs)
        self.assertEqual(verdict(reporting.CheckOutcome("K1d", "s", "C. elegans", 1, 1)), disconnection.NOT_EVALUABLE)
        self.assertEqual(verdict(reporting.CheckOutcome("K1d", "s", "C. elegans", 2, 2)), pass_rule.FAILS)
        self.assertEqual(disconnection.evaluate_disconnection(runs, ["celegans"])[1].runs_holding, 4)


class InertiaTests(unittest.TestCase):
    def test_i1_needs_recovery_more_than_one_step_below_the_loss(self) -> None:
        name = conditions.feedback_condition_name(settings.SCANNED_FEEDBACK[0])
        self.assertTrue(phase_inertia.dpc_inertia(readout_run(name, quorum_until=1.5, returns_at=1.4)))
        self.assertFalse(phase_inertia.dpc_inertia(readout_run(name, quorum_until=1.5, returns_at=1.45)))
        self.assertFalse(phase_inertia.dpc_inertia(readout_run(name, quorum_until=1.5, returns_at=None)))

    def test_calibration_picks_the_feedback_closest_to_the_target_among_those_where_every_seed_recovers(self) -> None:
        low, middle, high = (conditions.feedback_condition_name(f) for f in settings.SCANNED_FEEDBACK[:3])
        runs = [
            readout_run(low, quorum_until=1.5, returns_at=1.5), readout_run(low, quorum_until=1.5, returns_at=1.5, seed=2),
            readout_run(middle, quorum_until=1.5, returns_at=1.4), readout_run(middle, quorum_until=1.5, returns_at=1.4, seed=2),
            readout_run(high, quorum_until=1.5, returns_at=1.4), readout_run(high, quorum_until=1.5, returns_at=None, seed=2),
        ]
        calibration = phase_inertia.calibrate_feedback(runs, "celegans")
        self.assertEqual(calibration.value, settings.SCANNED_FEEDBACK[1])
        self.assertAlmostEqual(calibration.achieved, 1.5 / 1.4)

    def test_calibration_fails_when_no_feedback_lets_every_seed_recover(self) -> None:
        name = conditions.feedback_condition_name(settings.SCANNED_FEEDBACK[0])
        self.assertIsNone(phase_inertia.calibrate_feedback([readout_run(name, quorum_until=1.5)], "celegans").value)
        self.assertEqual(plans.validation_plan([calibrated_values.Calibrated("celegans", None, None)]).organisms, ())

    def test_i2_needs_the_ratio_within_the_measured_range(self) -> None:
        name = conditions.validation_condition_name(0.8)
        self.assertTrue(phase_inertia.within_measured_inertia(readout_run(name, quorum_until=1.5, returns_at=1.4)))
        self.assertFalse(phase_inertia.within_measured_inertia(readout_run(name, quorum_until=1.5, returns_at=1.5)))
        self.assertFalse(phase_inertia.within_measured_inertia(readout_run(name, quorum_until=1.5, returns_at=0.0)))

    def test_validation_runs_each_organism_at_its_own_calibrated_feedback(self) -> None:
        calibrations = [calibrated_values.Calibrated("celegans", 0.8, 1.1), calibrated_values.Calibrated("human", 1.0, 1.2)]
        built = plans.validation_plan(calibrations).conditions(cal.QUICK_INTEGRATION)
        self.assertEqual([(c.organisms, c.design.dynamics.reference_feedback) for c in built], [(("celegans",), 0.8), (("human",), 1.0)])


if __name__ == "__main__":
    unittest.main()
