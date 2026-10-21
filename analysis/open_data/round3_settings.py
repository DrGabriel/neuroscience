"""Every number the three round-3 reanalyses depend on (Appendix E.15), fixed before any of them runs.

The committed settings (settings.py) are left unchanged; their hashes are recorded in the earlier results. Values
taken from them (seed, smallest effects, bootstrap size) are reused, not restated.
"""

from __future__ import annotations

from dataclasses import dataclass

from .settings import LAG


@dataclass(frozen=True)
class SnrControl:
    """H5a with a signal-to-noise control: restriction bound and the synthetic responses of the simulation."""

    restriction_ratio: float = 1.25
    sampling_hz: float = 2048.0
    latency_ms: float = 22.0
    width_ms: float = 5.0
    connections: int = 200
    snr_doublings: tuple[float, ...] = (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
    trial_counts: tuple[int, ...] = (6, 10, 100)
    jitter_ms: tuple[float, ...] = (0.0, 2.0, 4.0)
    colours: tuple[str, ...] = ("white", "pink")
    null_trials: int = 10
    null_awake_snr: tuple[float, ...] = (4.0, 8.0, 16.0)
    null_snr_ratios: tuple[float, ...] = (0.5, 0.25)
    sensitivity_trials: int = 10
    sensitivity_jitter_ms: float = 2.0
    sensitivity_floor_share: float = 0.5

    @property
    def nominal_snr(self) -> tuple[float, ...]:
        return tuple(float(2.0**d) for d in self.snr_doublings)


@dataclass(frozen=True)
class MonkeyBootstrap:
    """H2b and H3 resampled over monkeys, then sessions within monkey."""

    resamples: int = LAG.bootstrap_resamples


@dataclass(frozen=True)
class Launcher:
    """Parallel launcher of the reseeded Michigan analysis (D8)."""

    processes: int = 10
    log_tail_lines: int = 20


SNR = SnrControl()
MONKEY = MonkeyBootstrap()
LAUNCHER = Launcher()
