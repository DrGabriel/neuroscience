"""Tests H1 (threshold shape), H2a (critical slowing down) and H4 (hysteresis) on the Michigan propofol fMRI dataset.

Run 1 of the imagery task is the awake reference (before the infusion, concentration zero throughout), run 2 the
induction (stepped effect-site concentration, loss of responsiveness marked), run 3 the emergence after the infusion
stops (return of responsiveness marked) and run 4 its continuation. Run 2 itself has under a minute at zero
concentration (28 volumes in sub-02), too little for one window, so the awake reference comes from run 1. Task-evoked
activity is regressed out with the dataset's own instruction regressors, and volumes with framewise displacement above
the limit are censored.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from . import early_warning, hysteresis, network, threshold_shape
from .constants import PROVIDED_EFFECT_SITE
from .hysteresis import EffectSiteModel
from .loaders import MichiganRun
from .settings import FMRI, HYSTERESIS, SHAPE
from .specs import EdgeTest, Resampling, SurrogateSpec

AWAKE_RUN, INDUCTION_RUN, EMERGENCE_RUNS = 1, 2, (3, 4)
TABLE_KEYS = ("run", "start_volume", "concentration", "giant_component", "mean_coupling", "amplitude")


@dataclass(frozen=True)
class Subject:
    """One subject's awake reference, induction and emergence runs."""

    awake: MichiganRun
    induction: MichiganRun
    emergence: tuple[MichiganRun, ...]


@dataclass(frozen=True)
class Events:
    """Loss (run 2) and return (run 3) of responsiveness, in volumes; None when the dataset has none."""

    lor_volume: int | None
    ror_volume: int | None


@dataclass(frozen=True)
class NullSpec:
    """Number of smooth-decline null realisations and the edge test they go through."""

    realisations: int
    test: EdgeTest


def edge_test(rng: np.random.Generator, alpha: float = FMRI.edge_alpha) -> EdgeTest:
    return EdgeTest(SurrogateSpec(alpha, FMRI.surrogates_per_window), rng)


def regress_out(timeseries: np.ndarray, confounds: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(confounds.shape[0]), confounds])
    beta, *_ = np.linalg.lstsq(design, timeseries.T, rcond=None)
    return (timeseries.T - design @ beta).T


def window_starts(n_volumes: int) -> range:
    return range(0, n_volumes - FMRI.window_trs + 1, FMRI.step_trs)


def clean_run(run: MichiganRun) -> tuple[np.ndarray, np.ndarray]:
    """Residual BOLD after removing instruction-evoked activity, and the mask of volumes kept after censoring."""
    keep = run.framewise_displacement <= FMRI.framewise_displacement_limit_mm
    return regress_out(run.timeseries, run.instructions), keep


def _window_measures(data: np.ndarray, test: EdgeTest) -> dict:
    stats = network.correlation_network(data, test)
    return {"giant_component": stats["giant_component"], "mean_coupling": stats["mean_coupling"], "amplitude": float(np.mean(data.std(axis=1)))}


def window_table(run: MichiganRun, concentration: np.ndarray, test: EdgeTest) -> dict:
    """Giant component, mean coupling and local amplitude in each sliding window, with its mean concentration."""
    residual, keep = clean_run(run)
    rows, windows = [], []
    for start in window_starts(residual.shape[1]):
        span = slice(start, start + FMRI.window_trs)
        if 1.0 - keep[span].mean() > FMRI.max_censored_share:
            continue
        data = residual[:, span][:, keep[span]]
        place = {"run": run.run, "start_volume": start, "concentration": float(np.mean(concentration[span]))}
        rows.append({**place, **_window_measures(data, test)})
        windows.append(network.zscore_rows(data))
    if not rows:
        raise ValueError(f"{run.subject} run {run.run}: every window exceeds the censoring limit")
    table = {key: np.array([r[key] for r in rows]) for key in rows[0]}
    table["windows"] = windows
    return table


def merge_tables(tables: list[dict]) -> dict:
    merged = {k: np.concatenate([t[k] for t in tables]) for k in TABLE_KEYS}
    merged["windows"] = [w for t in tables for w in t["windows"]]
    return merged


def induction_table(subject: Subject, concentration: np.ndarray, test: EdgeTest) -> dict:
    """Awake reference windows (run 1, concentration zero) followed by the induction windows (run 2)."""
    awake_part = window_table(subject.awake, np.zeros(subject.awake.timeseries.shape[1]), test)
    return merge_tables([awake_part, window_table(subject.induction, concentration, test)])


def emergence_table(runs: tuple[MichiganRun, ...], concentrations: list[np.ndarray], test: EdgeTest) -> dict:
    return merge_tables([window_table(run, c, test) for run, c in zip(runs, concentrations, strict=True)])


def awake_and_deep(table: dict) -> tuple[np.ndarray, np.ndarray]:
    c = table["concentration"]
    awake = c <= FMRI.awake_max_concentration
    deep = c >= np.quantile(c, 1.0 - SHAPE.deep_top_share)
    if not awake.any():
        raise ValueError("no window at zero concentration, so there is no awake reference")
    return awake, deep


def null_steepness(table: dict, targets: np.ndarray, null: NullSpec) -> np.ndarray:
    awake, _ = awake_and_deep(table)
    awake_windows = [w for w, a in zip(table["windows"], awake, strict=True) if a]
    fractions = threshold_shape.mixing_fractions(targets, float(np.mean(table["mean_coupling"][awake])))
    steepness = np.empty(null.realisations)
    for r in range(null.realisations):
        s = threshold_shape.null_giant_components(awake_windows, fractions, null.test)
        steepness[r] = threshold_shape.fit_shape(table["concentration"], s).steepness
    return steepness


def linear_null_targets(table: dict) -> np.ndarray:
    awake, deep = awake_and_deep(table)
    m = table["mean_coupling"]
    return threshold_shape.linear_decline(table["concentration"], float(np.mean(m[awake])), float(np.mean(m[deep])))


def _post_lor_share(table: dict, lor_volume: int | None) -> float | None:
    if lor_volume is None:
        return None
    awake, _ = awake_and_deep(table)
    after = (table["run"] == INDUCTION_RUN) & (table["start_volume"] >= lor_volume)
    s = table["giant_component"]
    return float(np.mean(s[after]) / np.mean(s[awake])) if after.any() else None


def threshold_test(table: dict, lor: tuple[int | None, float | None], null: NullSpec) -> dict:
    """H1 for one subject: observed fit, both nulls, local amplitude, coincidence with LOR and the intact check.

    ``lor`` is the LOR volume in run 2 and the effect-site concentration there.
    """
    lor_volume, lor_concentration = lor
    c, m = table["concentration"], table["mean_coupling"]
    awake, deep = awake_and_deep(table)
    observed = threshold_shape.fit_shape(c, table["giant_component"])
    local = threshold_shape.fit_shape(c, table["amplitude"])
    result = {
        "windows": int(c.size),
        "observed": asdict(observed),
        "null_a_linear_decline": threshold_shape.steepness_against_null(observed.steepness, null_steepness(table, linear_null_targets(table), null)),
        "null_b_observed_coupling": threshold_shape.steepness_against_null(observed.steepness, null_steepness(table, m, null)),
        "local_amplitude": asdict(local),
        "local_slope_ratio": float(observed.steepness / local.steepness),
        "coupling_deep_over_awake": float(np.mean(m[deep]) / np.mean(m[awake])),
        "lor_concentration": lor_concentration,
        "c50_minus_lor": None if lor_concentration is None else observed.c50 - lor_concentration,
    }
    if lor_volume is not None:
        result["post_lor_share_of_awake"] = _post_lor_share(table, lor_volume)
    return result


def threshold_sensitivity(subject: Subject, null: NullSpec) -> dict:
    """H1 robustness: the observed fit and null A at each sensitivity threshold of the edge test."""
    out = {}
    for alpha in FMRI.edge_alpha_sensitivity:
        at_alpha = NullSpec(null.realisations, null.test.at_alpha(alpha))
        table = induction_table(subject, subject.induction.effect_site, at_alpha.test)
        observed = threshold_shape.fit_shape(table["concentration"], table["giant_component"])
        out[f"alpha={alpha}"] = {
            "observed": asdict(observed),
            "null_a_linear_decline": threshold_shape.steepness_against_null(observed.steepness, null_steepness(table, linear_null_targets(table), at_alpha)),
        }
    return out


def baseline_zscore(residual: np.ndarray, awake: np.ndarray) -> np.ndarray:
    mean = awake.mean(axis=1, keepdims=True)
    sd = awake.std(axis=1, keepdims=True)
    sd[sd == 0] = 1.0
    return (residual - mean) / sd


def cofluctuation_threshold(z_baseline: np.ndarray, test: EdgeTest) -> float:
    upper = np.triu_indices(z_baseline.shape[0], k=1)
    per_surrogate = min(FMRI.cofluctuation_volumes_per_surrogate, z_baseline.shape[1])
    pooled = []
    for _ in range(test.surrogates.count):
        surrogate = network.zscore_rows(network.phase_randomise(z_baseline, test.rng))
        volumes = test.rng.choice(surrogate.shape[1], size=per_surrogate, replace=False)
        pooled += [np.outer(surrogate[:, t], surrogate[:, t])[upper] for t in volumes]
    return float(np.quantile(np.concatenate(pooled), 1.0 - test.surrogates.alpha))


def order_parameter_series(run: MichiganRun, awake_run: MichiganRun, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """S(t) at every volume from edge co-fluctuations (z_i z_j), standardised on the awake run; censored volumes are NaN."""
    residual, keep = clean_run(run)
    awake_residual, awake_keep = clean_run(awake_run)
    awake = awake_residual[:, awake_keep]
    z = baseline_zscore(residual, awake)
    threshold = cofluctuation_threshold(baseline_zscore(awake, awake), edge_test(rng))
    series = np.full(z.shape[1], np.nan)
    for t in np.flatnonzero(keep):
        series[t] = network.giant_component_fraction(network.adjacency_above(np.outer(z[:, t], z[:, t]), threshold))
    return series, keep


def pre_lor_segment(series: np.ndarray, effect_site: np.ndarray, lor_volume: int) -> np.ndarray:
    start = int(np.argmax(effect_site > FMRI.awake_max_concentration))
    segment = series[start:lor_volume]
    missing = np.isnan(segment)
    if missing.mean() > FMRI.max_censored_share:
        raise ValueError("more than the allowed share of volumes before LOR are censored")
    if missing.any():
        idx = np.arange(segment.size)
        segment = segment.copy()
        segment[missing] = np.interp(idx[missing], idx[~missing], segment[~missing])
    return segment


def critical_slowing(subject: Subject, lor_volume: int, resampling: Resampling) -> dict:
    series, _ = order_parameter_series(subject.induction, subject.awake, resampling.rng)
    segment = pre_lor_segment(series, subject.induction.effect_site, lor_volume)
    return {"points": int(segment.size), **early_warning.critical_slowing_test(segment, resampling.rng, resampling.count)}


def recomputed_effect_site(run: MichiganRun, ke0: float) -> np.ndarray:
    """Effect-site series from the run's plasma series, starting from the provided effect-site value."""
    model = EffectSiteModel(ke0, FMRI.tr_seconds)
    return hysteresis.effect_site_from_plasma(run.plasma, model, float(run.effect_site[0]))


def effect_site_variants(subject: Subject) -> dict[str, tuple[np.ndarray, list[np.ndarray]]]:
    """The dataset's effect-site series and one recomputed series per ke0, for induction and for emergence."""
    variants = {PROVIDED_EFFECT_SITE: (subject.induction.effect_site, [r.effect_site for r in subject.emergence])}
    for ke0 in HYSTERESIS.ke0_per_minute:
        variants[f"ke0={ke0}"] = (recomputed_effect_site(subject.induction, ke0), [recomputed_effect_site(r, ke0) for r in subject.emergence])
    return variants


@dataclass(frozen=True)
class HysteresisInputs:
    subject: Subject
    events: Events
    test: EdgeTest


def _hysteresis_variant(inputs: HysteresisInputs, concentrations: tuple[np.ndarray, list[np.ndarray]]) -> dict:
    induction_c, emergence_c = concentrations
    subject, events = inputs.subject, inputs.events
    ind = induction_table(subject, induction_c, inputs.test)
    em = emergence_table(subject.emergence, emergence_c, inputs.test)
    c50_ind = threshold_shape.fit_shape(ind["concentration"], ind["giant_component"]).c50
    c50_em = threshold_shape.fit_shape(em["concentration"], em["giant_component"]).c50
    lor = hysteresis.concentration_at(induction_c, events.lor_volume)
    ror = hysteresis.concentration_at(emergence_c[0], events.ror_volume)
    return {
        "c50_induction": c50_ind,
        "c50_emergence": c50_em,
        "network_ratio": hysteresis.hysteresis_ratio(c50_ind, c50_em),
        "lor_concentration": lor,
        "ror_concentration": ror,
        "behavioural_ratio": None if lor is None or ror is None or ror <= 0 else lor / ror,
    }


def hysteresis_test(subject: Subject, events: Events, test: EdgeTest) -> dict:
    """H4 for one subject, with effect-site concentration as provided and recomputed for each ke0."""
    inputs = HysteresisInputs(subject, events, test)
    return {name: _hysteresis_variant(inputs, c) for name, c in effect_site_variants(subject).items()}
