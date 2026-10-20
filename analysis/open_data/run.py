"""Command line for the pre-specified open-data tests. Run from the repository root with an isolated interpreter:

    .venv/bin/python -I analysis/open_data/run.py <command> [options]

Commands: michigan, neurotycho, prios (per subject or session, each writes one JSON file) and group (verdicts).
``--check-only`` loads and validates a dataset without computing any statistic, so that file layouts can be
checked before the confirmatory run without seeing a result.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "analysis.open_data"

import numpy as np

from . import group, loaders, pipeline_michigan, pipeline_neurotycho, pipeline_prios, settings, verdicts
from .constants import Dataset, Hypothesis
from .montage import Experiment, build_montage
from .outputs import EXCLUDED, Output, attempt, included, is_excluded, to_json, write
from .pipeline_michigan import Events, NullSpec, Subject, edge_test
from .pipeline_prios import PriosSession
from .specs import Resampling

BANDS = {band.name: band for band in (settings.GAMMA, *settings.SECONDARY_BANDS)}
ALL_CHANNELS, AUTO_MAP = "all", "auto"
NAME_SEPARATOR, EXPERIMENTER_FIELD = "_", 3
CHANNEL_SEPARATOR = ","
SLEEP = loaders.AGENT_CODES["SLP"]
H1_SENSITIVITY, H3_BLOCKS = "H1_threshold_sensitivity", "H3_blocks"
NO_LOR = {EXCLUDED: "no loss-of-responsiveness volume in LOR_ROR_Timing.csv"}
AWAKE_TASK, PROPOFOL_TASK = "SPESclin", "SPESprop"
HEADER_SUFFIX = "_ieeg.vhdr"


@dataclass(frozen=True)
class MichiganOptions:
    null_realisations: int
    surrogates: int
    rng: np.random.Generator


# --------------------------------------------------------------------------- Michigan fMRI


def load_subject(root: Path, name: str) -> Subject:
    def location(run: int) -> loaders.RunLocation:
        return loaders.RunLocation(root, name, run)

    emergence = tuple(loaders.load_michigan_run(location(r)) for r in pipeline_michigan.EMERGENCE_RUNS if loaders.michigan_run_exists(location(r)))
    if not emergence or emergence[0].run != pipeline_michigan.EMERGENCE_RUNS[0]:
        raise FileNotFoundError(f"{name}: emergence run {pipeline_michigan.EMERGENCE_RUNS[0]} is missing")
    awake, induction = (loaders.load_michigan_run(location(r)) for r in (pipeline_michigan.AWAKE_RUN, pipeline_michigan.INDUCTION_RUN))
    return Subject(awake, induction, emergence)


def subject_summary(subject: Subject, events: Events) -> dict:
    runs = (subject.awake, subject.induction, *subject.emergence)
    limit = settings.FMRI.framewise_displacement_limit_mm
    return {
        "subject": subject.induction.subject,
        "volumes": {r.run: r.timeseries.shape[1] for r in runs},
        "awake_run_max_concentration": float(subject.awake.effect_site.max()),
        "parcels": len(subject.induction.parcels),
        "lor_ror_volumes": asdict(events),
        "censored_share": {r.run: float(np.mean(r.framewise_displacement > limit)) for r in runs},
    }


def analyse_subject(subject: Subject, events: Events, options: MichiganOptions) -> dict:
    test = edge_test(options.rng)
    null = NullSpec(options.null_realisations, test)
    lor_c = None if events.lor_volume is None else float(subject.induction.effect_site[events.lor_volume])
    table = pipeline_michigan.induction_table(subject, subject.induction.effect_site, test)
    results = {Hypothesis.H1: attempt(pipeline_michigan.threshold_test, table, (events.lor_volume, lor_c), null)}
    results[H1_SENSITIVITY] = attempt(pipeline_michigan.threshold_sensitivity, subject, null)
    resampling = Resampling(options.surrogates, options.rng)
    no_lor = events.lor_volume is None
    results[Hypothesis.H2a] = NO_LOR if no_lor else attempt(pipeline_michigan.critical_slowing, subject, events.lor_volume, resampling)
    results[Hypothesis.H4] = attempt(pipeline_michigan.hysteresis_test, subject, events, test)
    return {**results, "induction_windows": {k: v for k, v in table.items() if k != "windows"}}


def michigan(arguments: argparse.Namespace) -> None:
    root = Path(arguments.root)
    options = MichiganOptions(arguments.null_realisations, arguments.surrogates, np.random.default_rng(settings.SEED))
    timing = loaders.load_lor_ror(root)
    for name in arguments.subject:
        started = time.time()
        subject, events = load_subject(root, name), Events(**timing[name])
        summary = subject_summary(subject, events)
        if arguments.check_only:
            print(json.dumps(summary, default=to_json))
            continue
        output = Output(Path(arguments.out) / f"{Dataset.MICHIGAN}_{name}.json", arguments, started)
        write(output, {**summary, **analyse_subject(subject, events, options)})


# --------------------------------------------------------------------------- Neurotycho ECoG


def channel_list(text: str, experiment: Path) -> list[int]:
    if text != ALL_CHANNELS:
        return [int(c) for c in text.split(CHANNEL_SEPARATOR)]
    sessions = sorted(experiment.glob(f"{loaders.neurotycho.SESSION_PREFIX}*"))
    return sorted(set.intersection(*(set(loaders.available_channels(s)) for s in sessions)))


def electrode_map(text: str, experiment: Path, monkey: str) -> Path:
    """An explicit path, or with 'auto' the single map of this monkey by the same experimenter as the recording.

    Su has a second map from a later implant by another experimenter (2013), which must not be used for 2011 data.
    """
    if text != AUTO_MAP:
        return Path(text)
    experimenter = experiment.name.split(NAME_SEPARATOR)[EXPERIMENTER_FIELD]
    found = sorted(experiment.parent.glob(f"*_{monkey}_{experimenter}_*2Dimg/*.mat"))
    if len(found) != 1:
        raise FileNotFoundError(f"expected one electrode map for {monkey} beside {experiment}, found {[str(f) for f in found]}")
    return found[0]


def check_experiment(experiment: Experiment, summary: dict) -> dict:
    """Loader check only: montage size, recording length and induction duration; no statistic is computed."""
    montage = build_montage(experiment.channels, experiment.xy_all)
    induction = pipeline_neurotycho.induction_segment(loaders.load_markers(experiment.path))
    raw = loaders.load_ecog(experiment.path / induction.session, experiment.channels[:1])
    seconds = (induction.span.end - induction.span.start) / settings.ECOG.sampling_hz
    sizes = {"bipolar_derivations": len(montage.pairs), "long_range_pairs": len(montage.long_range), "samples": raw.shape[1]}
    return {**summary, **sizes, "induction_seconds": seconds}


def analyse_experiment(experiment: Experiment, meta: dict, arguments: argparse.Namespace) -> dict:
    band = BANDS[arguments.band]
    session_id = f"{meta['monkey']}-{meta['date']}"
    labels = {"agent": meta["agent"], "monkey": meta["monkey"], "session_id": session_id}
    payload = {"band": band.name, H3_BLOCKS: [{**b, **labels} for b in pipeline_neurotycho.session_blocks(experiment, band)]}
    if band is settings.GAMMA:
        resampling = Resampling(arguments.surrogates, np.random.default_rng(settings.SEED))
        payload[Hypothesis.H2b] = attempt(pipeline_neurotycho.critical_slowing, experiment, resampling)
    return payload


def neurotycho(arguments: argparse.Namespace) -> None:
    started, path = time.time(), Path(arguments.experiment)
    meta = loaders.parse_session_name(path)
    xy = loaders.load_electrode_map(electrode_map(arguments.map, path, meta["monkey"]))
    experiment = Experiment(path, channel_list(arguments.channels, path), xy)
    markers = [m.__dict__ for m in loaders.load_markers(path)]
    summary = {**meta, "experiment": path.name, "channels": experiment.channels, "markers": markers}
    if arguments.check_only:
        print(json.dumps(check_experiment(experiment, summary), default=to_json))
        return
    prefix = Dataset.NEUROTYCHO if arguments.band == settings.GAMMA.name else f"secondary-{arguments.band}-{Dataset.NEUROTYCHO}"
    write(Output(Path(arguments.out) / f"{prefix}_{path.name}.json", arguments, started), {**summary, **analyse_experiment(experiment, meta, arguments)})


# --------------------------------------------------------------------------- PRIOS iEEG


def single(folder: Path, pattern: str) -> Path:
    found = sorted(folder.glob(pattern))
    if len(found) != 1:
        raise FileNotFoundError(f"expected one {pattern} in {folder}, found {[f.name for f in found]}")
    return found[0]


def prios_session(session_dir: Path) -> PriosSession:
    ieeg = session_dir / "ieeg"
    stems = {task: single(ieeg, f"*task-{task}_*{HEADER_SUFFIX}").name.removesuffix(HEADER_SUFFIX) for task in (AWAKE_TASK, PROPOFOL_TASK)}
    return PriosSession(ieeg, stems[AWAKE_TASK], stems[PROPOFOL_TASK], single(ieeg, "*_electrodes.tsv"))


def prios(arguments: argparse.Namespace) -> None:
    started, session_dir = time.time(), Path(arguments.session_dir)
    session = prios_session(session_dir)
    result = attempt(pipeline_prios.subject_changes, session, np.random.default_rng(settings.SEED))
    runs = {AWAKE_TASK: session.awake_stem, PROPOFOL_TASK: session.propofol_stem}
    write(Output(Path(arguments.out) / f"{Dataset.PRIOS}_{session_dir.parent.name}.json", arguments, started), {"runs": runs, Hypothesis.H5a: result})


# --------------------------------------------------------------------------- group verdicts


def load_all(directory: Path, prefix: str) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(directory.glob(f"{prefix}_*.json"))]


def h1_inputs(michigan_results: list[dict]) -> list[dict]:
    usable = [r for r in michigan_results if not is_excluded(r[Hypothesis.H1]) and not is_excluded(r[H1_SENSITIVITY])]
    return [{**r[Hypothesis.H1], "sensitivity": r[H1_SENSITIVITY]} for r in usable]


def primary_summaries(michigan_results: list[dict], neurotycho_results: list[dict]) -> dict:
    return {
        Hypothesis.H1: group.h1_threshold(h1_inputs(michigan_results)),
        Hypothesis.H2a: group.h2_critical_slowing(included([r[Hypothesis.H2a] for r in michigan_results])),
        Hypothesis.H2b: group.h2_critical_slowing(included([r[Hypothesis.H2b] for r in neurotycho_results])),
        Hypothesis.H3: group.h3_lag_variability([b for r in neurotycho_results for b in r[H3_BLOCKS]]),
        Hypothesis.H4: group.h4_hysteresis(included([r[Hypothesis.H4] for r in michigan_results])),
    }


def exclusions(results: list[dict]) -> dict[str, str]:
    names = (Hypothesis.H1, H1_SENSITIVITY, Hypothesis.H2a, Hypothesis.H2b, Hypothesis.H4)
    return {
        f"{name}:{r.get('subject') or r.get('experiment')}": r[name][EXCLUDED]
        for r in results
        for name in names
        if isinstance(r.get(name), dict) and EXCLUDED in r[name]
    }


def group_command(arguments: argparse.Namespace) -> None:
    started, directory = time.time(), Path(arguments.inputs)
    michigan_results = load_all(directory, Dataset.MICHIGAN)
    neurotycho_results = [r for r in load_all(directory, Dataset.NEUROTYCHO) if r["agent"] != SLEEP]
    payload = {
        "primary": verdicts.family_verdicts(primary_summaries(michigan_results, neurotycho_results)),
        "secondary_H1": group.h1_secondary(included([r[Hypothesis.H1] for r in michigan_results])),
        "exclusions": exclusions(michigan_results + neurotycho_results),
    }
    prios_results = load_all(directory, Dataset.PRIOS)
    if prios_results:
        payload["secondary_H5a"] = group.h5a_latency(included([r[Hypothesis.H5a] for r in prios_results]))
    write(Output(Path(arguments.out), arguments, started), payload)


# --------------------------------------------------------------------------- arguments


def _michigan_parser(commands) -> None:
    m = commands.add_parser(Dataset.MICHIGAN, help="H1, H2a, H4 for each subject of ds006623")
    m.add_argument("--root", required=True)
    m.add_argument("--subject", action="append", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--null-realisations", type=int, default=settings.SHAPE.null_realisations)
    m.add_argument("--surrogates", type=int, default=settings.WARNING.surrogates)
    m.add_argument("--check-only", action="store_true")
    m.set_defaults(handler=michigan)


def _neurotycho_parser(commands) -> None:
    n = commands.add_parser(Dataset.NEUROTYCHO, help="H2b and the H3 blocks for one Neurotycho experiment folder")
    n.add_argument("--experiment", required=True)
    n.add_argument("--map", default=AUTO_MAP, help="electrode map .mat, or 'auto' to find this monkey's map beside the experiment")
    n.add_argument("--band", choices=sorted(BANDS), default=settings.GAMMA.name)
    n.add_argument("--channels", default=ALL_CHANNELS)
    n.add_argument("--out", required=True)
    n.add_argument("--surrogates", type=int, default=settings.WARNING.surrogates)
    n.add_argument("--check-only", action="store_true")
    n.set_defaults(handler=neurotycho)


def _prios_and_group_parsers(commands) -> None:
    p = commands.add_parser(Dataset.PRIOS, help="H5a for one PRIOS patient")
    p.add_argument("--session-dir", required=True, help="for example data_external/ds004370/sub-PRIOS01/ses-1")
    p.add_argument("--out", required=True)
    p.set_defaults(handler=prios)
    g = commands.add_parser("group", help="family-wise verdicts from a folder of per-subject results")
    g.add_argument("--inputs", required=True)
    g.add_argument("--out", required=True)
    g.set_defaults(handler=group_command)


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = top.add_subparsers(required=True)
    for add in (_michigan_parser, _neurotycho_parser, _prios_and_group_parsers):
        add(commands)
    return top


def main(argv: list[str] | None = None) -> None:
    arguments = parser().parse_args(argv)
    arguments.handler(arguments)


if __name__ == "__main__":
    main()
