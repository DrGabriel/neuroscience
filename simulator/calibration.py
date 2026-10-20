"""Parameters of the cross-species phase-oscillator study, with their basis and source.

Each value is one of:
    measured    a published measurement used as it stands (source given);
    assumed     a published estimate that is not a direct measurement of the quantity in the
                model (source given); the sensitivity analysis varies it;
    calibrated  fitted to one published measurement (target given), then held fixed;
    free        not measured at this level of description; the sensitivity analysis
                reports how the results change across a range.

The percolation model (dpc_simulator.py), the congestion test (excitatory_inhibitory.py,
congestion_study.py) and the threshold formulas (percolation_thresholds.py) keep their own
constants beside the code that uses them, each labelled with the same categories.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import dpc_simulator as dpc
import phase_dynamics as dynamics
import plant_tissue

BASE_SEED = dpc.REFERENCE_SEED
CONNECTOME_SEED = dpc.REFERENCE_SEED


@dataclass(frozen=True)
class OrganismSpec:
    display_name: str
    has_tract_lengths: bool
    full_study_seeds: int
    worker_processes: int
    # Numerical resolution for the full study; None keeps the study-wide setting.
    concentration_step: float | None = None
    relaxation_steps: int | None = None
    # Whether the dataset gives transmitter identity, so connections can be signed.
    has_connection_signs: bool = False

    def grid_step(self, study_step: float) -> float:
        """Concentration step used for this organism: its own coarser step if it has one, else the study's."""
        return study_step if self.concentration_step is None else self.concentration_step


# Numerical: the fly connectome has 2.7 million connections, about 80 ms per integration step on
# the machine used, so it is run on a coarser concentration grid with a shorter settling period.
# The measurement window is kept at full length because entrainment needs whole stimulus cycles.
DROSOPHILA_CONCENTRATION_STEP = 0.1
DROSOPHILA_RELAXATION_STEPS = 200

# The rewired-network null model is run for the two connectomes whose runs take under a minute;
# one Drosophila run takes about 20 minutes.
NULL_MODEL_ORGANISMS = ("celegans", "human")

ORGANISMS: dict[str, OrganismSpec] = {
    "celegans": OrganismSpec("C. elegans", has_tract_lengths=False, full_study_seeds=20, worker_processes=10),
    "drosophila": OrganismSpec(
        "Drosophila",
        has_tract_lengths=False,
        full_study_seeds=6,
        worker_processes=6,
        concentration_step=DROSOPHILA_CONCENTRATION_STEP,
        relaxation_steps=DROSOPHILA_RELAXATION_STEPS,
        has_connection_signs=True,
    ),
    "human": OrganismSpec("Human", has_tract_lengths=True, full_study_seeds=20, worker_processes=10),
}


@dataclass(frozen=True)
class ParameterRecord:
    name: str
    value: object
    basis: str
    source: str


# ---------------------------------------------------------------------------
# Anaesthetic agents (shared with the percolation model)
# ---------------------------------------------------------------------------

GABAERGIC_AGENT = dpc.GABAERGIC_LIKE_AGENT
NMDA_ANTAGONIST_AGENT = dpc.NMDA_ANTAGONIST_LIKE_AGENT

# ---------------------------------------------------------------------------
# Population dynamics
# ---------------------------------------------------------------------------

# Assumed: gamma band 30-90 Hz (Fries, 2015); 40 Hz lies within it, and coherent 40 Hz activity
# is found in waking and dreaming but much reduced in deep sleep (Llinás & Ribary, 1993).
OSCILLATION_FREQUENCY_HZ = 40.0
# Free: calibration against the reference inertia ratio was attempted with calibrate_phase_feedback.py
# on the human connectome and failed. For λ from 0 to 0.75 the ratio of each run stayed within 0.91-1.05
# (means 0.99-1.00), within run-to-run noise, except one run at 0.75 that never recovered. The mid-range
# value is used, and inertia is tested in the percolation model instead.
PHASE_REFERENCE_FEEDBACK = 0.45
INERTIA_TARGET_RATIO = dpc.REFERENCE_INERTIA_RATIO
# Free: in units of the natural-frequency spread, coupling well above the synchronisation
# threshold so that the awake network is coherent; noise small relative to coupling.
SYNAPTIC_COUPLING = 4.0
NATURAL_FREQUENCY_SPREAD = 0.5
NOISE_INTENSITY = 0.05
# Free: how long a connection's timing error persists, in model time units; about one coupling
# time (1 / K) and longer, so that an error acts during an exchange rather than averaging out.
JITTER_CORRELATION_TIME = 1.0

# Free, used only by the learned-timing test of P4b (Appendix C.10): how fast a connection learns its expected
# arrival offset, in model time units. Ten jitter correlation times, so that the learning averages timing
# variability rather than tracking it, and about a sixth of the time held at each concentration, so that it
# settles within one concentration step.
ARRIVAL_LEARNING_TIME = 10 * JITTER_CORRELATION_TIME

POPULATION_DYNAMICS = dynamics.PopulationDynamics(
    synaptic_coupling=SYNAPTIC_COUPLING,
    natural_frequency_spread=NATURAL_FREQUENCY_SPREAD,
    noise_intensity=NOISE_INTENSITY,
    reference_feedback=PHASE_REFERENCE_FEEDBACK,
    oscillation_frequency_hz=OSCILLATION_FREQUENCY_HZ,
    baseline_jitter_ms=dpc.REFERENCE_BASELINE_JITTER_MS,
    arousal_level=dpc.REFERENCE_AROUSAL_LEVEL,
    jitter_correlation_time=JITTER_CORRELATION_TIME,
)

# Measured: frontal alpha at propofol-induced loss of consciousness lies in the 8-12 Hz band
# (Purdon et al., 2013); its centre is the rate the reference falls back to under P8.
ALPHA_FALLBACK_FREQUENCY_HZ = 10.0

# Measured: median axonal conduction velocity of human cortico-cortical connections, 3.9 m/s, with a
# median delay of about 10 ms (Lemaréchal et al., 2022, in patients with epilepsy over 15 years old).
CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S = 3.9

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

# Free: quorum as a fraction of awake coherence, shared with the percolation model.
QUORUM_FRACTION = dpc.REFERENCE_QUORUM_FRACTION
CONCENTRATION_GRID = dpc.ConcentrationGrid(maximum=3.0, step=0.05)
# Numerical: Euler-Maruyama step well below the fastest coupling time scale (1 / K); the
# relaxation and measurement windows span many cycles of the slowest population.
# Entrainment to the stimulus is measured over a whole number of its cycles, so that a population that does not
# follow the stimulus averages to zero instead of leaving a residue that depends on the window (the first
# measurement window, 600 steps, covered 1.43 cycles). Two cycles are used; more would multiply the cost of
# every Drosophila run.
STIMULUS_ANGULAR_FREQUENCY = 0.3
MEASURED_STIMULUS_CYCLES = 2
FULL_TIME_STEP = 0.05
FULL_MEASUREMENT_STEPS = round(MEASURED_STIMULUS_CYCLES * 2 * math.pi / STIMULUS_ANGULAR_FREQUENCY / FULL_TIME_STEP)
FULL_INTEGRATION = dynamics.IntegrationSettings(time_step=FULL_TIME_STEP, relaxation_steps=400, measurement_steps=FULL_MEASUREMENT_STEPS)
QUICK_INTEGRATION = dynamics.IntegrationSettings(time_step=0.05, relaxation_steps=100, measurement_steps=100)

def base_sweep_design(integration: dynamics.IntegrationSettings, seed: int = BASE_SEED) -> dynamics.SweepDesign:
    """The reference sweep: GABAergic-like agent, calibrated dynamics, reference grid and quorum."""
    return dynamics.SweepDesign(
        agent=GABAERGIC_AGENT,
        dynamics=POPULATION_DYNAMICS,
        integration=integration,
        grid=CONCENTRATION_GRID,
        quorum_fraction=QUORUM_FRACTION,
        seed=seed,
    )


# Free: strong enough to entrain the stimulated populations, weak enough that the awake
# network still propagates the stimulus (at twice this strength it does not).
SENSORY_STIMULUS = dynamics.SensoryStimulus(strength=1.0, angular_frequency=STIMULUS_ANGULAR_FREQUENCY)

# ---------------------------------------------------------------------------
# Pillar thresholds (definitions, stated before the results are seen)
# ---------------------------------------------------------------------------

# A surge is a peak at least one order of magnitude above the awake value ...
MINIMUM_SUSCEPTIBILITY_SURGE = 10.0
# ... located within three grid steps of the loss of quorum.
SURGE_WINDOW = 3 * CONCENTRATION_GRID.step
# Broadcast has collapsed when it falls to half its awake value or less.
BROADCAST_COLLAPSE_FRACTION = 0.5

# Post hoc (set after the first smoke run, reported as secondary analyses only):
# the stimulated area "keeps processing" if it retains at least this share of its awake entrainment.
POST_HOC_SENSORY_RETENTION = 0.8

# ---------------------------------------------------------------------------
# Plant tissue
# ---------------------------------------------------------------------------

PLANT_JUNCTION_CONDUCTANCES = (0.5, 1.0, 2.0, 4.0)
PLANT_SEEDS = 10
# Propagation has failed when the action potential reaches less than half the sheet.
PROPAGATION_FAILURE_FRACTION = 0.5
PLANT_TISSUE = plant_tissue.TissueDesign(
    geometry=plant_tissue.TissueGeometry(rows=60, columns=60),
    junction_conductance=PLANT_JUNCTION_CONDUCTANCES[0],
    time_step=0.05,
    duration_steps=4000,
    agent=GABAERGIC_AGENT,
    grid=dpc.ConcentrationGrid(maximum=3.0, step=0.05),
    seed=BASE_SEED,
)


def parameter_table() -> tuple[ParameterRecord, ...]:
    return (
        ParameterRecord("Baseline timing jitter (ms)", dpc.REFERENCE_BASELINE_JITTER_MS, "assumed", "within-neuron value used between areas: precision of rate modulation in macaque MT in vivo, Buracas et al. (1998); swept 1-10"),
        ParameterRecord("Integration window W (ms)", dpc.REFERENCE_INTEGRATION_WINDOW_MS, "assumed", "within-cell windows used between areas: 1-10 ms in rodent barrel cortex, Gabernet et al. (2005); under 2 ms in hippocampus, Pouille and Scanziani (2001); swept 1-10"),
        ParameterRecord("Oscillation frequency (Hz)", OSCILLATION_FREQUENCY_HZ, "assumed", "within the gamma band, Fries (2015); Llinás and Ribary (1993)"),
        ParameterRecord("Jitter correlation time τ", JITTER_CORRELATION_TIME, "free", "sensitivity analysis"),
        ParameterRecord("Arrival learning time τ_L (P4b test only)", ARRIVAL_LEARNING_TIME, "free", "ten jitter correlation times; not varied"),
        ParameterRecord("Percolation feedback λ (ms)", dpc.REFERENCE_FEEDBACK_JITTER_MS, "calibrated", f"ratio {dpc.REFERENCE_INERTIA_RATIO}, Friedman et al. (2010), isoflurane"),
        ParameterRecord("Oscillator feedback λ", PHASE_REFERENCE_FEEDBACK, "free", f"calibration to ratio {dpc.REFERENCE_INERTIA_RATIO} failed: inertia within noise"),
        ParameterRecord("Conduction velocity (m/s)", CORTICOCORTICAL_CONDUCTION_VELOCITY_M_PER_S, "measured", "Lemaréchal et al. (2022)"),
        ParameterRecord("Arousal level", dpc.REFERENCE_AROUSAL_LEVEL, "free", "inertia ratios 1.07-1.63 reproduced at every level tested"),
        ParameterRecord("Fallback reference rate, P8 (Hz)", ALPHA_FALLBACK_FREQUENCY_HZ, "assumed", "centre of the measured frontal alpha band, 8-12 Hz, Purdon et al. (2013)"),
        ParameterRecord("Synaptic coupling K", SYNAPTIC_COUPLING, "free", "sensitivity analysis"),
        ParameterRecord("Natural-frequency spread", NATURAL_FREQUENCY_SPREAD, "free", "sensitivity analysis"),
        ParameterRecord("Noise intensity D", NOISE_INTENSITY, "free", "sensitivity analysis"),
        ParameterRecord("Quorum fraction", QUORUM_FRACTION, "free", "sensitivity analysis"),
        ParameterRecord("GABAergic-like agent", asdict(GABAERGIC_AGENT), "free", "maximal failure swept 0.6-0.95; failure at loss of quorum compared with 62% inhibition of glutamate release by 0.7 mM isoflurane (about 2 MAC) in cultured rat hippocampal neurons, Baumgart et al. (2015)"),
        ParameterRecord("NMDA-antagonist-like agent", asdict(NMDA_ANTAGONIST_AGENT), "free", "maximal effects not measurable at this scale"),
        ParameterRecord("Sensory stimulus", asdict(SENSORY_STIMULUS), "free", "see comment in calibration.py"),
        ParameterRecord("FitzHugh-Nagumo a, b, ε", (plant_tissue.FITZHUGH_A, plant_tissue.FITZHUGH_B, plant_tissue.FITZHUGH_EPSILON), "standard model values", "FitzHugh (1961)"),
        ParameterRecord("Plant junction conductance", PLANT_JUNCTION_CONDUCTANCES, "free", "reported across the range"),
    )


def as_record() -> list[dict[str, object]]:
    return [asdict(record) for record in parameter_table()]
