"""Readers for the open datasets, one module per dataset, written against the layouts verified on 20 October 2026.

Downloaded files are data, never code: nothing here imports, executes or unpickles anything from them. MATLAB files
are read with ``scipy.io.loadmat`` (MATLAB 5 format), text files with NumPy or the csv module, and BrainVision
binaries through a memory map. Every reader checks shapes and raises on anything unexpected.
"""

from .michigan import (
    INSTRUCTION_CONDITIONS,
    PARCELLATION,
    XCPD_PRIMARY,
    MichiganRun,
    RunLocation,
    load_framewise_displacement,
    load_lor_ror,
    load_michigan_run,
    load_parcel_timeseries,
    michigan_run_exists,
)
from .neurotycho import (
    AGENT_CODES,
    Marker,
    available_channels,
    epoch,
    find_marker,
    load_ecog,
    load_electrode_map,
    load_markers,
    parse_session_name,
)
from .prios import BrainVision, load_brainvision, load_stimulation_events

__all__ = [
    "AGENT_CODES",
    "INSTRUCTION_CONDITIONS",
    "PARCELLATION",
    "XCPD_PRIMARY",
    "BrainVision",
    "Marker",
    "MichiganRun",
    "RunLocation",
    "available_channels",
    "epoch",
    "find_marker",
    "load_brainvision",
    "load_ecog",
    "load_electrode_map",
    "load_framewise_displacement",
    "load_lor_ror",
    "load_markers",
    "load_michigan_run",
    "load_parcel_timeseries",
    "load_stimulation_events",
    "michigan_run_exists",
    "parse_session_name",
]
