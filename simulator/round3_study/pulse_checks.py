"""Analysis A: one seed's measurement, the tests P15a and P15b, and the pulse of the awake drive reported without one."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import dpc_simulator as dpc
import reporting
import validation_study as validation
from round3_study.arousal_pulse import (
    PULSE_INCREASE,
    BistableWindow,
    IncreaseProbe,
    Pulse,
    PulseOutcome,
    PulseSetting,
    TestPoint,
    pulse_outcome,
    smallest_increase,
    window_of,
)

Condition = tuple[TestPoint, Pulse]
CONDITIONS: tuple[Condition, ...] = tuple((point, pulse) for pulse in Pulse for point in TestPoint)


def condition_key(condition: Condition) -> str:
    point, pulse = condition
    return f"{point.name.lower()}, {pulse.name.lower()}"


def woken_and_persists(outcome: PulseOutcome | None) -> bool:
    """Unconscious before the pulse, quorum during it, and quorum kept after it; False without a window."""
    return outcome is not None and outcome.starts_unconscious and outcome.woken_by_pulse and outcome.quorum_persists


def woken_and_lost_again(outcome: PulseOutcome | None) -> bool:
    """Unconscious before the pulse, quorum during it, and quorum lost again after it; False without a window."""
    return outcome is not None and outcome.starts_unconscious and outcome.woken_by_pulse and not outcome.quorum_persists


def woken(outcome: PulseOutcome) -> bool:
    return outcome.starts_unconscious and outcome.woken_by_pulse


# Reported without a verdict: the smallest increase of A that leaves quorum persisting inside the window, and the
# smallest that restores quorum during the pulse above the loss concentration.
SMALLEST_INCREASES = {
    "persisting quorum inside the window": (TestPoint.INSIDE_WINDOW, woken_and_persists),
    "quorum during the pulse above c_off": (TestPoint.ABOVE_LOSS, woken),
}


@dataclass(frozen=True)
class PulseMeasurement:
    """One seed at one network size: its bistable window (None if it has none), every pulse outcome and the smallest
    effective increases of A."""

    node_count: int
    seed: int
    window: BistableWindow | None
    outcomes: dict[str, PulseOutcome]
    smallest_increases: dict[str, float | None]
    duration_seconds: float


@dataclass(frozen=True)
class PulseStart:
    """The seed's window and the state that induction left at the top of the concentration grid."""

    window: BistableWindow
    induction_end: float

    def setting(self, condition: Condition) -> PulseSetting:
        point, pulse = condition
        return PulseSetting(self.window.concentration_at(point), PULSE_INCREASE[pulse], self.induction_end)

    def probe(self, point: TestPoint, achieves: Callable[[PulseOutcome], bool]) -> IncreaseProbe:
        return IncreaseProbe(self.window.concentration_at(point), self.induction_end, achieves)


def pulse_outcomes(curve: dpc.PercolationCurve, scenario: dpc.Scenario, start: PulseStart) -> dict[str, PulseOutcome]:
    return {condition_key(condition): pulse_outcome(curve, scenario, start.setting(condition)) for condition in CONDITIONS}


def smallest_increases(curve: dpc.PercolationCurve, scenario: dpc.Scenario, start: PulseStart) -> dict[str, float | None]:
    return {name: smallest_increase(curve, scenario, start.probe(point, achieves)) for name, (point, achieves) in SMALLEST_INCREASES.items()}


def measure_seed(task: validation.SeedTask) -> PulseMeasurement:
    """The reference sweep gives the window; each pulse starts from the state that induction left."""
    started = time.perf_counter()
    scenario = validation.sized(dpc.REFERENCE_SCENARIO, task)
    curve = dpc.build_curve(scenario)
    sweep = dpc.run_on_curve(curve, scenario)
    window = window_of(sweep)
    if window is None:
        return PulseMeasurement(task.node_count, task.seed, None, {}, {}, time.perf_counter() - started)
    start = PulseStart(window, sweep.induction[-1].coherent_fraction)
    outcomes, increases = pulse_outcomes(curve, scenario, start), smallest_increases(curve, scenario, start)
    return PulseMeasurement(task.node_count, task.seed, window, outcomes, increases, time.perf_counter() - started)


def outcome_of(measurement: PulseMeasurement, condition: Condition) -> PulseOutcome | None:
    return measurement.outcomes.get(condition_key(condition))


INSIDE_FULL, ABOVE_FULL = (TestPoint.INSIDE_WINDOW, Pulse.FULL), (TestPoint.ABOVE_LOSS, Pulse.FULL)
INSIDE_AWAKE, ABOVE_AWAKE = (TestPoint.INSIDE_WINDOW, Pulse.AWAKE_DRIVE), (TestPoint.ABOVE_LOSS, Pulse.AWAKE_DRIVE)

TESTS = (
    reporting.Check(
        "P15a",
        "Inside the bistable window (midpoint of c_on and c_off), quorum restored by the arousal pulse persists after it",
        lambda m: woken_and_persists(outcome_of(m, INSIDE_FULL)),
        reporting.CONSISTENCY_CHECK,
    ),
    reporting.Check(
        "P15b",
        "Above the loss concentration (c_off + 0.1 EC50), quorum restored by the arousal pulse is lost again after it",
        lambda m: woken_and_lost_again(outcome_of(m, ABOVE_FULL)),
        reporting.CONSISTENCY_CHECK,
    ),
)

# The same readings with a pulse of the awake drive only; reported, not part of the verdict.
OBSERVATIONS = (
    reporting.Check(
        "P15a-A0", "As P15a, with the arousal drive raised by A0 = 0.5 instead of 1",
        lambda m: woken_and_persists(outcome_of(m, INSIDE_AWAKE)),
    ),
    reporting.Check(
        "P15b-A0", "As P15b, with the arousal drive raised by A0 = 0.5 instead of 1",
        lambda m: woken_and_lost_again(outcome_of(m, ABOVE_AWAKE)),
    ),
    reporting.Check(
        "W", "The seed has a bistable window (quorum lost on induction and regained on emergence at a lower concentration)",
        lambda m: m.window is not None,
    ),
)
