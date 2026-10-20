"""One seed of one condition read with the DPC readout, and the pairing of runs that the paired tests compare."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from operator import attrgetter
from typing import Callable, Sequence

import calibration as cal
import dpc_readout as readout
import dpc_simulator as dpc
import reporting
import species_study as species
from readout_study.settings import READOUT


class Reading(Enum):
    """The ways a cycle's quorum is read; the first is the primary reading of P2 and P3."""

    SHARED_RHYTHM = "undirected giant component, timed against the shared rhythm"
    STRONGLY_CONNECTED = "strongly connected component, timed against the shared rhythm"
    RECEIVER_PHASE = "undirected giant component, timed at the receiver"
    JITTER_ONLY = "undirected giant component of the timing draws alone (static percolation)"


READING_SUMMARY: dict[Reading, Callable[[readout.ConcentrationReadout], readout.ComponentSummary]] = {
    Reading.SHARED_RHYTHM: attrgetter("undirected"),
    Reading.STRONGLY_CONNECTED: attrgetter("strongly_connected"),
    Reading.RECEIVER_PHASE: attrgetter("receiver_phase"),
    Reading.JITTER_ONLY: attrgetter("jitter_only"),
}


@dataclass(frozen=True)
class ReadoutRun:
    """One seed of one condition: the coherence summary every study records, and the DPC readout of each step."""

    coherence: species.RunSummary
    induction: tuple[readout.ConcentrationReadout, ...]
    emergence: tuple[readout.ConcentrationReadout, ...]

    @property
    def organism(self) -> str:
        return self.coherence.organism

    @property
    def condition(self) -> str:
        return self.coherence.condition

    @property
    def seed(self) -> int:
        return self.coherence.seed

    @property
    def dpc_loss_concentration(self) -> float | None:
        return readout.dpc_loss_concentration(self.induction)

    @property
    def dpc_recovery_concentration(self) -> float | None:
        return readout.dpc_recovery_concentration(self.emergence)

    def loss_under(self, reading: Reading) -> float | None:
        summary = READING_SUMMARY[reading]
        return dpc.loss_concentration(self.induction, lambda point: summary(point).holds_quorum)

    def readout_at(self, concentration: float | None) -> readout.ConcentrationReadout | None:
        return None if concentration is None else next(p for p in self.induction if p.concentration == concentration)

    @property
    def last_conscious(self) -> readout.ConcentrationReadout | None:
        """The readout at the last concentration of induction with DPC quorum, before it is lost."""
        return self.readout_at(self.dpc_loss_concentration)

    @property
    def inertia_ratio(self) -> float | None:
        """Loss over recovery concentration in the DPC readout; None unless quorum is lost and returns above zero."""
        loss, recovery = self.dpc_loss_concentration, self.dpc_recovery_concentration
        return None if loss is None or not recovery else loss / recovery


def run_readout_task(task: species.RunTask) -> ReadoutRun:
    started = time.perf_counter()
    sweep = readout.run_with_readout(species.connectome_for(task), species.design_for(task), READOUT)
    return ReadoutRun(species.summarise(task, sweep.record, time.perf_counter() - started), sweep.induction, sweep.emergence)


def runs_of(runs: Sequence[ReadoutRun], organism: str, condition: str) -> list[ReadoutRun]:
    return [r for r in runs if r.organism == organism and r.condition == condition]


def concentration_step(organism: str) -> float:
    return cal.ORGANISMS[organism].grid_step(cal.CONCENTRATION_GRID.step)


@dataclass(frozen=True)
class RunPair:
    """Two runs of the same seed, compared by a paired test."""

    first: ReadoutRun
    second: ReadoutRun


def pairs_by_seed(firsts: Sequence[ReadoutRun], seconds: Sequence[ReadoutRun]) -> list[RunPair]:
    by_seed = {run.seed: run for run in seconds}
    return [RunPair(run, by_seed[run.seed]) for run in firsts if run.seed in by_seed]


@dataclass(frozen=True)
class PairedTest:
    """A test comparing each seed's run in one condition with the same seed's run in another, on one organism."""

    check: reporting.Check[RunPair]
    first: str
    second: str


def evaluate_paired(tests: Sequence[PairedTest], runs: Sequence[ReadoutRun], organisms: Sequence[str]) -> list[reporting.CheckOutcome]:
    outcomes = []
    for test in tests:
        groups = {cal.ORGANISMS[o].display_name: pairs_by_seed(runs_of(runs, o, test.first), runs_of(runs, o, test.second)) for o in organisms}
        outcomes += [o for o in reporting.evaluate((test.check,), groups) if o.runs_applicable > 0]
    return outcomes
