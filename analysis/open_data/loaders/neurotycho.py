"""Neurotycho "Anesthesia and Sleep" task (macaque ECoG, 128 channels, 1 kHz)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy.io as sio

AGENT_CODES = {"PF": "propofol", "KT": "ketamine", "MD": "medetomidine", "KTMD": "ketamine-medetomidine", "SLP": "sleep"}
SESSION_NAME = re.compile(r"^(\d{8})(KTMD|PF|KT|MD|SLP)_Anesthesia\+and\+Sleep_([A-Za-z0-9]+)_")
SESSION_PREFIX = "Session"
CHANNEL_PREFIX = "ECoG_ch"
CONDITION_FILE = "Condition.mat"
COORDINATES = 2
WHOLE_RECORDING = slice(None)


@dataclass(frozen=True)
class Marker:
    session: str
    label: str
    index: int
    seconds: float


def _loadmat(path: Path) -> dict:
    return sio.loadmat(path, squeeze_me=True, mat_dtype=False, struct_as_record=True)


def parse_session_name(directory: Path) -> dict[str, str]:
    match = SESSION_NAME.match(directory.name)
    if not match:
        raise ValueError(f"not a Neurotycho Anesthesia and Sleep folder: {directory.name}")
    date, code, monkey = match.groups()
    return {"date": date, "agent": AGENT_CODES[code], "monkey": monkey}


def _session_markers(session: Path) -> list[Marker]:
    content = _loadmat(session / CONDITION_FILE)
    labels, indices, times = (np.atleast_1d(content[k]) for k in ("ConditionLabel", "ConditionIndex", "ConditionTime"))
    if not len(labels) == len(indices) == len(times):
        raise ValueError(f"{session}: condition arrays differ in length")
    return [Marker(session.name, str(label), int(i), float(s)) for label, i, s in zip(labels, indices, times, strict=True)]


def load_markers(experiment: Path) -> list[Marker]:
    sessions = sorted(experiment.glob(f"{SESSION_PREFIX}*"), key=lambda p: int(p.name.removeprefix(SESSION_PREFIX)))
    return [marker for session in sessions for marker in _session_markers(session)]


def find_marker(markers: list[Marker], label: str) -> Marker:
    found = [m for m in markers if m.label == label]
    if len(found) != 1:
        raise ValueError(f"expected one '{label}' marker, found {len(found)}")
    return found[0]


def epoch(markers: list[Marker], labels: tuple[str, str]) -> tuple[str, int, int]:
    """Session and sample span between a start and an end marker."""
    start, end = find_marker(markers, labels[0]), find_marker(markers, labels[1])
    if start.session != end.session or end.index <= start.index:
        raise ValueError(f"'{labels[0]}' to '{labels[1]}' is not a forward span within one session")
    return start.session, start.index, end.index


def load_ecog(session_dir: Path, channels: list[int], span: slice = WHOLE_RECORDING) -> np.ndarray:
    """Channels x samples in microvolts; ``span`` is applied per channel so a whole session is never held as floats."""
    rows = []
    for ch in channels:
        content = _loadmat(session_dir / f"{CHANNEL_PREFIX}{ch}.mat")
        rows.append(np.asarray(content[f"ECoGData_ch{ch}"][span], float))
    lengths = {r.size for r in rows}
    if len(lengths) != 1:
        raise ValueError(f"{session_dir}: channels differ in length {sorted(lengths)}")
    return np.stack(rows)


def load_electrode_map(path: Path) -> np.ndarray:
    content = _loadmat(path)
    xy = np.column_stack([content["X"], content["Y"]]).astype(float)
    if xy.shape[1] != COORDINATES or not np.all(np.isfinite(xy)):
        raise ValueError(f"{path}: electrode coordinates missing or not finite")
    return xy


def available_channels(session_dir: Path) -> list[int]:
    return sorted(int(p.stem.removeprefix(CHANNEL_PREFIX)) for p in session_dir.glob(f"{CHANNEL_PREFIX}*.mat"))
