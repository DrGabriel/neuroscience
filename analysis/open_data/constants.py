"""Units, numerical floors and the labels (datasets, hypotheses, states) shared by every module."""

from __future__ import annotations

from enum import StrEnum

MS_PER_SECOND = 1000.0
MICROSECONDS_PER_SECOND = 1e6
SECONDS_PER_MINUTE = 60.0
BYTES_PER_MEGABYTE = 1e6
BYTES_PER_GIGABYTE = 1e9

NUMERICAL_FLOOR = 1e-30  # keeps a division by a vanishing magnitude finite
RESULTANT_FLOOR = 1e-12  # smallest mean resultant length taken to a logarithm

PROVIDED_EFFECT_SITE = "provided"  # the dataset's own effect-site series, as opposed to one recomputed for a ke0


class Dataset(StrEnum):
    MICHIGAN = "michigan"
    NEUROTYCHO = "neurotycho"
    PRIOS = "prios"


class Hypothesis(StrEnum):
    H1 = "H1"
    H2a = "H2a"
    H2b = "H2b"
    H3 = "H3"
    H4 = "H4"
    H5a = "H5a"


class State(StrEnum):
    AWAKE = "awake"
    ANAESTHETISED = "anaesthetised"
