"""Glial regulation of timing coherence (postulate P9): slower loops nested around the integration cycle.

Three glial cell types are represented as parameters that change slowly compared with the
millisecond integration cycle, so each is held fixed during a concentration sweep (separation
of timescales):

- Oligodendrocytes (myelin): set conduction timing; damaged myelin adds conduction-time
  variability (Kato et al., 2020), modelled as a higher baseline jitter.
- Microglia: under anaesthesia, low noradrenaline activates microglia, which lower
  noradrenaline further (Liu et al., 2019; Stowell et al., 2019; Ma et al., 2024); removing
  microglia delays induction and hastens emergence (Cao et al., 2023; He et al., 2023).
  Modelled as an arousal drive that weakens further as the coherent core collapses.
- Astrocytes: trigger slow-oscillation states (Poskanzer & Yuste, 2016); modelled as the share
  of sleep down-states that depends on astrocytic signalling.

Standard library only, like dpc_simulator.py, which it extends through its model variants.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

import dpc_simulator as dpc

# Free parameters: no published measurement fixes them, so the study reports their effect over a range.
# Complete loss of myelin doubles the baseline conduction-time jitter.
DEMYELINATION_JITTER_GAIN = 1.0
MYELIN_INTEGRITY_SERIES = (1.0, 0.75, 0.5)
# 0 represents microglial depletion (PLX5622 in He et al., 2023; pharmacological in Cao et al., 2023).
MICROGLIAL_DEPLETED_GAIN = 0.0
MICROGLIAL_GAIN_SERIES = (MICROGLIAL_DEPLETED_GAIN, 0.25, 0.5)
STRONGEST_MICROGLIAL_GAIN = max(MICROGLIAL_GAIN_SERIES)
# Share of sleep down-states lost when astrocytic signalling is silenced.
ASTROCYTIC_DOWN_STATE_SHARE = 0.5

# Measured definition: a slow wave is global when it is detected at more than half of the
# recording locations (Nir et al., 2011), so a global down-state silences half the populations.
GLOBAL_DOWN_STATE_SHARE = 0.5
GLOBAL_SLEEP = dpc.BrainState(dpc.SLEEP_AROUSAL_LEVEL, GLOBAL_DOWN_STATE_SHARE)


def demyelinated(scenario: dpc.Scenario, myelin_integrity: float) -> dpc.Scenario:
    """Scenario with baseline jitter raised in proportion to the share of myelin lost."""
    added_share = DEMYELINATION_JITTER_GAIN * (1 - myelin_integrity)
    jitter_ms = scenario.timing.baseline_jitter_ms * (1 + added_share)
    return replace(scenario, timing=replace(scenario.timing, baseline_jitter_ms=jitter_ms))


def astrocytes_silenced(sleep: dpc.BrainState) -> dpc.BrainState:
    """Sleep state without the down-states that depend on astrocytic signalling."""
    return replace(sleep, down_state_fraction=sleep.down_state_fraction * (1 - ASTROCYTIC_DOWN_STATE_SHARE))


class MicroglialCoherenceModel(dpc.CoherenceModel):
    """Coherence model in which a microglial loop weakens arousal as the coherent core collapses.

    In wakefulness (coherent fraction 1) the loop is silent; in the collapsed state it removes
    the share microglial_gain of the arousal drive, which stabilises the unconscious state.
    With gain 0 it reproduces dpc.CoherenceModel exactly.
    """

    def __init__(
        self, timing: dpc.TimingParameters, agent: dpc.AnaestheticAgent, state: dpc.BrainState, microglial_gain: float
    ) -> None:
        super().__init__(timing, agent, state)
        self._microglial_gain = microglial_gain

    def arousal_at(self, concentration: float, coherent_fraction: float) -> float:
        return self.arousal(concentration) * (1 - self._microglial_gain * (1 - coherent_fraction))


def with_microglia(microglial_gain: float) -> dpc.ModelVariant:
    return dpc.ModelVariant(coherence=partial(MicroglialCoherenceModel, microglial_gain=microglial_gain))

