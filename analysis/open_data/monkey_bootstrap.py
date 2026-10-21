"""Monkey-level bootstrap for H2b and H3 (round 3, exploratory sensitivity analysis; Appendix E.15).

The committed H2b test treats the sessions as independent (a Wilcoxon test over sessions), and the committed H3
bootstrap resamples sessions within agent. Sessions of one monkey are not independent, so here the monkeys are
resampled first and then the sessions within each drawn monkey: for H2b over all sessions; for H3 within each agent
(the monkeys that received that agent, then that monkey's sessions with it), so that every agent is present in every
resample and the leave-one-agent-out statistic stays defined. The statistics are the committed ones, recomputed on
each resample; the session-level results are recomputed beside them with the committed group functions.

Only per-session result files are read, never a recording. Usage, from the repository root:
    .venv/bin/python -E -s -m analysis.open_data.monkey_bootstrap --inputs <folder or list> --out <json>
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import exploratory_group, group, outputs, run
from .constants import Dataset, Hypothesis, State
from .group import INDICATORS, LAG_VARIABILITY, LOCAL_POWER, MEAN_LAG, STANDARDISED_SUFFIX
from .outputs import Output
from .round3_settings import MONKEY
from .settings import LAG, SEED, WARNING
from .specs import Resampling

INFERENCE_UNIT = "monkey"
ONE_STRATUM = "all sessions"
SESSION_FIELD, BLOCK_SESSION_FIELD, MONKEY_FIELD, AGENT_FIELD = "experiment", "session_id", "monkey", "agent"
LOWER_QUANTILE, UPPER_QUANTILE = (1 - LAG.confidence) / 2, (1 + LAG.confidence) / 2
Layout = dict[str, dict[str, dict[str, np.ndarray]]]
Statistic = Callable[[np.ndarray], float]


@dataclass(frozen=True)
class Nesting:
    """For every row: its stratum (kept fixed), the outer unit resampled first (monkey) and the inner unit (session)."""

    strata: np.ndarray
    outer: np.ndarray
    inner: np.ndarray


@dataclass(frozen=True)
class Target:
    """A statistic of selected rows, its smallest effect of interest, and how its rows nest."""

    statistic: Statistic
    smallest_effect: float
    nesting: Nesting


def nested_layout(nesting: Nesting) -> Layout:
    """stratum -> monkey -> session -> row indices, with every label sorted so that row order does not matter."""
    keys = list(zip(*(np.asarray(a).astype(str) for a in (nesting.strata, nesting.outer, nesting.inner)), strict=True))
    layout: Layout = {}
    for stratum, unit, member in sorted(set(keys)):
        rows = np.array([k for k, key in enumerate(keys) if key == (stratum, unit, member)])
        layout.setdefault(stratum, {}).setdefault(unit, {})[member] = rows
    return layout


def _draw(labels: list[str], rng: np.random.Generator) -> list[str]:
    return [labels[k] for k in rng.integers(len(labels), size=len(labels))]


def two_stage_rows(layout: Layout, rng: np.random.Generator) -> np.ndarray:
    """In each stratum: draw its monkeys with replacement, then each drawn monkey's sessions with replacement."""
    chosen = []
    for units in layout.values():
        for unit in _draw(list(units), rng):
            sessions = units[unit]
            chosen += [sessions[s] for s in _draw(list(sessions), rng)]
    return np.concatenate(chosen)


def two_stage_bootstrap(statistic: Statistic, layout: Layout, resampling: Resampling) -> np.ndarray:
    return np.array([statistic(two_stage_rows(layout, resampling.rng)) for _ in range(resampling.count)])


def summarise(target: Target, resampling: Resampling) -> dict:
    """Point estimate on every row, the percentile interval and the one-sided shares, as the committed H3 reports them."""
    layout = nested_layout(target.nesting)
    boot = two_stage_bootstrap(target.statistic, layout, resampling)
    lower, upper = np.quantile(boot, [LOWER_QUANTILE, UPPER_QUANTILE])
    return {
        "effect": target.statistic(np.arange(target.nesting.inner.size)),
        "smallest_effect": target.smallest_effect,
        "confidence_interval": [float(lower), float(upper)],
        "share_at_or_below_zero": group._bootstrap_share(boot, at_or_below=0.0),
        "share_at_or_above_smallest_effect": group._bootstrap_share(boot, at_or_above=target.smallest_effect),
        "resamples": int(boot.size),
        "monkeys_per_stratum": {stratum: len(units) for stratum, units in layout.items()},
        "sessions": int(np.unique(target.nesting.inner).size),
    }


def h2b_target(sessions: list[dict]) -> Target:
    """The committed H2b effect: the smaller of the two median Kendall taus, over the selected sessions."""
    taus = [np.array([s[Hypothesis.H2b][k]["tau"] for s in sessions]) for k in INDICATORS]
    labels = {f: np.array([s[f] for s in sessions]) for f in (MONKEY_FIELD, SESSION_FIELD)}

    def smaller_median(rows: np.ndarray) -> float:
        return float(min(np.median(t[rows]) for t in taus))

    nesting = Nesting(np.full(len(sessions), ONE_STRATUM), labels[MONKEY_FIELD], labels[SESSION_FIELD])
    return Target(smaller_median, WARNING.smallest_kendall_tau, nesting)


def h3_target(blocks: list[dict]) -> Target:
    """The committed H3 statistic D on the selected blocks, monkeys resampled within agent."""
    agents = np.array([b[AGENT_FIELD] for b in blocks])
    anaesthetised = np.array([b["state"] == State.ANAESTHETISED for b in blocks])
    values = {f: np.array([b[f"{f}{STANDARDISED_SUFFIX}"] for b in blocks]) for f in (LAG_VARIABILITY, MEAN_LAG, LOCAL_POWER)}
    difference = group._auc_difference(values, anaesthetised, agents)
    nesting = Nesting(agents, np.array([b[MONKEY_FIELD] for b in blocks]), np.array([b[BLOCK_SESSION_FIELD] for b in blocks]))
    return Target(lambda rows: float(difference(rows)), LAG.smallest_auc_difference, nesting)


def analysed_sessions(source: Path) -> list[dict]:
    """The committed group step's Neurotycho inputs: every gamma-band session file except sleep."""
    return [r for r in exploratory_group.load_listed(source, Dataset.NEUROTYCHO) if r[AGENT_FIELD] != run.SLEEP]


def monkey_level(sessions: list[dict], resamples: int) -> dict:
    """Session-level results as committed, and the monkey-level bootstrap beside them; one generator for both tests."""
    h2b_sessions = [s for s in sessions if not outputs.is_excluded(s[Hypothesis.H2b])]
    blocks = [b for s in sessions for b in s[run.H3_BLOCKS]]
    resampling = Resampling(resamples, np.random.default_rng(SEED))
    return {
        "inference_unit": INFERENCE_UNIT,
        Hypothesis.H2b: {
            "session_level": group.h2_critical_slowing(outputs.included([s[Hypothesis.H2b] for s in h2b_sessions])),
            "monkey_level": summarise(h2b_target(h2b_sessions), resampling),
        },
        Hypothesis.H3: {
            "session_level": group.h3_lag_variability(blocks),
            "monkey_level": summarise(h3_target(blocks), resampling),
        },
    }


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument("--inputs", required=True, help="a results folder, or a list of result files (exploratory/group_inputs.txt)")
    top.add_argument("--out", required=True)
    top.add_argument("--resamples", type=int, default=MONKEY.resamples)
    return top


def main(argv: list[str] | None = None) -> None:
    arguments = parser().parse_args(argv)
    started = time.time()
    payload = monkey_level(analysed_sessions(Path(arguments.inputs)), arguments.resamples)
    outputs.write(Output(Path(arguments.out), arguments, started), {"settings_round3": asdict(MONKEY), **payload})


if __name__ == "__main__":
    main()
