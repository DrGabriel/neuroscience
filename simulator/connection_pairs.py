"""When a connection between two populations counts in a cycle: the pair rules of the DPC readout (Appendix C.13).

A connectome stores directed arcs. Two populations linked by at least one arc form one anatomical connection, an
unordered pair. DPC never stated whether such a pair has one chance to be on time in a cycle or one per arc, and the
answer matters: diffusion MRI records no direction, so each human fibre is stored as two arcs, and reading each arc
as its own connection gives every fibre two independent timing draws. Three rules are read side by side:

    ONE_PER_CONNECTION  each anatomical connection has one timing draw: that of its canonical arc, the first arc
                        (in connectome order) from the lower-indexed to the higher-indexed population when one
                        exists, else the first arc the other way. It counts when that arc transmits and is on time.
                        This is the rule of the percolation model and of the threshold theory of Appendix B.5, and
                        the primary rule.
    BOTH_DIRECTIONS     a connection with arcs both ways counts only when it is on time both ways; one with arcs one
                        way only counts when it is on time that way. Each direction is read on its first arc, so
                        repeated arcs in one direction (chemical and electrical synapses in C. elegans) give it no
                        extra chance. A lower bound.
    EITHER_DIRECTION    a connection counts when any of its arcs transmits and is on time: the rule Appendix C.12
                        used, every arc a separate chance. An upper bound.

In every cycle the connections counting under BOTH_DIRECTIONS are among those counting under ONE_PER_CONNECTION,
which are among those counting under EITHER_DIRECTION.

Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

from connectomes import Connectome

NO_ARC = -1


class PairRule(Enum):
    """When an anatomical connection between two populations counts in a cycle."""

    ONE_PER_CONNECTION = "one timing draw per anatomical connection"
    BOTH_DIRECTIONS = "both directions on time"
    EITHER_DIRECTION = "either direction on time"


PRIMARY_PAIR_RULE = PairRule.ONE_PER_CONNECTION


def first_arc_of_each_connection(connection_of_arc: np.ndarray, arcs: np.ndarray, connection_count: int) -> np.ndarray:
    """For each connection, the lowest-indexed of the given arcs that belongs to it; NO_ARC where none does."""
    absent = connection_of_arc.size
    first = np.full(connection_count, absent, dtype=np.int64)
    np.minimum.at(first, connection_of_arc[arcs], arcs)
    return np.where(first == absent, NO_ARC, first)


def on_time_where_present(arc: np.ndarray, on_time_arcs: np.ndarray) -> np.ndarray:
    """Whether each connection's arc in one direction is on time; True where the connection has no arc that way."""
    return np.where(arc == NO_ARC, True, on_time_arcs[np.maximum(arc, 0)])


@dataclass(frozen=True)
class AnatomicalConnections:
    """The unordered pairs of populations that the connectome links, with the arcs that carry each pair's draws."""

    population_count: int
    lower: np.ndarray
    higher: np.ndarray
    # For each arc of the connectome, the index of its anatomical connection.
    connection_of_arc: np.ndarray
    # For each connection, its first arc from the lower- to the higher-indexed population, and the other way.
    ascending_arc: np.ndarray
    descending_arc: np.ndarray
    # The arc carrying each connection's one draw under ONE_PER_CONNECTION.
    canonical_arc: np.ndarray

    @classmethod
    def of(cls, connectome: Connectome) -> AnatomicalConnections:
        sources, targets = connectome.sources.astype(np.int64), connectome.targets.astype(np.int64)
        lower, higher = np.minimum(sources, targets), np.maximum(sources, targets)
        keys, connection_of_arc = np.unique(lower * connectome.node_count + higher, return_inverse=True)
        arcs = np.arange(sources.size)
        ascending = first_arc_of_each_connection(connection_of_arc, arcs[sources <= targets], keys.size)
        descending = first_arc_of_each_connection(connection_of_arc, arcs[sources > targets], keys.size)
        return cls(
            population_count=connectome.node_count,
            lower=(keys // connectome.node_count).astype(connectome.sources.dtype),
            higher=(keys % connectome.node_count).astype(connectome.sources.dtype),
            connection_of_arc=connection_of_arc,
            ascending_arc=ascending,
            descending_arc=descending,
            canonical_arc=np.where(ascending == NO_ARC, descending, ascending),
        )

    @property
    def count(self) -> int:
        return self.lower.size

    def counting(self, on_time_arcs: np.ndarray, rule: PairRule) -> np.ndarray:
        """Which connections count, given which arcs of the connectome transmit and are on time in this cycle."""
        return COUNTING_UNDER[rule](self, on_time_arcs)


def counts_one_per_connection(connections: AnatomicalConnections, on_time_arcs: np.ndarray) -> np.ndarray:
    return on_time_arcs[connections.canonical_arc]


def counts_both_directions(connections: AnatomicalConnections, on_time_arcs: np.ndarray) -> np.ndarray:
    ascending = on_time_where_present(connections.ascending_arc, on_time_arcs)
    return ascending & on_time_where_present(connections.descending_arc, on_time_arcs)


def counts_either_direction(connections: AnatomicalConnections, on_time_arcs: np.ndarray) -> np.ndarray:
    return np.bincount(connections.connection_of_arc, weights=on_time_arcs, minlength=connections.count) > 0


COUNTING_UNDER: dict[PairRule, Callable[[AnatomicalConnections, np.ndarray], np.ndarray]] = {
    PairRule.ONE_PER_CONNECTION: counts_one_per_connection,
    PairRule.BOTH_DIRECTIONS: counts_both_directions,
    PairRule.EITHER_DIRECTION: counts_either_direction,
}
