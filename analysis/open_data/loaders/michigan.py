"""Michigan Human Anesthesia fMRI Dataset-1 (OpenNeuro ds006623, v1.0.0)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PARCELLATION = "4S156Parcels"
XCPD_PRIMARY = "xcp_d_without_GSR_bandpass_output"
INSTRUCTION_CONDITIONS = ("action", "navi", "squeeze", "tennis")
MISSING_TEXT = ("", "N/A", "n/a")
SUBJECT_PREFIX = "sub-"
TIMING_TABLE = "LOR_ROR_Timing.csv"
DISPLACEMENT_COLUMN = "framewise_displacement"
COMMENT = "#"
TAB = "\t"
SUBJECT_COLUMN, LOR_COLUMN, ROR_COLUMN = 0, 1, 2
LOR_KEY, ROR_KEY = "lor_volume", "ror_volume"
TABLE_DIMENSIONS = 2


@dataclass(frozen=True)
class RunLocation:
    """Where one imagery run of one subject lives, and which denoising pipeline to read."""

    root: Path
    subject: str
    run: int
    pipeline: str = XCPD_PRIMARY

    @property
    def derivatives(self) -> Path:
        return self.root / "derivatives"

    @property
    def func(self) -> Path:
        return self.derivatives / self.pipeline / self.subject / "func"

    @property
    def stem(self) -> str:
        return f"{self.subject}_task-imagery_run-{self.run}"

    @property
    def timeseries(self) -> Path:
        return self.func / f"{self.stem}_space-MNI152NLin2009cAsym_seg-{PARCELLATION}_stat-mean_timeseries.tsv"

    @property
    def motion(self) -> Path:
        return self.func / f"{self.stem}_motion.tsv"

    def infusion(self, kind: str) -> Path:
        return self.derivatives / "Propofol_Infusion" / self.subject / f"{self.subject}_task{self.run}_{kind}.1D"

    def instruction(self, condition: str) -> Path:
        return self.derivatives / "Squeeze_Force" / "Instruction_Timing" / f"Ideal_task{self.run}_{condition}.xmat.1D"


@dataclass(frozen=True)
class MichiganRun:
    subject: str
    run: int
    timeseries: np.ndarray  # parcels x volumes
    parcels: list[str]
    effect_site: np.ndarray
    plasma: np.ndarray
    framewise_displacement: np.ndarray
    instructions: np.ndarray  # volumes x conditions


def _one_column(path: Path) -> np.ndarray:
    values = np.loadtxt(path, comments=COMMENT, ndmin=1)
    if values.ndim != 1:
        raise ValueError(f"{path} should hold one column, found shape {values.shape}")
    return values


def load_parcel_timeseries(path: Path) -> tuple[np.ndarray, list[str]]:
    with path.open() as handle:
        header = handle.readline().rstrip("\n").split(TAB)
    raw = np.genfromtxt(path, delimiter=TAB, skip_header=1, missing_values="n/a", filling_values=np.nan)
    if raw.ndim != TABLE_DIMENSIONS or raw.shape[1] != len(header):
        raise ValueError(f"{path}: expected {len(header)} columns, found shape {raw.shape}")
    return raw.T, header


def load_framewise_displacement(path: Path) -> np.ndarray:
    """First volume has no displacement (n/a in the file); it is taken as zero."""
    with path.open() as handle:
        rows = list(csv.DictReader(handle, delimiter=TAB))
    return np.array([0.0 if r[DISPLACEMENT_COLUMN] in MISSING_TEXT else float(r[DISPLACEMENT_COLUMN]) for r in rows])


def _int_or_none(text: str) -> int | None:
    text = text.strip()
    return None if text in MISSING_TEXT else int(text)


def load_lor_ror(root: Path) -> dict[str, dict[str, int | None]]:
    """Loss and return of responsiveness, in volumes of the induction (task2) and emergence (task3) runs."""
    out = {}
    with (root / "derivatives" / TIMING_TABLE).open() as handle:
        for row in csv.reader(handle):
            if row and row[SUBJECT_COLUMN].startswith(SUBJECT_PREFIX):
                out[row[SUBJECT_COLUMN]] = {LOR_KEY: _int_or_none(row[LOR_COLUMN]), ROR_KEY: _int_or_none(row[ROR_COLUMN])}
    return out


def michigan_run_exists(location: RunLocation) -> bool:
    """Some subjects lack a run (sub-29 has no run 4 in v1.0.0); emergence then rests on run 3 alone."""
    return location.timeseries.exists()


def _check_lengths(location: RunLocation, n_volumes: int, series: dict[str, np.ndarray]) -> None:
    for name, values in series.items():
        if len(values) != n_volumes:
            raise ValueError(f"{location.subject} run {location.run}: {name} has {len(values)} samples, BOLD has {n_volumes}")


def load_michigan_run(location: RunLocation) -> MichiganRun:
    timeseries, parcels = load_parcel_timeseries(location.timeseries)
    effect_site, plasma = _one_column(location.infusion("ESC")), _one_column(location.infusion("PLAS"))
    displacement = load_framewise_displacement(location.motion)
    instructions = np.column_stack([_one_column(location.instruction(c)) for c in INSTRUCTION_CONDITIONS])
    lengths = {"effect-site": effect_site, "plasma": plasma, "displacement": displacement, "instructions": instructions}
    _check_lengths(location, timeseries.shape[1], lengths)
    if np.isnan(timeseries).any():
        raise ValueError(f"{location.subject} run {location.run}: BOLD contains missing values (the run is unusable)")
    return MichiganRun(location.subject, location.run, timeseries, parcels, effect_site, plasma, displacement, instructions)
