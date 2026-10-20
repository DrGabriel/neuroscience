"""Test H4: hysteresis between induction and emergence, and its sensitivity to the pharmacokinetic model.

A lag between plasma and effect-site concentration that the model gets wrong produces apparent hysteresis on its
own. The effect-site series is therefore recomputed from the plasma series over a range of equilibration rate
constants (ke0), and hysteresis is claimed only if it survives every one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import SECONDS_PER_MINUTE


@dataclass(frozen=True)
class EffectSiteModel:
    """First-order effect compartment, dCe/dt = ke0 (Cp - Ce), sampled every ``dt_seconds``."""

    ke0_per_minute: float
    dt_seconds: float

    @property
    def retained_per_sample(self) -> float:
        return float(np.exp(-self.ke0_per_minute * self.dt_seconds / SECONDS_PER_MINUTE))


def effect_site_from_plasma(plasma: np.ndarray, model: EffectSiteModel, initial: float = 0.0) -> np.ndarray:
    """Effect-site series, integrated exactly for plasma held constant over each sample."""
    plasma = np.asarray(plasma, float)
    retain = model.retained_per_sample
    effect = np.empty_like(plasma)
    current = initial
    for i, cp in enumerate(plasma):
        effect[i] = current
        current = cp + (current - cp) * retain
    return effect


def hysteresis_ratio(c50_induction: float, c50_emergence: float) -> float:
    if c50_emergence <= 0:
        raise ValueError("emergence threshold must be positive")
    return c50_induction / c50_emergence


def concentration_at(series: np.ndarray, index: int | None) -> float | None:
    if index is None:
        return None
    if not 0 <= index < len(series):
        raise IndexError(f"event at sample {index} lies outside a series of {len(series)} samples")
    return float(series[index])
