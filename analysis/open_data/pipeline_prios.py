"""Test H5a (prediction 8, partial): latency variability of cortico-cortical evoked potentials, awake against propofol.

The same stimulated pairs are compared in the awake clinical session (SPESclin) and under propofol in the operating
room (SPESprop). Both polarities of a pair are pooled, trial counts are equalised by random subsampling, and only
response electrodes at least the minimum distance from both stimulated electrodes count as another area.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import evoked_latency
from .constants import MS_PER_SECOND, State
from .evoked_latency import LatencyWindow, ResponseTest
from .loaders import BrainVision, load_brainvision, load_stimulation_events
from .settings import EVOKED

PROPOFOL = "propofol"
SITE_SEPARATOR = "-"
MISSING_TEXT = ("n/a", "")
ECOG_TYPE, GOOD_STATUS = "ECOG", "good"
TrialsByChannel = dict[str, dict[str, np.ndarray]]


@dataclass(frozen=True)
class PriosSession:
    """One patient's awake and propofol recordings (BIDS stems) and electrode table."""

    ieeg_dir: Path
    awake_stem: str
    propofol_stem: str
    electrodes: Path


@dataclass(frozen=True)
class Comparison:
    sampling_hz: float
    positions: dict[str, np.ndarray]
    rng: np.random.Generator


def samples(ms: float, fs: float) -> int:
    return int(ms * fs / MS_PER_SECOND)


def unordered_site(site: str) -> str:
    return SITE_SEPARATOR.join(sorted(site.split(SITE_SEPARATOR)))


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def electrode_positions(path: Path) -> dict[str, np.ndarray]:
    return {r["name"]: np.array([float(r["x"]), float(r["y"]), float(r["z"])]) for r in read_tsv(path) if r["x"] not in MISSING_TEXT}


def good_ecog_channels(path: Path) -> set[str]:
    return {r["name"] for r in read_tsv(path) if r.get("type", "").upper() == ECOG_TYPE and r.get("status", GOOD_STATUS) == GOOD_STATUS}


def trials_by_site(recording: BrainVision, events: list[dict], channel: int) -> dict[str, np.ndarray]:
    fs = recording.sampling_hz
    before = samples(-EVOKED.baseline_ms[0], fs)
    after = samples(EVOKED.response_end_ms + EVOKED.max_shift_ms, fs)
    grouped: dict[str, list[np.ndarray]] = {}
    for event in events:
        s = event["sample"]
        if 0 <= s - before and s + after <= recording.data.shape[0]:
            grouped.setdefault(unordered_site(event["site"]), []).append(np.asarray(recording.data[s - before : s + after, channel], float))
    return {site: np.stack(rows) for site, rows in grouped.items()}


def baseline_corrected(trials: np.ndarray, fs: float) -> tuple[np.ndarray, int]:
    onset = samples(-EVOKED.baseline_ms[0], fs)
    end = onset + samples(EVOKED.baseline_ms[1], fs)
    return trials - np.median(trials[:, :end], axis=1, keepdims=True), onset


def far_enough(response: str, site: str, positions: dict[str, np.ndarray]) -> bool:
    members = site.split(SITE_SEPARATOR)
    if response in members or response not in positions or any(m not in positions for m in members):
        return False
    return all(np.linalg.norm(positions[response] - positions[m]) >= EVOKED.min_distance_mm for m in members)


def measure(trials: np.ndarray, fs: float) -> dict[str, float] | None:
    corrected, onset = baseline_corrected(trials, fs)
    start, end = onset + samples(EVOKED.artefact_end_ms, fs), onset + samples(EVOKED.response_end_ms, fs)
    template = corrected.mean(axis=0)
    baseline = template[: onset + samples(EVOKED.baseline_ms[1], fs)]
    if not evoked_latency.is_response(template, baseline, ResponseTest(start, end, EVOKED.response_z)):
        return None
    latency = evoked_latency.connection_latency(corrected, LatencyWindow(fs, start, end, samples(EVOKED.max_shift_ms, fs)))
    latency["mean_latency_ms"] -= MS_PER_SECOND * onset / fs
    return latency


def compare_connection(awake: np.ndarray, propofol: np.ndarray, comparison: Comparison) -> dict | None:
    """Both states on equal trial counts; None when there are too few trials or no response in either state."""
    count = min(awake.shape[0], propofol.shape[0])
    if count < EVOKED.min_trials:
        return None
    a = measure(evoked_latency.equalise_trials(awake, count, comparison.rng), comparison.sampling_hz)
    p = measure(evoked_latency.equalise_trials(propofol, count, comparison.rng), comparison.sampling_hz)
    if a is None or p is None or min(a["latency_sd_ms"], p["latency_sd_ms"]) <= 0:
        return None
    return {"trials": count, State.AWAKE.value: a, PROPOFOL: p, "relative_change": evoked_latency.relative_change(a, p)}


def candidate_connections(by_state: dict[str, TrialsByChannel], positions: dict[str, np.ndarray]) -> list[tuple[str, str]]:
    awake, propofol = by_state[State.AWAKE], by_state[PROPOFOL]
    pairs = [(r, s) for r in sorted(set(awake) & set(propofol)) for s in sorted(set(awake[r]) & set(propofol[r]))]
    return [(r, s) for r, s in pairs if far_enough(r, s, positions)]


def connection_changes(by_state: dict[str, TrialsByChannel], comparison: Comparison) -> list[dict]:
    rows = []
    for response, site in candidate_connections(by_state, comparison.positions):
        row = compare_connection(by_state[State.AWAKE][response][site], by_state[PROPOFOL][response][site], comparison)
        if row is not None:
            rows.append({"response": response, "site": site, **row})
    return rows


def _state_trials(session: PriosSession, stem: str) -> tuple[BrainVision, TrialsByChannel]:
    recording = load_brainvision(session.ieeg_dir / f"{stem}_ieeg.vhdr")
    events = load_stimulation_events(session.ieeg_dir / f"{stem}_events.tsv")
    good = good_ecog_channels(session.ieeg_dir / f"{stem}_channels.tsv")
    return recording, {name: trials_by_site(recording, events, i) for i, name in enumerate(recording.channels) if name in good}


def subject_changes(session: PriosSession, rng: np.random.Generator) -> dict:
    awake_recording, awake = _state_trials(session, session.awake_stem)
    propofol_recording, propofol = _state_trials(session, session.propofol_stem)
    if awake_recording.sampling_hz != propofol_recording.sampling_hz:
        raise ValueError("awake and propofol sessions differ in sampling rate")
    comparison = Comparison(awake_recording.sampling_hz, electrode_positions(session.electrodes), rng)
    rows = connection_changes({State.AWAKE: awake, PROPOFOL: propofol}, comparison)
    values = np.array([r["relative_change"] for r in rows])
    return {"connections": rows, "median_relative_change": float(np.median(values)) if values.size else None}
