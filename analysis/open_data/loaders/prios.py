"""PRIOS (OpenNeuro ds004370, v1.0.2): BrainVision iEEG with single-pulse stimulation events."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..constants import MICROSECONDS_PER_SECOND

BRAINVISION_FORMATS = {"IEEE_FLOAT_32": np.float32, "INT_16": np.int16}
MULTIPLEXED = "MULTIPLEXED"
STIMULATION = "electrical_stimulation"
NO_NOTE = ("n/a", "")
HEADER_FIELD = re.compile(r"^(\w+)=(.*)$", flags=re.M)
CHANNEL_LINE = re.compile(r"^Ch\d+=([^,]*)")


@dataclass(frozen=True)
class BrainVision:
    data: np.ndarray  # samples x channels, memory-mapped
    channels: list[str]
    sampling_hz: float


def _channel_names(text: str) -> list[str]:
    return [m.group(1) for m in (CHANNEL_LINE.match(line) for line in text.splitlines()) if m]


def load_brainvision(header_path: Path) -> BrainVision:
    text = header_path.read_text(errors="replace")
    fields = dict(HEADER_FIELD.findall(text))
    if fields.get("DataOrientation", "").strip() != MULTIPLEXED:
        raise ValueError(f"{header_path}: only multiplexed BrainVision data are supported")
    n_channels = int(fields["NumberOfChannels"])
    channels = _channel_names(text)
    if len(channels) != n_channels:
        raise ValueError(f"{header_path}: {len(channels)} channel names for {n_channels} channels")
    data_path = header_path.with_name(fields["DataFile"].strip())
    flat = np.memmap(data_path, dtype=BRAINVISION_FORMATS[fields["BinaryFormat"].strip()], mode="r")
    if flat.size % n_channels:
        raise ValueError(f"{data_path}: size is not a whole number of samples")
    return BrainVision(flat.reshape(-1, n_channels), channels, MICROSECONDS_PER_SECOND / float(fields["SamplingInterval"]))


def load_stimulation_events(events_path: Path) -> list[dict[str, object]]:
    """Single pulses with their stimulated pair, excluding pulses whose notes report a deviation from the request."""
    with events_path.open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return [
        {"sample": int(r["sample_start"]), "site": r["electrical_stimulation_site"], "current": r["electrical_stimulation_current"]}
        for r in rows
        if r["trial_type"] == STIMULATION and r.get("notes", NO_NOTE[0]) in NO_NOTE
    ]
