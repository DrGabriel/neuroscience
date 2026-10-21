"""The pair rules of the DPC readout (connection_pairs.py and dpc_readout.py): when a connection between two
populations counts, on hand-built cases with known answers; the regression that gave every human fibre two chances;
and proof that adding the rules left every earlier reading of the readout unchanged, to the last bit.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

import numpy as np

import calibration as cal
import connectomes
import dpc_readout as readout
import phase_dynamics as dynamics
from connection_pairs import NO_ARC, AnatomicalConnections, PairRule
from tests.test_dpc_readout import HALF_WINDOW, LATE, LOCKED, ON_TIME, SETTINGS, lattice, small_design

ONE, BOTH, EITHER = PairRule.ONE_PER_CONNECTION, PairRule.BOTH_DIRECTIONS, PairRule.EITHER_DIRECTION
# Readings of the code before the pair rules were added (commit adc63f6), on the sweeps of EARLIER_SWEEPS.
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "dpc_readout_before_pair_rules.json"
EARLIER_SWEEPS = {
    "gabaergic": small_design(),
    "nmda_antagonist": small_design(agent=cal.NMDA_ANTAGONIST_AGENT),
    "fixed_jitter": small_design(jitter_dynamics=dynamics.JitterDynamics.FIXED),
}
ON_TIME_SHARE = 0.3
LARGE_RING = 20_000
SHARE_TOLERANCE = 0.02
RANDOM_POPULATIONS = 60
RANDOM_ARCS = 400
RANDOM_CYCLES = 50
NESTING_SEED, SYMMETRIC_SEED, RANDOM_WIRING_SEED = 1, 2, 3
LATTICE_POPULATIONS, LATTICE_NEIGHBOURS = 40, 3
SMALL_RING = 4
CHAIN = [(0, 1), (1, 2), (2, 3)]
# Six arcs over four populations: a pair stored both ways and once more, a one-way pair, and a pair stored both ways.
MIXED_WIRING = [(0, 1), (1, 0), (1, 2), (3, 2), (2, 3), (0, 1)]
MIXED_PAIRS = [(0, 1), (1, 2), (2, 3)]
MIXED_CONNECTION_OF_ARC = [0, 0, 1, 2, 2, 0]


def wired(wiring: list[tuple[int, int]], population_count: int | None = None) -> connectomes.Connectome:
    sources, targets = (np.array(side, dtype=np.int32) for side in zip(*wiring))
    count = population_count or int(max(sources.max(), targets.max())) + 1
    return connectomes.Connectome(
        name="hand-built", organism="synthetic", node_count=count, sources=sources, targets=targets,
        weights=np.ones(sources.size, dtype=np.float32), modules=np.zeros(count, dtype=np.int32), module_basis="synthetic",
        sensory_nodes=np.arange(1, dtype=np.int32), sensory_description="first population",
    )


def counted(wiring: list[tuple[int, int]], on_time: list[bool]) -> dict[PairRule, bool]:
    """Whether the single anatomical connection of the wiring counts under each rule."""
    connections = AnatomicalConnections.of(wired(wiring))
    return {rule: bool(connections.counting(np.array(on_time), rule)[0]) for rule in PairRule}


def two_way_ring(population_count: int) -> list[tuple[int, int]]:
    forward = [(i, (i + 1) % population_count) for i in range(population_count)]
    return forward + [(target, source) for source, target in forward]


class CanonicalArcTests(unittest.TestCase):
    def test_the_canonical_arc_runs_from_the_lower_to_the_higher_population_whatever_the_order_stored(self) -> None:
        self.assertEqual(AnatomicalConnections.of(wired([(0, 1), (1, 0)])).canonical_arc.tolist(), [0])
        self.assertEqual(AnatomicalConnections.of(wired([(1, 0), (0, 1)])).canonical_arc.tolist(), [1])

    def test_a_one_way_connection_is_read_on_its_only_arc(self) -> None:
        connections = AnatomicalConnections.of(wired([(2, 1)]))
        self.assertEqual((connections.canonical_arc.tolist(), connections.ascending_arc.tolist()), ([0], [NO_ARC]))

    def test_repeated_arcs_in_one_direction_are_read_on_the_first(self) -> None:
        connections = AnatomicalConnections.of(wired([(1, 0), (0, 1), (0, 1)]))
        self.assertEqual((connections.ascending_arc.tolist(), connections.descending_arc.tolist()), ([1], [0]))

    def test_each_unordered_pair_is_one_connection(self) -> None:
        connections = AnatomicalConnections.of(wired(MIXED_WIRING))
        self.assertEqual(list(zip(connections.lower.tolist(), connections.higher.tolist())), MIXED_PAIRS)
        self.assertEqual(connections.connection_of_arc.tolist(), MIXED_CONNECTION_OF_ARC)


class PairRuleTests(unittest.TestCase):
    def test_a_two_way_pair_with_only_the_non_canonical_arc_on_time(self) -> None:
        self.assertEqual(counted([(0, 1), (1, 0)], [False, True]), {ONE: False, BOTH: False, EITHER: True})

    def test_a_two_way_pair_with_only_the_canonical_arc_on_time(self) -> None:
        self.assertEqual(counted([(0, 1), (1, 0)], [True, False]), {ONE: True, BOTH: False, EITHER: True})

    def test_a_two_way_pair_on_time_both_ways_counts_under_every_rule(self) -> None:
        self.assertEqual(counted([(0, 1), (1, 0)], [True, True]), {ONE: True, BOTH: True, EITHER: True})

    def test_a_two_way_pair_late_both_ways_counts_under_none(self) -> None:
        self.assertEqual(counted([(0, 1), (1, 0)], [False, False]), {ONE: False, BOTH: False, EITHER: False})

    def test_a_one_way_pair_counts_under_every_rule_exactly_when_its_arc_is_on_time(self) -> None:
        self.assertEqual(counted([(2, 1)], [True]), {ONE: True, BOTH: True, EITHER: True})
        self.assertEqual(counted([(2, 1)], [False]), {ONE: False, BOTH: False, EITHER: False})

    def test_a_repeated_arc_gives_no_extra_chance_except_under_either_direction(self) -> None:
        self.assertEqual(counted([(0, 1), (0, 1), (1, 0)], [False, True, True]), {ONE: False, BOTH: False, EITHER: True})

    def test_both_directions_counts_within_one_per_connection_which_counts_within_either_direction(self) -> None:
        rng = np.random.default_rng(NESTING_SEED)
        wiring = [tuple(arc) for arc in rng.integers(0, RANDOM_POPULATIONS, size=(RANDOM_ARCS, 2)) if arc[0] != arc[1]]
        connections = AnatomicalConnections.of(wired(wiring, RANDOM_POPULATIONS))
        for _ in range(RANDOM_CYCLES):
            on_time = rng.random(len(wiring)) < ON_TIME_SHARE
            both, one, either = (connections.counting(on_time, rule) for rule in (BOTH, ONE, EITHER))
            self.assertTrue(np.all(both <= one) and np.all(one <= either))


class SymmetricWiringTests(unittest.TestCase):
    def test_a_symmetric_graph_gets_two_chances_per_pair_under_either_direction_and_one_under_one_per_connection_Regression(self) -> None:
        """Diffusion MRI stores each human fibre as two arcs. Read arc by arc (Appendix C.12), each fibre had two
        independent chances to be on time: with each arc on time with probability p, a fibre counted with probability
        1 − (1 − p)², not p."""
        connections = AnatomicalConnections.of(wired(two_way_ring(LARGE_RING)))
        self.assertEqual(connections.count, LARGE_RING)
        on_time = np.random.default_rng(SYMMETRIC_SEED).random(2 * LARGE_RING) < ON_TIME_SHARE
        shares = {rule: float(connections.counting(on_time, rule).mean()) for rule in PairRule}
        self.assertAlmostEqual(shares[EITHER], 1 - (1 - ON_TIME_SHARE) ** 2, delta=SHARE_TOLERANCE)
        self.assertAlmostEqual(shares[ONE], ON_TIME_SHARE, delta=SHARE_TOLERANCE)
        self.assertAlmostEqual(shares[BOTH], ON_TIME_SHARE**2, delta=SHARE_TOLERANCE)

    def test_one_arc_on_time_per_fibre_keeps_every_pair_under_either_direction_and_none_under_one_per_connection_Regression(self) -> None:
        ring = wired(two_way_ring(SMALL_RING))
        connections = AnatomicalConnections.of(ring)
        only_descending_on_time = ring.sources > ring.targets
        self.assertEqual(connections.counting(only_descending_on_time, EITHER).tolist(), [True] * SMALL_RING)
        self.assertEqual(connections.counting(only_descending_on_time, ONE).tolist(), [False] * SMALL_RING)


def cycle_snapshot(wiring: list[tuple[int, int]], arc_errors: list[float]) -> readout.CycleSnapshot:
    """Every arc transmits, every population sits on the rhythm, each arc with its own timing error."""
    network = wired(wiring)
    edges = np.arange(network.edge_count)
    return readout.CycleSnapshot(
        np.zeros(network.node_count), LOCKED, network.sources, network.targets, np.array(arc_errors), network.edge_count,
        edges, AnatomicalConnections.of(network),
    )


class CycleReadingTests(unittest.TestCase):
    def test_a_chain_on_time_only_against_the_canonical_direction_is_whole_under_either_and_broken_under_one(self) -> None:
        snapshot = cycle_snapshot(CHAIN + [(t, s) for s, t in CHAIN], [LATE] * len(CHAIN) + [ON_TIME] * len(CHAIN))
        cycle = readout.read_cycle(snapshot, HALF_WINDOW)
        self.assertEqual(cycle.pair_rules[EITHER].giant_share, 1.0)
        self.assertEqual(cycle.pair_rules[ONE].giant_share, 1 / snapshot.phases.size)
        self.assertEqual(cycle.pair_rules[ONE].counting_share, 0.0)
        self.assertEqual(cycle.pair_rules[EITHER].giant_share, cycle.giant_share)

    def test_without_the_anatomical_connections_no_pair_rule_is_read(self) -> None:
        snapshot = readout.CycleSnapshot(np.zeros(2), LOCKED, np.array([0]), np.array([1]), np.array([ON_TIME]), 1)
        self.assertEqual(readout.read_cycle(snapshot, HALF_WINDOW).pair_rules, {})

    def test_a_failed_canonical_arc_leaves_the_connection_out_under_one_per_connection(self) -> None:
        network = wired([(0, 1), (1, 0)])
        transmitting = np.array([1])
        snapshot = readout.CycleSnapshot(
            np.zeros(2), LOCKED, network.sources[transmitting], network.targets[transmitting], np.array([ON_TIME]), 2,
            transmitting, AnatomicalConnections.of(network),
        )
        cycle = readout.read_cycle(snapshot, HALF_WINDOW)
        self.assertEqual((cycle.pair_rules[ONE].counting_share, cycle.pair_rules[EITHER].counting_share), (0.0, 1.0))


def earlier_readings(point: readout.ConcentrationReadout) -> dict[str, object]:
    return {key: value for key, value in asdict(point).items() if key != "pair_rules"}


def random_wiring() -> connectomes.Connectome:
    rng = np.random.default_rng(RANDOM_WIRING_SEED)
    return wired([tuple(arc) for arc in rng.integers(0, RANDOM_POPULATIONS, size=(RANDOM_ARCS, 2)) if arc[0] != arc[1]], RANDOM_POPULATIONS)


class SweepTests(unittest.TestCase):
    def test_every_earlier_reading_is_unchanged_to_the_last_bit(self) -> None:
        before = json.loads(FIXTURE.read_text())
        for name, design in EARLIER_SWEEPS.items():
            sweep = readout.run_with_readout(lattice(LATTICE_POPULATIONS, LATTICE_NEIGHBOURS), design, SETTINGS)
            for branch, points in (("induction", sweep.induction), ("emergence", sweep.emergence)):
                self.assertEqual([earlier_readings(p) for p in points], before[name][branch], f"{name}, {branch}")

    def test_either_direction_reproduces_the_c12_reading_exactly_at_every_concentration(self) -> None:
        for network in (lattice(LATTICE_POPULATIONS, LATTICE_NEIGHBOURS), random_wiring()):
            for design in EARLIER_SWEEPS.values():
                sweep = readout.run_with_readout(network, design, SETTINGS)
                for point in sweep.induction + sweep.emergence:
                    self.assertEqual(point.pair_rules[EITHER].component, point.undirected)

    def test_every_rule_is_read_at_every_concentration_and_never_above_either_direction(self) -> None:
        sweep = readout.run_with_readout(random_wiring(), small_design(agent=cal.NMDA_ANTAGONIST_AGENT), SETTINGS)
        for point in sweep.induction:
            self.assertEqual(set(point.pair_rules), set(PairRule))
            shares = [point.pair_rules[rule].component.mean_share for rule in (BOTH, ONE, EITHER)]
            self.assertEqual(shares, sorted(shares))

    def test_the_loss_under_a_rule_follows_its_cycles_with_quorum(self) -> None:
        sweep = readout.run_with_readout(lattice(LATTICE_POPULATIONS, LATTICE_NEIGHBOURS), small_design(), SETTINGS)
        self.assertEqual(readout.pair_rule_loss_concentration(sweep.induction, EITHER), readout.dpc_loss_concentration(sweep.induction))


if __name__ == "__main__":
    unittest.main()
