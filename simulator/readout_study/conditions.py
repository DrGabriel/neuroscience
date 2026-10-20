"""The experimental conditions of the DPC readout study."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum

import calibration as cal
import disconnection_study
import dpc_simulator as dpc
import phase_dynamics as dynamics
import species_study as species
from readout_study.settings import (
    AGENT_ORGANISMS,
    AWAKE_ONLY_GRID,
    COUPLING_GRID,
    DISCONNECTION_ORGANISMS,
    INERTIA_ORGANISMS,
    LOCKING_THRESHOLD,
    SCANNED_FEEDBACK,
    WINDOW_CYCLES,
)

NULL_ORGANISMS = cal.NULL_MODEL_ORGANISMS


class ConditionName(StrEnum):
    GABAERGIC = species.ConditionName.GABAERGIC
    NMDA_ANTAGONIST = species.ConditionName.NMDA_ANTAGONIST
    GABAERGIC_REWIRED = species.ConditionName.NULL_REWIRED
    NMDA_ANTAGONIST_REWIRED = "NMDA-antagonist-like, rewired connectome (null model)"
    GABAERGIC_WIRED = "GABAergic-like, reference carried by the connections"
    NMDA_ANTAGONIST_WIRED = "NMDA-antagonist-like, reference carried by the connections"
    GABAERGIC_WIRED_REWIRED = "GABAergic-like, reference carried by the connections, rewired connectome (null model)"
    NMDA_ANTAGONIST_WIRED_REWIRED = "NMDA-antagonist-like, reference carried by the connections, rewired connectome (null model)"
    SENSORY_APPLIED = disconnection_study.APPLIED
    SENSORY_PHANTOM = disconnection_study.PHANTOM
    RANDOM_APPLIED = f"NMDA-antagonist-like on as many random connections, sensory stimulus, {WINDOW_CYCLES}-cycle window"
    RANDOM_PHANTOM = f"NMDA-antagonist-like on as many random connections, phantom stimulus of zero strength, {WINDOW_CYCLES}-cycle window"


def agent_designs(integration: dynamics.IntegrationSettings) -> tuple[dynamics.SweepDesign, dynamics.SweepDesign]:
    gabaergic = cal.base_sweep_design(integration)
    return gabaergic, replace(gabaergic, agent=cal.NMDA_ANTAGONIST_AGENT)


def agent_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    gabaergic, nmda = agent_designs(integration)
    gabaergic_wired, nmda_wired = (replace(d, reference_wiring=dynamics.ReferenceWiring.TRANSMITTING_INPUTS) for d in (gabaergic, nmda))
    return (
        species.Condition(ConditionName.GABAERGIC, gabaergic, AGENT_ORGANISMS),
        species.Condition(ConditionName.NMDA_ANTAGONIST, nmda, AGENT_ORGANISMS),
        species.Condition(ConditionName.GABAERGIC_REWIRED, gabaergic, NULL_ORGANISMS, rewired=True),
        species.Condition(ConditionName.NMDA_ANTAGONIST_REWIRED, nmda, NULL_ORGANISMS, rewired=True),
        species.Condition(ConditionName.GABAERGIC_WIRED, gabaergic_wired, AGENT_ORGANISMS),
        species.Condition(ConditionName.NMDA_ANTAGONIST_WIRED, nmda_wired, AGENT_ORGANISMS),
        species.Condition(ConditionName.GABAERGIC_WIRED_REWIRED, gabaergic_wired, NULL_ORGANISMS, rewired=True),
        species.Condition(ConditionName.NMDA_ANTAGONIST_WIRED_REWIRED, nmda_wired, NULL_ORGANISMS, rewired=True),
    )


def with_phantom(design: dynamics.SweepDesign) -> dynamics.SweepDesign:
    """The same design with a stimulus of the same rhythm and zero strength, whose locking measures the floor."""
    return replace(design, stimulus=replace(design.stimulus, strength=0.0))


def disconnection_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    """K1c's two conditions, and the same two with the timing error on as many randomly chosen connections."""
    applied, phantom = disconnection_study.build_conditions(integration)
    random_design = replace(applied.design, jitter_scaling=dynamics.JitterScaling.MATCHED_RANDOM_SENSORY_OUTPUTS)
    return (
        applied,
        phantom,
        species.Condition(ConditionName.RANDOM_APPLIED, random_design, DISCONNECTION_ORGANISMS),
        species.Condition(ConditionName.RANDOM_PHANTOM, with_phantom(random_design), DISCONNECTION_ORGANISMS),
    )


def with_dynamics(integration: dynamics.IntegrationSettings, **changes: float) -> dynamics.SweepDesign:
    """The GABAergic-like reference design with some population dynamics changed."""
    base = cal.base_sweep_design(integration)
    return replace(base, dynamics=replace(base.dynamics, **changes))


def feedback_condition_name(feedback: float) -> str:
    return f"GABAergic-like, reference feedback {feedback:.3f} ({feedback / LOCKING_THRESHOLD:.2f} times the locking threshold)"


def feedback_condition(feedback: float, organisms: tuple[str, ...], integration: dynamics.IntegrationSettings) -> species.Condition:
    return species.Condition(feedback_condition_name(feedback), with_dynamics(integration, reference_feedback=feedback), organisms)


def inertia_scan_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    return tuple(feedback_condition(feedback, INERTIA_ORGANISMS, integration) for feedback in SCANNED_FEEDBACK)


def coupling_condition_name(coupling: float) -> str:
    return f"GABAergic-like, synaptic coupling {coupling:g}, awake only"


def coupling_calibration_conditions(integration: dynamics.IntegrationSettings) -> tuple[species.Condition, ...]:
    def awake_only(coupling: float) -> dynamics.SweepDesign:
        return replace(with_dynamics(integration, synaptic_coupling=coupling), grid=AWAKE_ONLY_GRID)
    return tuple(species.Condition(coupling_condition_name(k), awake_only(k), AGENT_ORGANISMS) for k in COUPLING_GRID)


def metastable_name(agent: dpc.AnaestheticAgent, coupling: float) -> str:
    return f"{agent.name}, weaker coupling {coupling:g}"


def validation_condition_name(feedback: float) -> str:
    return f"{feedback_condition_name(feedback)}, calibrated, held-out seeds"
