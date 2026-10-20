"""Group-level summaries for the primary tests H1 to H4 and the partial test H5a.

Each function takes the per-subject (or per-session) results written by ``run.py`` and returns the raw one-sided
p-value, the effect estimate on the scale of its smallest effect of interest and the equivalence p-value, with the
details each verdict rule needs. ``verdicts.family_verdicts`` turns them into verdicts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.stats import spearmanr

from . import classification, stats
from .classification import MEAN_OVER_AGENTS, Grouping
from .constants import PROVIDED_EFFECT_SITE, State
from .settings import EVOKED, HYSTERESIS, LAG, SEED, SHAPE, WARNING
from .specs import Resampling

NOT_TESTED_FOR_EQUIVALENCE = 1.0
MIN_CORRELATION_PAIRS = 3
INDICATORS = ("variance", "autocorrelation")
LAG_VARIABILITY, MEAN_LAG, LOCAL_POWER = "lag_variability_ms", "mean_lag_ms", "log_power"
STANDARDISED_SUFFIX = "_z"
STEEPNESS_RATIO = "ratio_to_null_median"


@dataclass(frozen=True)
class TestSummary:
    p_value: float
    effect: float
    smallest_effect: float
    equivalence_p: float
    n: int

    def with_details(self, **details) -> dict:
        return {**asdict(self), **details}


def one_sample_summary(values: np.ndarray, smallest_effect: float) -> TestSummary:
    """One-sided Wilcoxon test of values > 0, their median, and the equivalence test within +/- the SESOI."""
    values = np.asarray(values, float)
    equivalence = stats.tost_p(values, -smallest_effect, smallest_effect)
    return TestSummary(stats.wilcoxon_greater(values), float(np.median(values)), float(smallest_effect), equivalence, int(values.size))


def sensitivity_medians(subjects: list[dict]) -> dict[str, float]:
    keys = subjects[0].get("sensitivity", {}).keys()
    return {k: float(np.median(np.log([s["sensitivity"][k]["null_a_linear_decline"][STEEPNESS_RATIO] for s in subjects]))) for k in keys}


def _h1_details(subjects: list[dict]) -> dict:
    intact = [s["post_lor_share_of_awake"] for s in subjects if s.get("post_lor_share_of_awake") is not None]
    return {
        "intact_through_lor": bool(intact and np.median(intact) >= SHAPE.intact_share),
        "coupling_falls": bool(np.median([s["coupling_deep_over_awake"] for s in subjects]) < SHAPE.coupling_fall_gate),
        "sensitivity_median_log_ratio": sensitivity_medians(subjects),
        "sigmoid_preferred": int(sum(s["observed"]["delta_bic"] <= -SHAPE.bic_margin for s in subjects)),
    }


def h1_threshold(subjects: list[dict]) -> dict:
    """Steepness against null A (log ratio), with the details of the 'intact through LOR' falsifier and the gate."""
    log_ratio = np.log([s["null_a_linear_decline"][STEEPNESS_RATIO] for s in subjects])
    return one_sample_summary(log_ratio, np.log(SHAPE.smallest_steepness_ratio)).with_details(**_h1_details(subjects))


def _without_equivalence(values: np.ndarray, smallest_effect: float) -> dict:
    return asdict(TestSummary(stats.wilcoxon_greater(values), float(np.median(values)), float(smallest_effect), NOT_TESTED_FOR_EQUIVALENCE, len(values)))


def h1_secondary(subjects: list[dict]) -> dict:
    """Reported without verdict: null B, steepness relative to local amplitude, and coincidence of the midpoint with LOR."""
    null_b = np.log([s["null_b_observed_coupling"][STEEPNESS_RATIO] for s in subjects])
    local = np.log([s["local_slope_ratio"] for s in subjects])
    offsets = np.array([s["c50_minus_lor"] for s in subjects if s.get("c50_minus_lor") is not None])
    window = SHAPE.lor_coincidence_ug_per_ml
    return {
        "null_b": _without_equivalence(null_b, np.log(SHAPE.smallest_steepness_ratio)),
        "local_amplitude": _without_equivalence(local, np.log(SHAPE.smallest_local_slope_ratio)),
        "midpoint_minus_lor_ug_per_ml": {
            "median": float(np.median(offsets)) if offsets.size else None,
            "equivalence_p": stats.tost_p(offsets, -window, window),
            "n": int(offsets.size),
        },
    }


def h2_critical_slowing(results: list[dict]) -> dict:
    """Both indicators must rise (intersection-union: the larger of the two p-values, the smaller of the two medians)."""
    sesoi = WARNING.smallest_kendall_tau
    per_indicator = {k: one_sample_summary(np.array([r[k]["tau"] for r in results]), sesoi) for k in INDICATORS}
    combined = TestSummary(
        max(s.p_value for s in per_indicator.values()),
        float(min(s.effect for s in per_indicator.values())),
        sesoi,
        max(s.equivalence_p for s in per_indicator.values()),
        len(results),
    )
    return combined.with_details(median_tau={k: s.effect for k, s in per_indicator.items()})


def _auc_difference(values: dict[str, np.ndarray], anaesthetised: np.ndarray, agents: np.ndarray):
    def difference(rows: np.ndarray) -> float:
        aucs = {f: classification.leave_one_agent_out_auc(v[rows], anaesthetised[rows], agents[rows])[MEAN_OVER_AGENTS] for f, v in values.items()}
        return aucs[LAG_VARIABILITY] - max(aucs[MEAN_LAG], aucs[LOCAL_POWER])

    return difference


def _bootstrap_share(boot: np.ndarray, at_or_below: float | None = None, at_or_above: float | None = None) -> float:
    hits = np.sum(boot <= at_or_below) if at_or_below is not None else np.sum(boot >= at_or_above)
    return float((1 + hits) / (1 + boot.size))


def h3_lag_variability(blocks: list[dict], n_resamples: int = LAG.bootstrap_resamples) -> dict:
    """Leave-one-agent-out AUC of lag variability minus the better of mean lag and local power, session bootstrap."""
    agents = np.array([b["agent"] for b in blocks])
    sessions = np.array([b["session_id"] for b in blocks])
    anaesthetised = np.array([b["state"] == State.ANAESTHETISED for b in blocks])
    values = {f: np.array([b[f"{f}{STANDARDISED_SUFFIX}"] for b in blocks]) for f in (LAG_VARIABILITY, MEAN_LAG, LOCAL_POWER)}
    difference = _auc_difference(values, anaesthetised, agents)
    boot = classification.session_bootstrap(difference, Grouping(sessions, agents), Resampling(n_resamples, np.random.default_rng(SEED)))
    lower, upper = np.quantile(boot, [(1 - LAG.confidence) / 2, (1 + LAG.confidence) / 2])
    summary = TestSummary(
        _bootstrap_share(boot, at_or_below=0.0),
        difference(np.arange(len(blocks))),
        LAG.smallest_auc_difference,
        _bootstrap_share(boot, at_or_above=LAG.smallest_auc_difference),
        int(np.unique(sessions).size),
    )
    per_feature = {f: classification.leave_one_agent_out_auc(v, anaesthetised, agents) for f, v in values.items()}
    return summary.with_details(confidence_interval=[float(lower), float(upper)], per_feature_auc=per_feature)


def network_behaviour_correlation(subjects: list[dict]) -> float | None:
    provided = [s[PROVIDED_EFFECT_SITE] for s in subjects]
    paired = [(p["network_ratio"], p["behavioural_ratio"]) for p in provided if p["behavioural_ratio"]]
    columns = list(zip(*paired, strict=True))
    varied = len(paired) >= MIN_CORRELATION_PAIRS and all(len(set(column)) > 1 for column in columns)
    return float(spearmanr(*columns).statistic) if varied else None


def h4_hysteresis(subjects: list[dict]) -> dict:
    """Network hysteresis ratio, claimed only if it holds at the provided effect-site series and every ke0."""
    sesoi = np.log(HYSTERESIS.smallest_ratio)
    per_variant = {}
    for name in subjects[0]:
        per_variant[name] = asdict(one_sample_summary(np.log([s[name]["network_ratio"] for s in subjects]), sesoi))
    return {
        **per_variant[PROVIDED_EFFECT_SITE],
        "min_effect": min(v["effect"] for v in per_variant.values()),
        "worst_case_p": max(v["p_value"] for v in per_variant.values()),
        "variants": per_variant,
        "network_behaviour_spearman": network_behaviour_correlation(subjects),
    }


def h5a_latency(patients: list[dict]) -> dict:
    """Per-patient median of log(SD ratio) - log(mean latency ratio); positive when variability rises more."""
    values = np.array([p["median_relative_change"] for p in patients if p["median_relative_change"] is not None])
    if values.size == 0:
        raise ValueError("no patient has a connection measurable in both states")
    return asdict(one_sample_summary(values, EVOKED.smallest_log_ratio))
