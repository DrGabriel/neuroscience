"""Cellular-level control: action-potential propagation through excitable plant tissue.

Plants have no neurons, so they cannot test the network postulates of the DPC hypothesis
(P1-P3, P5). They do test the cellular postulate (P4): general anaesthetics stop organ
movements and block action potentials in the Venus flytrap (Yokawa et al., 2018).

Tissue is a square sheet of excitable cells, each described by the FitzHugh-Nagumo model
(FitzHugh, 1961; Nagumo et al., 1962), coupled to its four neighbours through cell-to-cell
junctions (plasmodesmata):

    dv_i/dt = v_i − v_i³/3 − w_i + G Σ_j o_ij (v_j − v_i)
    dw_i/dt = ε (v_i + a − b w_i)

where o_ij is 1 for an open junction and 0 for one closed by the anaesthetic. A row of cells
on one edge is stimulated and the fraction of the sheet reached by the action potential is
recorded. On a square lattice, bond percolation has the exact threshold 1/2 (Kesten, 1980),
which provides an independent check: propagation should fail once about half the junctions
are closed. Dependencies: numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dpc_simulator import AnaestheticAgent, ConcentrationGrid

# FitzHugh (1961), the parameter set used in the original paper.
FITZHUGH_A = 0.7
FITZHUGH_B = 0.8
FITZHUGH_EPSILON = 0.08
RESTING_VOLTAGE = -1.1994
RESTING_RECOVERY = -0.6243
# Voltage above which a cell counts as having fired (the excited branch of the cubic nullcline).
FIRING_VOLTAGE = 1.0
STIMULUS_VOLTAGE = 2.0
# Bond-percolation threshold of the square lattice (Kesten, 1980).
SQUARE_LATTICE_BOND_THRESHOLD = 0.5


@dataclass(frozen=True)
class TissueGeometry:
    rows: int
    columns: int

    @property
    def cell_count(self) -> int:
        return self.rows * self.columns

    def junctions(self) -> tuple[np.ndarray, np.ndarray]:
        """Each undirected junction between horizontally or vertically adjacent cells, once."""
        index = np.arange(self.cell_count).reshape(self.rows, self.columns)
        horizontal = (index[:, :-1].ravel(), index[:, 1:].ravel())
        vertical = (index[:-1, :].ravel(), index[1:, :].ravel())
        return np.concatenate([horizontal[0], vertical[0]]), np.concatenate([horizontal[1], vertical[1]])

    def stimulated_cells(self) -> np.ndarray:
        return np.arange(self.rows) * self.columns


@dataclass(frozen=True)
class TissueDesign:
    geometry: TissueGeometry
    junction_conductance: float
    time_step: float
    duration_steps: int
    agent: AnaestheticAgent
    grid: ConcentrationGrid
    seed: int


@dataclass(frozen=True)
class PropagationMeasurement:
    concentration: float
    open_junction_fraction: float
    reached_fraction: float


class ExcitableTissue:
    """One tissue realisation with quenched junction draws shared by every concentration."""

    def __init__(self, design: TissueDesign) -> None:
        self._design = design
        self._first, self._second = design.geometry.junctions()
        self._failure_draws = np.random.default_rng(design.seed).random(self._first.size)

    def propagate(self, concentration: float) -> PropagationMeasurement:
        is_open = self._failure_draws >= self._design.agent.transmission_failure(concentration)
        first, second = self._first[is_open], self._second[is_open]
        voltage, recovery = self._resting_state()
        voltage[self._design.geometry.stimulated_cells()] = STIMULUS_VOLTAGE
        has_fired = voltage > FIRING_VOLTAGE
        for _ in range(self._design.duration_steps):
            voltage, recovery = self._step(voltage, recovery, first, second)
            has_fired |= voltage > FIRING_VOLTAGE
        return PropagationMeasurement(concentration, float(is_open.mean()), float(has_fired.mean()))

    def _resting_state(self) -> tuple[np.ndarray, np.ndarray]:
        cells = self._design.geometry.cell_count
        return np.full(cells, RESTING_VOLTAGE), np.full(cells, RESTING_RECOVERY)

    def _step(
        self, voltage: np.ndarray, recovery: np.ndarray, first: np.ndarray, second: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        current = voltage[second] - voltage[first]
        coupling = np.bincount(first, weights=current, minlength=voltage.size) - np.bincount(
            second, weights=current, minlength=voltage.size
        )
        dv = voltage - voltage**3 / 3 - recovery + self._design.junction_conductance * coupling
        dw = FITZHUGH_EPSILON * (voltage + FITZHUGH_A - FITZHUGH_B * recovery)
        step = self._design.time_step
        return voltage + step * dv, recovery + step * dw


def concentration_sweep(design: TissueDesign) -> list[PropagationMeasurement]:
    tissue = ExcitableTissue(design)
    return [tissue.propagate(concentration) for concentration in design.grid.ascending()]


def block_open_fraction(measurements: list[PropagationMeasurement], reached_threshold: float) -> float | None:
    """Open-junction fraction at the first concentration where propagation fails."""
    return next(
        (point.open_junction_fraction for point in measurements if point.reached_fraction < reached_threshold), None
    )
