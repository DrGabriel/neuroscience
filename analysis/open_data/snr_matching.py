"""H5a with a signal-to-noise control (round 3, exploratory; Appendix E.15): per-connection SNR and its equalisation.

Lower evoked amplitude makes single-trial latencies noisier, which by itself raises their spread. For each H5a
connection, on the same equalised trials as H5a, the single-trial signal-to-noise ratio (SNR) of each state is the
N1 amplitude of the mean response over the noise of single trials, the median over trials of the standard deviation
of the de-meaned pre-pulse signal over as many samples as the latency estimator reads. The state with the higher SNR
is then degraded to the lower: each of its trials receives, over the span the estimator reads, the de-meaned pre-pulse
signal of the next trial of the same state (cyclically), scaled so that its noise rises by the factor that equalises
the two SNRs. The added noise therefore has the spectrum of that state's own background activity. Mean latency and
latency spread are then measured again exactly as in H5a, by the committed estimator.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import evoked_latency, pipeline_prios
from .constants import MS_PER_SECOND, NUMERICAL_FLOOR, State
from .evoked_latency import LatencyWindow
from .pipeline_prios import PROPOFOL, Comparison, samples
from .settings import EVOKED

AWAKE = State.AWAKE.value
STATES = (AWAKE, PROPOFOL)
NEXT_TRIAL = -1
SD_FIELD, LATENCY_FIELD = "latency_sd_ms", "mean_latency_ms"


@dataclass(frozen=True)
class TrialLayout:
    """Where the pulse, the response window and the end of the baseline fall in a trial, as the committed measure() has them."""

    onset: int
    window: LatencyWindow
    baseline_end: int

    @property
    def span(self) -> slice:
        return slice(self.window.start - self.window.max_shift, self.window.end + self.window.max_shift)


def trial_layout(sampling_hz: float, onset: int) -> TrialLayout:
    start, end = onset + samples(EVOKED.artefact_end_ms, sampling_hz), onset + samples(EVOKED.response_end_ms, sampling_hz)
    window = LatencyWindow(sampling_hz, start, end, samples(EVOKED.max_shift_ms, sampling_hz))
    return TrialLayout(onset, window, onset + samples(EVOKED.baseline_ms[1], sampling_hz))


def noise_segments(corrected: np.ndarray, layout: TrialLayout) -> np.ndarray:
    """The first span-length samples of each trial's baseline, de-meaned: the noise the estimator sees, and the donors."""
    length = layout.span.stop - layout.span.start
    if length > layout.baseline_end:
        raise ValueError("the baseline is shorter than the span the latency estimator reads")
    segments = corrected[:, :length]
    return segments - segments.mean(axis=1, keepdims=True)


def state_snr(corrected: np.ndarray, layout: TrialLayout) -> dict[str, float]:
    template = corrected.mean(axis=0)
    peak = evoked_latency.peak_latency(template, layout.window.start, layout.window.end)
    amplitude = float(abs(template[peak]))
    noise = float(np.median(noise_segments(corrected, layout).std(axis=1)))
    return {"amplitude": amplitude, "noise_sd": noise, "snr": amplitude / max(noise, NUMERICAL_FLOOR)}


def noise_scale(higher_snr: float, lower_snr: float) -> float:
    """Scale of the donor noise that lowers an SNR from ``higher_snr`` to ``lower_snr``: sqrt(ratio^2 - 1)."""
    return float(np.sqrt(max((higher_snr / lower_snr) ** 2 - 1.0, 0.0)))


def degraded(corrected: np.ndarray, layout: TrialLayout, scale: float) -> np.ndarray:
    donors = np.roll(noise_segments(corrected, layout), NEXT_TRIAL, axis=0)
    out = corrected.copy()
    out[:, layout.span] += scale * donors
    return out


def latency_of(corrected: np.ndarray, layout: TrialLayout) -> dict[str, float]:
    """The committed estimator on baseline-corrected trials, latency counted from the pulse, as in measure()."""
    latency = evoked_latency.connection_latency(corrected, layout.window)
    latency[LATENCY_FIELD] -= MS_PER_SECOND * layout.onset / layout.window.sampling_hz
    return latency


def matched_relative_change(matched: dict[str, dict[str, float]]) -> float | None:
    if min(m[SD_FIELD] for m in matched.values()) <= 0:
        return None
    return evoked_latency.relative_change(matched[AWAKE], matched[PROPOFOL])


def snr_matched(trials: dict[str, np.ndarray], sampling_hz: float) -> dict:
    """SNR of both states, the higher degraded to the lower, and the H5a measures recomputed on the matched trials."""
    baseline = {s: pipeline_prios.baseline_corrected(trials[s], sampling_hz) for s in STATES}
    corrected = {s: c for s, (c, _) in baseline.items()}
    layout = trial_layout(sampling_hz, baseline[AWAKE][1])
    snr = {s: state_snr(corrected[s], layout) for s in STATES}
    higher = max(STATES, key=lambda s: snr[s]["snr"])
    lower = PROPOFOL if higher == AWAKE else AWAKE
    scale = noise_scale(snr[higher]["snr"], snr[lower]["snr"])
    matched = {s: latency_of(degraded(corrected[s], layout, scale) if s == higher else corrected[s], layout) for s in STATES}
    return {
        "snr": snr,
        "log_snr_ratio": float(np.log(snr[PROPOFOL]["snr"] / snr[AWAKE]["snr"])),
        "degraded_state": higher,
        "noise_scale": scale,
        "matched": matched,
        "matched_relative_change": matched_relative_change(matched),
    }


def matched_connection(awake: np.ndarray, propofol: np.ndarray, comparison: Comparison) -> dict | None:
    """The committed compare_connection() step for step (same draws, same exclusions), with the SNR control added."""
    count = min(awake.shape[0], propofol.shape[0])
    if count < EVOKED.min_trials:
        return None
    trials = {AWAKE: evoked_latency.equalise_trials(awake, count, comparison.rng), PROPOFOL: evoked_latency.equalise_trials(propofol, count, comparison.rng)}
    a, p = (pipeline_prios.measure(trials[s], comparison.sampling_hz) for s in STATES)
    if a is None or p is None or min(a[SD_FIELD], p[SD_FIELD]) <= 0:
        return None
    row = {"trials": count, AWAKE: a, PROPOFOL: p, "relative_change": evoked_latency.relative_change(a, p)}
    return {**row, **snr_matched(trials, comparison.sampling_hz)}
