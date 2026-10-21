"""Deviation D8 (round 3, exploratory; Appendix E.15): the Michigan analysis with each subject's generator seeded alone.

Under D6 every process seeded its generator once with the committed seed and analysed its subjects in turn, so a
subject's random draws depended on its place in its process. Here each subject's generator is seeded with the
committed seed plus the number in the subject's name (sub-02 is seeded with SEED + 2), so that any subject's result
can be reproduced alone, in any order and in any process. Everything else is the exploratory analysis as run, with
deviations D1 to D5 of deviations.py; deviations.py and exploratory_group.py are used unchanged.

Usage, from the repository root:
    .venv/bin/python -E -s -m analysis.open_data.reseeded michigan --root <ds006623> --subject sub-02 --out <folder>
    .venv/bin/python -E -s -m analysis.open_data.reseeded listing --previous <old list> --folder <folder> --out <new list>
    .venv/bin/python -E -s -m analysis.open_data.exploratory_group group --inputs <new list> --out <verdicts.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import deviations, loaders, outputs, run, settings
from .constants import Dataset
from .outputs import Output
from .pipeline_michigan import Events

SUBJECT_NAME = re.compile(r"sub-(\d+)")
SEED_FIELD = "D8_seed"
LISTING_COMMAND = "listing"
RESULT_SUFFIX = ".json"
LINE_END = "\n"


@dataclass(frozen=True)
class SubjectJob:
    root: Path
    name: str
    timing: dict


def subject_seed(name: str) -> int:
    """The committed seed plus the subject's number: sub-02 -> SEED + 2."""
    match = SUBJECT_NAME.fullmatch(name)
    if match is None:
        raise ValueError(f"subject name {name!r} is not of the form sub-NN")
    return settings.SEED + int(match.group(1))


def result_name(subject: str) -> str:
    return f"{Dataset.MICHIGAN}_{subject}{RESULT_SUFFIX}"


def analyse_one(job: SubjectJob, arguments: argparse.Namespace) -> None:
    """One subject, with its own generator; the committed loader (with D1), summary and analysis."""
    started, seed = time.time(), subject_seed(job.name)
    subject, events = run.load_subject(job.root, job.name), Events(**job.timing)
    summary = run.subject_summary(subject, events)
    if arguments.check_only:
        print(json.dumps({**summary, SEED_FIELD: seed}, default=outputs.to_json))
        return
    options = run.MichiganOptions(arguments.null_realisations, arguments.surrogates, np.random.default_rng(seed))
    output = Output(Path(arguments.out) / result_name(job.name), arguments, started)
    outputs.write(output, {**summary, SEED_FIELD: seed, **run.analyse_subject(subject, events, options)})


def michigan_reseeded(arguments: argparse.Namespace) -> None:
    """D8: replaces the committed runner's single generator by one generator per subject."""
    for name in arguments.subject:
        subject_seed(name)
    root = Path(arguments.root)
    timing = loaders.load_lor_ror(root)
    for name in arguments.subject:
        analyse_one(SubjectJob(root, name, timing[name]), arguments)


def _replacement(line: str, folder: Path) -> str:
    name = Path(line).name
    return outputs.portable(folder / name) if name.startswith(f"{Dataset.MICHIGAN}_") else line


def _check_seed(path: Path) -> None:
    subject = path.name.removeprefix(f"{Dataset.MICHIGAN}_").removesuffix(RESULT_SUFFIX)
    recorded = json.loads(path.read_text()).get(SEED_FIELD)
    if recorded != subject_seed(subject):
        raise ValueError(f"{path}: recorded seed {recorded} is not the D8 seed of {subject}")


def reseeded_listing(previous: Path, folder: Path) -> list[str]:
    """The earlier group inputs with every Michigan file replaced by its reseeded one; refused unless all exist."""
    folder = folder.absolute()
    lines = [_replacement(line, folder) for line in previous.read_text().split()]
    _check_complete(lines, folder)
    for line in (line for line in lines if Path(line).name.startswith(f"{Dataset.MICHIGAN}_")):
        _check_seed(outputs.REPO / line)
    return lines


def _check_complete(lines: list[str], folder: Path) -> None:
    listed = {Path(line).name for line in lines}
    unlisted = sorted(p.name for p in folder.glob(f"{Dataset.MICHIGAN}_*{RESULT_SUFFIX}") if p.name not in listed)
    missing = [line for line in lines if not (outputs.REPO / line).exists()]
    if unlisted or missing:
        raise FileNotFoundError(f"reseeded results missing: {missing}; present but not in the earlier list: {unlisted}")


def listing_command(argv: list[str]) -> None:
    top = argparse.ArgumentParser(prog=f"reseeded {LISTING_COMMAND}", description=reseeded_listing.__doc__)
    top.add_argument("--previous", required=True, help="the earlier list, exploratory/group_inputs.txt")
    top.add_argument("--folder", required=True, help="the folder of the reseeded Michigan results")
    top.add_argument("--out", required=True)
    arguments = top.parse_args(argv)
    lines = reseeded_listing(Path(arguments.previous), Path(arguments.folder))
    Path(arguments.out).write_text(LINE_END.join(lines) + LINE_END)
    print(f"wrote {arguments.out} ({len(lines)} files)")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == [LISTING_COMMAND]:
        listing_command(argv[1:])
        return
    deviations.apply_deviations()
    run.michigan = michigan_reseeded
    run.main(argv)


if __name__ == "__main__":
    main()
