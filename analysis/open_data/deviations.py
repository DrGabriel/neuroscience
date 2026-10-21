"""Deviations from the committed plan (Appendix E.13), used only by exploratory runs.

The committed code (commit adc63f6) is left unchanged and its confirmatory runs use it as committed. Two features of
the downloaded data were not anticipated by the plan, and the committed code refuses them:

D1, Michigan fMRI: in 19 of 26 subjects one to eight of the 156 regions of the parcellated BOLD are empty (missing
    in every volume) in at least one run, and the committed loader refuses any run with a missing value. Deviation:
    for each subject, the regions empty in any of its runs are removed from all of its runs, so that every run of a
    subject keeps the same regions. A region missing in only some volumes would still be refused (none was found).
D2, Neurotycho ECoG: 3 of 23 sessions carry more than one 'AnestheticInjection' marker (top-up injections), and the
    committed code requires exactly one. Deviation: the first injection marks the start of induction.
D3, Michigan fMRI: a sigmoid fit that does not converge raises an error that the committed runner does not catch, so
    one non-converging null realisation ends the whole run. Deviation: a null realisation whose fit does not converge
    is left out of the null distribution and counted (leaving out curves without a step makes the null steeper, so
    the test is harder to pass); a test whose observed fit does not converge is recorded as not evaluable for that
    subject, with the reason, as the committed runner already records a stated exclusion.

Usage, from the repository root (results go to a separate exploratory folder):
    .venv/bin/python -I -m analysis.open_data.deviations michigan --root ... --subject ... --out ...
    .venv/bin/python -I -m analysis.open_data.deviations neurotycho --experiment ... --out ...
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np

from . import group, loaders, outputs, pipeline_michigan, pipeline_neurotycho, run, stats, threshold_shape, verdicts
from .constants import Hypothesis
from .loaders import michigan as michigan_loader
from .loaders.neurotycho import Marker
from .pipeline_michigan import Subject

INJECTION = pipeline_neurotycho.INJECTION
# The committed functions, kept so that every case the deviations do not cover behaves exactly as committed.
_committed_find_marker = pipeline_neurotycho.find_marker
_committed_load_subject = run.load_subject
_committed_attempt = run.attempt
_committed_single = run.single
_committed_h1_secondary = group.h1_secondary
AWAKE_RUN_PATTERN = f"task-{run.AWAKE_TASK}_"


def load_run_keeping_empty_regions(location: loaders.RunLocation) -> loaders.MichiganRun:
    """The committed loader without its refusal of missing values (D1); every other check is kept."""
    timeseries, parcels = michigan_loader.load_parcel_timeseries(location.timeseries)
    effect_site = michigan_loader._one_column(location.infusion("ESC"))
    plasma = michigan_loader._one_column(location.infusion("PLAS"))
    displacement = michigan_loader.load_framewise_displacement(location.motion)
    instructions = np.column_stack([michigan_loader._one_column(location.instruction(c)) for c in michigan_loader.INSTRUCTION_CONDITIONS])
    lengths = {"effect-site": effect_site, "plasma": plasma, "displacement": displacement, "instructions": instructions}
    michigan_loader._check_lengths(location, timeseries.shape[1], lengths)
    return loaders.MichiganRun(location.subject, location.run, timeseries, parcels, effect_site, plasma, displacement, instructions)


def empty_regions(runs: tuple[loaders.MichiganRun, ...]) -> np.ndarray:
    """Regions missing in every volume of at least one run; a partly missing region is an error, as committed."""
    partly_missing = [r.run for r in runs if (np.isnan(r.timeseries).any(axis=1) & ~np.isnan(r.timeseries).all(axis=1)).any()]
    if partly_missing:
        raise ValueError(f"{runs[0].subject} runs {partly_missing}: a region is missing in only some volumes")
    return np.any([np.isnan(r.timeseries).all(axis=1) for r in runs], axis=0)


def without_regions(run_: loaders.MichiganRun, dropped: np.ndarray) -> loaders.MichiganRun:
    kept = ~dropped
    return dataclasses.replace(run_, timeseries=run_.timeseries[kept], parcels=[p for p, k in zip(run_.parcels, kept) if k])


def drop_empty_regions(subject: Subject) -> Subject:
    """D1: the same regions removed from every run of one subject."""
    dropped = empty_regions((subject.awake, subject.induction, *subject.emergence))
    return Subject(
        without_regions(subject.awake, dropped),
        without_regions(subject.induction, dropped),
        tuple(without_regions(r, dropped) for r in subject.emergence),
    )


def first_injection(markers: list[Marker], label: str) -> Marker:
    """D2: the first 'AnestheticInjection' marker; every other label still needs exactly one marker, as committed."""
    if label != INJECTION:
        return _committed_find_marker(markers, label)
    found = [m for m in markers if m.label == label]
    if not found:
        raise ValueError(f"no '{label}' marker")
    return found[0]


def steepness_or_none(concentration: np.ndarray, giant_component: np.ndarray) -> float | None:
    try:
        return threshold_shape.fit_shape(concentration, giant_component).steepness
    except RuntimeError:
        return None


def null_steepness_without_failed_fits(table: dict, targets: np.ndarray, null: pipeline_michigan.NullSpec) -> np.ndarray:
    """D3: the committed null distribution, leaving out realisations whose sigmoid fit does not converge."""
    awake, _ = pipeline_michigan.awake_and_deep(table)
    awake_windows = [w for w, a in zip(table["windows"], awake, strict=True) if a]
    fractions = threshold_shape.mixing_fractions(targets, float(np.mean(table["mean_coupling"][awake])))
    fitted = (steepness_or_none(table["concentration"], threshold_shape.null_giant_components(awake_windows, fractions, null.test)) for _ in range(null.realisations))
    steepness = np.array([s for s in fitted if s is not None])
    if steepness.size == 0:
        raise ValueError("no null realisation could be fitted with a sigmoid")
    print(f"D3: {null.realisations - steepness.size} of {null.realisations} null realisations left out (fit did not converge)", file=sys.stderr)
    return steepness


def attempt_recording_failed_fits(test, *args) -> dict:
    """D3: as the committed attempt(), and a fit that does not converge is recorded as not evaluable."""
    try:
        return _committed_attempt(test, *args)
    except RuntimeError as error:
        print(f"not evaluable in {test.__name__}: {error}", file=sys.stderr)
        return {outputs.EXCLUDED: f"not evaluable: {error}"}


def earliest_awake_run(folder: Path, pattern: str) -> Path:
    """D4: the earlier of several awake runs; every other file still needs to be unique, as committed."""
    if AWAKE_RUN_PATTERN not in pattern:
        return _committed_single(folder, pattern)
    found = sorted(folder.glob(pattern))
    if not found:
        raise FileNotFoundError(f"no {pattern} in {folder}")
    return found[0]


NO_SUBJECT = "not evaluable: no subject or session could be analysed"
WORST_P = 1.0


def summary_or_no_subject(summarise, inputs: list) -> dict:
    """D5: the committed summary, or a placeholder that enters the Holm family with p = 1."""
    if inputs:
        result = summarise(inputs)
        return result if isinstance(result, dict) else dataclasses.asdict(result)
    return {"no_subject": True, "n": 0}


def primary_summaries_allowing_empty(michigan_results: list[dict], neurotycho_results: list[dict]) -> dict:
    neurotycho_blocks = [b for r in neurotycho_results for b in r[run.H3_BLOCKS]]
    return {
        Hypothesis.H1: summary_or_no_subject(group.h1_threshold, run.h1_inputs(michigan_results)),
        Hypothesis.H2a: summary_or_no_subject(group.h2_critical_slowing, outputs.included([r[Hypothesis.H2a] for r in michigan_results])),
        Hypothesis.H2b: summary_or_no_subject(group.h2_critical_slowing, outputs.included([r[Hypothesis.H2b] for r in neurotycho_results])),
        Hypothesis.H3: summary_or_no_subject(group.h3_lag_variability, neurotycho_blocks),
        Hypothesis.H4: summary_or_no_subject(group.h4_hysteresis, outputs.included([r[Hypothesis.H4] for r in michigan_results])),
    }


def p_value_of(name: str, result: dict) -> float:
    if result.get("no_subject"):
        return WORST_P
    return result[verdicts.P_VALUE_FIELD.get(Hypothesis(name), verdicts.DEFAULT_P_VALUE_FIELD)]


def family_verdicts_with_empty_tests(primary: dict[str, dict]) -> dict[str, dict]:
    """D5: Holm across all five primary tests, empty ones at p = 1; the committed verdict rule for every other test."""
    adjusted = stats.holm({name: p_value_of(name, r) for name, r in primary.items()})
    out = {}
    for name, result in primary.items():
        rule = verdicts.VERDICT_RULES.get(Hypothesis(name), verdicts.general_verdict)
        verdict = NO_SUBJECT if result.get("no_subject") else rule(result, adjusted[name])
        out[name] = {**result, "adjusted_p": adjusted[name], "verdict": verdict}
    return out


def h1_secondary_allowing_empty(subjects: list[dict]) -> dict:
    return _committed_h1_secondary(subjects) if subjects else {"no_subject": True}


def load_subject_with_d1(root: Path, name: str) -> Subject:
    return drop_empty_regions(_committed_load_subject(root, name))



def apply_deviations() -> None:
    """Replaces exactly the committed behaviours named above (D1 to D5), for this process only."""
    loaders.load_michigan_run = load_run_keeping_empty_regions
    run.load_subject = load_subject_with_d1
    pipeline_neurotycho.find_marker = first_injection
    pipeline_michigan.null_steepness = null_steepness_without_failed_fits
    run.attempt = attempt_recording_failed_fits
    run.single = earliest_awake_run
    run.primary_summaries = primary_summaries_allowing_empty
    verdicts.family_verdicts = family_verdicts_with_empty_tests
    group.h1_secondary = h1_secondary_allowing_empty


if __name__ == "__main__":
    apply_deviations()
    run.main()
