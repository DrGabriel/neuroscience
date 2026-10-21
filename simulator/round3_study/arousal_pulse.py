"""Prediction 15 in the percolation model: a transient arousal pulse at a fixed concentration (Section 5.4).

The model is that of Appendix B with every reference value. Its state is the giant-component share S, and one step of
the self-consistency map S -> F(pi(c, S)) is the model's only unit of time. A pulse raises the arousal drive A(c)
(Section 4.3) by a fixed amount, capped at one, for a fixed number of steps; A then returns to baseline and the map is
iterated to its steady state, as the reference solver does. Before the pulse the network is in the unconscious state
that induction leaves: taken up the induction branch to the top of the concentration grid, where quorum is lost, then
set to the test concentration and settled there, which is the state on the emergence branch.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import dpc_simulator as dpc

# The arousal drive cannot sustain more than the whole reference (Section 4.3: A = 1, the reference never weakens).
MAXIMUM_AROUSAL = 1.0
# Primary pulse: an increase of 1, which takes A to its maximum at every concentration, so that during the pulse the
# reference does not weaken (sigma_ref = 0) and the pulsed network is the model without feedback.
FULL_PULSE_INCREASE = 1.0
# Secondary pulse, reported without a verdict: an increase equal to the awake drive A0 = 0.5, which brings A back at
# least to its awake value at every concentration, since the agent removes at most A0.
AWAKE_DRIVE_PULSE_INCREASE = dpc.REFERENCE_AROUSAL_LEVEL
# The pulse lasts as many steps as the reference solver allows for convergence, so the network settles under it.
PULSE_STEPS = dpc.SOLVER_MAX_ITERATIONS
# Test concentration above the loss concentration, in EC50: c_off + 0.1.
ABOVE_LOSS_OFFSET = 0.1
# The smallest effective increase of A is found by bisection on [0, 1] to 1/1024 of the range.
SMALLEST_INCREASE_BISECTION_STEPS = 10


class TestPoint(Enum):
    """Where, relative to the seed's own bistable window, the pulse is given."""

    INSIDE_WINDOW = "midpoint of c_on and c_off"
    ABOVE_LOSS = "c_off + 0.1 EC50"


class Pulse(Enum):
    """How much the pulse raises the arousal drive."""

    FULL = "A raised by 1 (to its maximum)"
    AWAKE_DRIVE = "A raised by A0 = 0.5"


PULSE_INCREASE = {Pulse.FULL: FULL_PULSE_INCREASE, Pulse.AWAKE_DRIVE: AWAKE_DRIVE_PULSE_INCREASE}


class PulsedCoherenceModel(dpc.CoherenceModel):
    """The reference coherence model with the arousal drive raised by a fixed amount, capped at its maximum."""

    def __init__(self, scenario: dpc.Scenario, increase: float) -> None:
        super().__init__(scenario.timing, scenario.agent, scenario.state)
        self._increase = increase

    def arousal_at(self, concentration: float, coherent_fraction: float) -> float:
        return min(MAXIMUM_AROUSAL, super().arousal_at(concentration, coherent_fraction) + self._increase)


@dataclass(frozen=True)
class BistableWindow:
    """The seed's loss (c_off) and recovery (c_on) concentrations, as Appendix B.4 computes them."""

    recovery: float
    loss: float

    @property
    def width(self) -> float:
        return self.loss - self.recovery

    @property
    def midpoint(self) -> float:
        return (self.loss + self.recovery) / 2

    @property
    def relative_half_width(self) -> float:
        """Half the width as a share of the midpoint: how closely an experiment must hold the concentration."""
        return self.width / 2 / self.midpoint

    def concentration_at(self, point: TestPoint) -> float:
        return self.midpoint if point is TestPoint.INSIDE_WINDOW else self.loss + ABOVE_LOSS_OFFSET


def window_of(sweep: dpc.SweepResult) -> BistableWindow | None:
    """None when quorum is never lost, never regained, or regained at the loss concentration (no window)."""
    loss, recovery = sweep.loss_concentration, sweep.recovery_concentration
    if loss is None or recovery is None or loss <= recovery:
        return None
    return BistableWindow(recovery, loss)


@dataclass(frozen=True)
class FixedPointMap:
    """One step of S -> F(pi(c, S)) at a fixed concentration, for one coherence model."""

    curve: dpc.PercolationCurve
    coherence: dpc.CoherenceModel
    concentration: float

    def step(self, fraction: float) -> float:
        return self.curve.giant_fraction(self.coherence.coherence_probability(self.concentration, fraction))

    def settle(self, fraction: float) -> float:
        """The steady state reached from fraction, exactly as the reference solver finds it."""
        return dpc.CoherentCoreSolver(self.curve, self.coherence).solve(self.concentration, fraction)


@dataclass(frozen=True)
class PulseTrace:
    """The state at the end of a pulse and the first step at which it reached the quorum (None if it never did)."""

    final_fraction: float
    first_quorum_step: int | None


def apply_pulse(pulsed: FixedPointMap, start: float, quorum: float) -> PulseTrace:
    """PULSE_STEPS steps of the pulsed map from start."""
    fraction, first_quorum_step = start, None
    for step in range(1, PULSE_STEPS + 1):
        fraction = pulsed.step(fraction)
        if first_quorum_step is None and fraction >= quorum:
            first_quorum_step = step
    return PulseTrace(fraction, first_quorum_step)


@dataclass(frozen=True)
class PulseOutcome:
    """The state before, at the end of and after one pulse, against the quorum."""

    concentration: float
    before: float
    end_of_pulse: float
    first_quorum_step: int | None
    after: float
    quorum_fraction: float

    @property
    def starts_unconscious(self) -> bool:
        return self.before < self.quorum_fraction

    @property
    def woken_by_pulse(self) -> bool:
        return self.end_of_pulse >= self.quorum_fraction

    @property
    def quorum_persists(self) -> bool:
        return self.after >= self.quorum_fraction


@dataclass(frozen=True)
class PulseSetting:
    """Where and how strongly one seed's network is pulsed, from the state that induction left."""

    concentration: float
    increase: float
    induction_end: float


def pulse_outcome(curve: dpc.PercolationCurve, scenario: dpc.Scenario, setting: PulseSetting) -> PulseOutcome:
    baseline = FixedPointMap(curve, dpc.CoherenceModel(scenario.timing, scenario.agent, scenario.state), setting.concentration)
    pulsed = FixedPointMap(curve, PulsedCoherenceModel(scenario, setting.increase), setting.concentration)
    before = baseline.settle(setting.induction_end)
    trace = apply_pulse(pulsed, before, scenario.quorum_fraction)
    return PulseOutcome(
        concentration=setting.concentration,
        before=before,
        end_of_pulse=trace.final_fraction,
        first_quorum_step=trace.first_quorum_step,
        after=baseline.settle(trace.final_fraction),
        quorum_fraction=scenario.quorum_fraction,
    )


@dataclass(frozen=True)
class IncreaseProbe:
    """Where to search for the smallest pulse that achieves an outcome, from the state that induction left."""

    concentration: float
    induction_end: float
    achieves: Callable[[PulseOutcome], bool]


def smallest_increase(curve: dpc.PercolationCurve, scenario: dpc.Scenario, probe: IncreaseProbe) -> float | None:
    """Smallest increase of A, by bisection, at which the pulse achieves the outcome; None if even the full pulse does not.

    The outcomes searched for become no less likely as the increase grows, since a larger drive never lowers pi.
    """

    def achieved(increase: float) -> bool:
        return probe.achieves(pulse_outcome(curve, scenario, PulseSetting(probe.concentration, increase, probe.induction_end)))

    if not achieved(FULL_PULSE_INCREASE):
        return None
    return dpc.smallest_crossing(achieved, SMALLEST_INCREASE_BISECTION_STEPS)
