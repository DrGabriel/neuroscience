"""Family-wise verdicts: Holm across the primary tests, then each hypothesis's verdict rule.

H1 adds the measurement gate, the 'intact through LOR' falsifier and the threshold-sensitivity requirement; H4 claims
support only if every effect-site series holds and judges 'counts against' on the dataset's own series.
"""

from __future__ import annotations

from collections.abc import Callable

from . import stats
from .constants import Hypothesis
from .settings import FAMILY
from .stats import Evidence, Verdict

NOT_EVALUABLE = "not evaluable: BOLD coupling did not fall with concentration"
P_VALUE_FIELD = {Hypothesis.H4: "worst_case_p"}
DEFAULT_P_VALUE_FIELD = "p_value"


def _evidence(result: dict, adjusted_p: float) -> Evidence:
    return Evidence(adjusted_p, result["effect"], result["smallest_effect"], result["equivalence_p"])


def general_verdict(result: dict, adjusted_p: float) -> str:
    return stats.verdict(_evidence(result, adjusted_p)).value


def h1_verdict(result: dict, adjusted_p: float) -> str:
    if result.get("coupling_falls") is False:
        return NOT_EVALUABLE
    if result.get("intact_through_lor"):
        return Verdict.AGAINST.value
    verdict = stats.verdict(_evidence(result, adjusted_p))
    robust = all(m > 0 for m in result.get("sensitivity_median_log_ratio", {}).values())
    return Verdict.INCONCLUSIVE.value if verdict is Verdict.SUPPORTS and not robust else verdict.value


def h4_verdict(result: dict, adjusted_worst_p: float) -> str:
    """Supports only if every effect-site variant holds; counts against judged on the provided effect-site series."""
    if adjusted_worst_p < FAMILY.alpha and result["min_effect"] >= result["smallest_effect"]:
        return Verdict.SUPPORTS.value
    if result["equivalence_p"] < FAMILY.alpha or result["effect"] <= -result["smallest_effect"]:
        return Verdict.AGAINST.value
    return Verdict.INCONCLUSIVE.value


VERDICT_RULES: dict[Hypothesis, Callable[[dict, float], str]] = {Hypothesis.H1: h1_verdict, Hypothesis.H4: h4_verdict}


def family_verdicts(primary: dict[str, dict]) -> dict[str, dict]:
    """Holm across the primary tests, then the verdict rule of each hypothesis."""
    p_values = {name: r[P_VALUE_FIELD.get(Hypothesis(name), DEFAULT_P_VALUE_FIELD)] for name, r in primary.items()}
    adjusted = stats.holm(p_values)
    out = {}
    for name, result in primary.items():
        rule = VERDICT_RULES.get(Hypothesis(name), general_verdict)
        out[name] = {**result, "adjusted_p": adjusted[name], "verdict": rule(result, adjusted[name])}
    return out
