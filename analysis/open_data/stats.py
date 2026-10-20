"""Family-wise correction, equivalence tests and the three-way verdict used by every primary test."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from scipy.stats import t as student_t
from scipy.stats import wilcoxon

from .settings import FAMILY

MIN_SAMPLE_FOR_TOST = 2
NO_EVIDENCE_P = 1.0
CERTAIN_P = 0.0


class Verdict(StrEnum):
    SUPPORTS = "supports DPC"
    AGAINST = "counts against DPC"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class Evidence:
    """What a verdict needs: the corrected p-value, the effect, its smallest size of interest and the equivalence p."""

    adjusted_p: float
    effect: float
    smallest_effect: float
    equivalence_p: float


def holm(p_values: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values, monotone in the order of the raw p-values."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    m = len(ordered)
    adjusted, running = {}, 0.0
    for rank, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def wilcoxon_greater(values: np.ndarray, reference: float = 0.0) -> float:
    differences = np.asarray(values, float) - reference
    if np.all(differences == 0):
        return NO_EVIDENCE_P
    return float(wilcoxon(differences, alternative="greater").pvalue)


def tost_p(values: np.ndarray, lower: float, upper: float) -> float:
    """Two one-sided t-tests (Lakens et al., 2018): small p means the mean lies inside (lower, upper)."""
    values = np.asarray(values, float)
    n = values.size
    if n < MIN_SAMPLE_FOR_TOST:
        return NO_EVIDENCE_P
    se = values.std(ddof=1) / np.sqrt(n)
    if se == 0:
        return CERTAIN_P if lower < values.mean() < upper else NO_EVIDENCE_P
    p_lower = student_t.sf((values.mean() - lower) / se, n - 1)
    p_upper = student_t.cdf((values.mean() - upper) / se, n - 1)
    return float(max(p_lower, p_upper))


def verdict(evidence: Evidence, alpha: float = FAMILY.alpha) -> Verdict:
    """Supports: significant and at least the smallest effect of interest. Against: shown to be smaller than it."""
    if evidence.adjusted_p < alpha and evidence.effect >= evidence.smallest_effect:
        return Verdict.SUPPORTS
    if evidence.equivalence_p < alpha or evidence.effect <= -evidence.smallest_effect:
        return Verdict.AGAINST
    return Verdict.INCONCLUSIVE
