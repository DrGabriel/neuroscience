"""Test H3: which measure separates awake from anaesthetised states across agents.

A measure "predicts loss of responsiveness across agents" only if the direction of its change generalises: the
direction is learned on the other agents and applied to the held-out agent (leave one agent out).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata

from .specs import Resampling

INCREASE, DECREASE = 1.0, -1.0
MEAN_OVER_AGENTS = "mean"


@dataclass(frozen=True)
class Grouping:
    """Session and agent of every block, for resampling whole sessions within each agent."""

    sessions: np.ndarray
    agents: np.ndarray


def auc(positive: np.ndarray, negative: np.ndarray) -> float:
    """Area under the ROC curve: probability that a positive scores above a negative, ties counting half."""
    positive, negative = np.asarray(positive, float), np.asarray(negative, float)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("both classes need at least one block")
    ranks = rankdata(np.concatenate([positive, negative]))
    u = ranks[: positive.size].sum() - positive.size * (positive.size + 1) / 2
    return float(u / (positive.size * negative.size))


def learned_direction(values: np.ndarray, anaesthetised: np.ndarray) -> float:
    shift = np.median(values[anaesthetised]) - np.median(values[~anaesthetised])
    return INCREASE if shift >= 0 else DECREASE


def leave_one_agent_out_auc(values: np.ndarray, anaesthetised: np.ndarray, agents: Sequence[str]) -> dict[str, float]:
    """AUC on each held-out agent with the direction learned on the rest; 'mean' averages agents equally."""
    values, anaesthetised, agents = np.asarray(values, float), np.asarray(anaesthetised, bool), np.asarray(agents)
    per_agent = {}
    for agent in np.unique(agents):
        train, test = agents != agent, agents == agent
        direction = learned_direction(values[train], anaesthetised[train])
        scores = direction * values[test]
        per_agent[str(agent)] = auc(scores[anaesthetised[test]], scores[~anaesthetised[test]])
    per_agent[MEAN_OVER_AGENTS] = float(np.mean(list(per_agent.values())))
    return per_agent


def session_bootstrap(statistic: Callable[[np.ndarray], float], grouping: Grouping, resampling: Resampling) -> np.ndarray:
    """Resample whole sessions with replacement within each agent and recompute ``statistic(selected_indices)``."""
    sessions, agents = np.asarray(grouping.sessions), np.asarray(grouping.agents)
    by_agent = {a: np.unique(sessions[agents == a]) for a in np.unique(agents)}
    rows = {s: np.flatnonzero(sessions == s) for s in np.unique(sessions)}
    out = np.empty(resampling.count)
    for b in range(resampling.count):
        chosen = [rows[s] for members in by_agent.values() for s in resampling.rng.choice(members, size=members.size)]
        out[b] = statistic(np.concatenate(chosen))
    return out
