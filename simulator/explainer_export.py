"""Export the data behind the interactive explainer (../explainer/).

Writes ../explainer/data/explainer-data.js with:
- the percolation model's parameters, agents, sleep, glial and plant settings, read from the
  simulator's own modules so the browser model cannot drift from the Python one;
- the C. elegans connectome (OpenWorm c302, MIT licence) and an open human connectome (CC BY 4.0),
  whose notices are reproduced in the file;
- results read from the latest reports: thresholds for every organism, the validation statistics,
  the calibration targets, the predictions of the paper and every pre-specified test outcome.

Nothing in the explainer is typed in by hand: re-run this after any study and the page follows.

Usage: ../.venv/bin/python explainer_export.py
"""

from __future__ import annotations

import functools
import json
import re
import sys
from enum import IntEnum

import numpy as np
import scipy.io

import calibration as cal
import connectomes
import dpc_simulator as dpc
import glial_regulation as glia
import percolation_thresholds
import plant_tissue
import provenance
import reporting
from figures import mean_and_spread
from paper_appendices import PAPER, latest_report_path
from results_catalogue import check_outcomes
from species_study import ConditionName

ORGANISM = "celegans"
SPECIES_CURVE_CONDITION = ConditionName.GABAERGIC
OUTPUT = provenance.SIMULATOR_DIRECTORY.parent / "explainer" / "data" / "explainer-data.js"

# Open human connectome for the 3D view: region centre coordinates and fibre connections (diffusion MRI, undirected).
LAUSANNE = connectomes.DatasetSource(
    key="human_lausanne_consensus",
    organism="Homo sapiens (consensus of 70 adults, Lausanne parcellation)",
    url="https://zenodo.org/api/records/3067849/files/Consensus_Connectomes.mat/content",
    file_name="Consensus_Connectomes.mat",
    # Zenodo publishes MD5 5b4c1b791693a8e917be5373629bef26 for this file; the download matched it.
    sha256="258439dfb3a74787c18703896aa0aeba2ba41281cbd89800010e2bd596f5c122",
    licence="CC BY 4.0 (Zenodo record 3067849)",
    redistributed=True,
    citations=(
        "Shafiei, G., Markello, R. D., Talpalaru, T., Makowski, C., Kirschner, M., Devenyi, G. A., et al. (2019). Consensus structural and functional connectome from 70 young healthy adults [Data set]. Zenodo. https://doi.org/10.5281/zenodo.3067849",
        "Shafiei, G., Markello, R. D., Makowski, C., Talpalaru, A., Kirschner, M., Devenyi, G. A., et al. (2020). Spatial patterning of tissue volume loss in schizophrenia reflects brain network architecture. Biological Psychiatry, 87(8), 727-735. https://doi.org/10.1016/j.biopsych.2019.09.031",
    ),
)
# The 219-region scale among the five Lausanne scales (68, 114, 219, 448, 1000).
LAUSANNE_SCALE = 2
LAUSANNE_AUDITORY_REGION = "transversetemporal"


class LausanneMatrix(IntEnum):
    """Position of each matrix within one scale of the consensus file (its Readme)."""

    WEIGHTS = 0
    FIBRE_LENGTHS = 1
    FUNCTIONAL = 2
    COORDINATES = 3
    LABELS = 4


class LausanneLabel(IntEnum):
    """Columns of the region label table."""

    NAME = 0
    SHORT_NAME = 1
    NETWORK = 2
    HEMISPHERE = 3


# Reports whose test outcomes the explainer shows: (study, run label, required).
OUTCOME_REPORTS: tuple[tuple[str, str, bool], ...] = (
    ("validation", "full", True),
    ("glia", "full", True),
    ("congestion", "full", True),
    ("congestion", "confirmatory", True),
    ("species", "full", False),
)
# The predictions table of Section 7, read from each language version of the paper.
PREDICTION_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("en-GB", "white_paper_anesthesia_consensus.md", "## 7. Falsifiable predictions"),
    ("pt-BR", "white_paper_anesthesia_consensus.pt-BR.md", "## 7. Previsões falseáveis"),
)
PREDICTION_COLUMNS = ("number", "prediction", "test", "falsifiedIf")
# LaTeX the predictions use, rendered as plain text for the page.
MATH_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\\text\{([^}]*)\}", r"\1"),
    (r"_\{([^}]*)\}", r"<sub>\1</sub>"),
    (r"_([A-Za-z0-9])", r"<sub>\1</sub>"),
    (r"\\lambda", "λ"),
    (r"\\sigma", "σ"),
    (r"\\pi", "π"),
    (r"\$", ""),
)
OPENWORM_MIT_NOTICE = """C. elegans connectome: OpenWorm c302, https://github.com/openworm/c302
Underlying data: Cook, S. J., et al. (2019). Nature, 571, 63-71.

MIT License

Copyright (c) 2024 OpenWorm

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
LAUSANNE_NOTICE = """Human connectome (3D view): Shafiei, G., Markello, R. D., et al. (2019). Consensus structural and
functional connectome from 70 young healthy adults [Data set]. Zenodo. https://doi.org/10.5281/zenodo.3067849
Licence: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/
Changes: only the 219-region scale is kept; connections are listed as region pairs; values are rounded."""

FLYWIRE_NOTICE = """Fly wiring map (by neuropil): FlyWire Consortium (2024). FlyWire Whole-brain Connectome Connectivity Data
(version 783) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.10676866
Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. Nature, 634, 124-138.
Licence: Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/
Changes: neurons are grouped by the neuropil where they receive most input synapses; connections of at least
five synapses between neurons are summed into connections between neuropils; connections within a neuropil
are dropped."""

# ---------------------------------------------------------------------------
# Networks
# ---------------------------------------------------------------------------


def directed_connections(connectome: connectomes.Connectome) -> list[int]:
    pairs = sorted({(a, b) for a, b in zip(connectome.sources.tolist(), connectome.targets.tolist()) if a != b})
    return [node for pair in pairs for node in pair]


def worm_record(connectome: connectomes.Connectome) -> dict[str, object]:
    undirected = percolation_thresholds.undirected_graph(connectome)
    return {
        "name": connectome.name,
        "nodeCount": connectome.node_count,
        "connections": [node for edge in undirected.edges for node in edge],
        "directedConnections": directed_connections(connectome),
        "sensoryNodes": connectome.sensory_nodes.tolist(),
    }


def fly_record() -> dict[str, object]:
    """The fly's wiring by neuropil: each neuron in the neuropil where it receives most input, connections summed.

    A summary for drawing only; the study simulates the neuron-level network (connectomes.load_drosophila).
    """
    import pyarrow.feather as feather

    fly = connectomes.LOADERS["drosophila"](cal.CONNECTOME_SEED)
    names = feather.read_table(connectomes.fetch(connectomes.DROSOPHILA), columns=["neuropil"]).column("neuropil").dictionary_encode().combine_chunks().dictionary.to_pylist()
    count = len(names)
    source_neuropils, target_neuropils = fly.modules[fly.sources], fly.modules[fly.targets]
    between = source_neuropils != target_neuropils
    pair = source_neuropils[between].astype(np.int64) * count + target_neuropils[between]
    synapses = np.bincount(pair, weights=fly.weights[between], minlength=count * count).reshape(count, count)
    sources, targets = np.nonzero(synapses)
    return {
        "neuropils": names,
        "neuronCounts": np.bincount(fly.modules, minlength=count).tolist(),
        "connections": np.column_stack([sources, targets, synapses[sources, targets].astype(int)]).ravel().tolist(),
        "sensoryNeuropils": [names.index(name) for name in connectomes.DROSOPHILA_SENSORY_NEUROPILS],
        "neuronCount": fly.node_count,
        "connectionCount": fly.edge_count,
    }


def relative_mean(runs: list[dict], field: str) -> list[float]:
    """Each run divided by its own awake coherence, then averaged: the statistic of the paper's Figure 3."""
    mean, _ = mean_and_spread([[value / run["induction_coherence"][0] for value in run[field]] for run in runs])
    return np.round(mean, 4).tolist()


def species_curves_record() -> dict[str, object]:
    """Mean global coherence relative to awake during induction and emergence per organism, from the cross-species report."""
    report, document = latest_document("species", "full", required=True)
    curves = []
    for organism in cal.ORGANISMS:
        runs = [run for run in document["runs"] if run["organism"] == organism and run["condition"] == SPECIES_CURVE_CONDITION]
        curves.append({
            "organism": organism,
            "seeds": len(runs),
            "concentrations": runs[0]["concentrations"],
            "induction": relative_mean(runs, "induction_coherence"),
            "emergence": relative_mean(runs, "emergence_coherence"),
        })
    return {"report": report, "condition": SPECIES_CURVE_CONDITION, "curves": curves}


def human_record() -> dict[str, object]:
    """The 219-region Lausanne consensus connectome with region centre coordinates, for the 3D view."""
    document = scipy.io.loadmat(connectomes.fetch(LAUSANNE), squeeze_me=True, struct_as_record=False)
    matrices = document["LauConsensus"].Matrices[LAUSANNE_SCALE]
    weights = np.asarray(matrices[LausanneMatrix.WEIGHTS], dtype=float)
    labels = matrices[LausanneMatrix.LABELS]
    sources, targets = np.nonzero(np.triu(weights, k=1))
    name_of = lambda row: str(row[LausanneLabel.NAME]).strip()
    return {
        "name": "Human (Lausanne, 219 regions)",
        "nodeCount": int(weights.shape[0]),
        "connections": np.column_stack([sources, targets]).ravel().tolist(),
        "directedConnections": [],
        "coordinates": np.round(np.asarray(matrices[LausanneMatrix.COORDINATES], dtype=float), 1).ravel().tolist(),
        "sensoryNodes": [index for index, row in enumerate(labels) if name_of(row) == LAUSANNE_AUDITORY_REGION],
    }


# ---------------------------------------------------------------------------
# Model parameters
# ---------------------------------------------------------------------------


def agent_record(agent: dpc.AnaestheticAgent) -> dict[str, float]:
    return {
        "maxTransmissionFailure": agent.max_transmission_failure,
        "maxAddedJitterMs": agent.max_added_jitter_ms,
        "halfEffectConcentration": agent.half_effect_concentration,
        "hillCoefficient": agent.hill_coefficient,
        "arousalSuppression": agent.arousal_suppression,
    }


def model_record() -> dict[str, object]:
    scenario = dpc.REFERENCE_SCENARIO
    return {
        "integrationWindowMs": scenario.timing.integration_window_ms,
        "baselineJitterMs": scenario.timing.baseline_jitter_ms,
        "feedbackJitterMs": scenario.timing.feedback_jitter_ms,
        "arousalLevel": scenario.state.arousal_level,
        "quorumFraction": scenario.quorum_fraction,
        "agents": {"OMISSION": agent_record(dpc.GABAERGIC_LIKE_AGENT), "TIMING": agent_record(dpc.NMDA_ANTAGONIST_LIKE_AGENT)},
    }


def sleep_record() -> dict[str, float]:
    return {
        "arousalLevel": dpc.SLEEP_AROUSAL_LEVEL,
        "ratDownStateShare": dpc.SLEEP_DOWN_STATE_FRACTION,
        "humanDownStateShareUpper": dpc.HUMAN_SLEEP_DOWN_STATE_FRACTION_UPPER,
        "globalDownStateShare": glia.GLOBAL_DOWN_STATE_SHARE,
    }


def glia_record() -> dict[str, float]:
    return {"demyelinationJitterGain": glia.DEMYELINATION_JITTER_GAIN}


def plant_record() -> dict[str, object]:
    """Excitable plant tissue (FitzHugh-Nagumo sheet) as run by the species study."""
    design = cal.PLANT_TISSUE
    return {
        "rows": design.geometry.rows,
        "columns": design.geometry.columns,
        "timeStep": design.time_step,
        "durationSteps": design.duration_steps,
        "junctionConductances": list(cal.PLANT_JUNCTION_CONDUCTANCES),
        "fitzHugh": {"a": plant_tissue.FITZHUGH_A, "b": plant_tissue.FITZHUGH_B, "epsilon": plant_tissue.FITZHUGH_EPSILON},
        "restingVoltage": plant_tissue.RESTING_VOLTAGE,
        "restingRecovery": plant_tissue.RESTING_RECOVERY,
        "firingVoltage": plant_tissue.FIRING_VOLTAGE,
        "stimulusVoltage": plant_tissue.STIMULUS_VOLTAGE,
        "agent": agent_record(design.agent),
    }


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------


# Cached: several records read the same report, and none of them changes it.
@functools.cache
def latest_document(study: str, label: str, *, required: bool) -> tuple[str, dict] | None:
    """The latest report of a study, or None when it is optional and has not been run yet."""
    try:
        path = latest_report_path(study, label).with_suffix(".json")
    except FileNotFoundError:
        if required:
            raise FileNotFoundError(f"The explainer needs a {label} {study} report; run that study first") from None
        print(f"warning: no {label} {study} report yet; the page will show its results as pending", file=sys.stderr)
        return None
    return path.name, json.loads(path.read_text())


def outcomes_from(study: str, label: str, report: str, document: dict) -> list[dict[str, object]]:
    outcomes = [
        {
            "report": report,
            "study": study,
            "label": label,
            "identifier": outcome["identifier"],
            "statement": outcome["statement"],
            "group": outcome["group"],
            "kind": outcome.get("kind", reporting.TEST),
            "holding": outcome["runs_holding"],
            "applicable": outcome["runs_applicable"],
        }
        for outcome in check_outcomes(document)
    ]
    if not outcomes:
        raise ValueError(f"{report}: no check outcomes found; has the report format changed?")
    keys = [(outcome["identifier"], outcome["group"]) for outcome in outcomes]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{report}: an identifier appears twice in the same group")
    return outcomes


def outcomes_record() -> list[dict[str, object]]:
    outcomes = []
    for study, label, required in OUTCOME_REPORTS:
        found = latest_document(study, label, required=required)
        if found is not None:
            outcomes.extend(outcomes_from(study, label, *found))
    return outcomes


def plain_text(markdown: str) -> str:
    text = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", markdown)
    for pattern, replacement in MATH_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text.strip()


def predictions_from(paper: str, heading: str) -> list[dict[str, str]]:
    section = (PAPER.parent / paper).read_text().split(heading, 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if re.match(r"^\| *\d+ *\|", line)]
    return [dict(zip(PREDICTION_COLUMNS, (plain_text(cell) for cell in row.strip("|").split(" | ")))) for row in rows]


def predictions_record() -> dict[str, list[dict[str, str]]]:
    """The falsifiable predictions of Section 7, per language, read from the paper itself."""
    predictions = {locale: predictions_from(paper, heading) for locale, paper, heading in PREDICTION_SOURCES}
    counts = {locale: len(rows) for locale, rows in predictions.items()}
    if len(set(counts.values())) != 1:
        raise ValueError(f"The language versions of the paper list different numbers of predictions: {counts}")
    return predictions


def inertia_record() -> dict[str, object]:
    """Measured loss-to-recovery ratios and the λ each calibrates to at the reference arousal level."""
    report, document = latest_document("calibration_feedback", "full", required=True)
    rows = [row for row in document["calibrations"] if row["calibration"]["arousal_level"] == dpc.REFERENCE_AROUSAL_LEVEL]
    return {
        "report": report,
        "targets": [{"ratio": row["target"]["ratio"], "source": row["target"]["source"], "feedbackMs": row["calibration"]["feedback_ms"]} for row in rows],
    }


def plant_claims_record() -> dict[str, object] | None:
    found = latest_document("species", "full", required=False)
    if found is None:
        return None
    report, document = found
    return {"report": report, "claims": [{"statement": statement, "holds": holds} for statement, holds in document["plant_claims"].items()]}


def thresholds_record() -> dict[str, object]:
    report, document = latest_document("percolation", "full", required=True)
    return {"report": report, "organisms": document["thresholds"]}


def validation_record() -> dict[str, object]:
    report, document = latest_document("validation", "full", required=True)
    return {"report": report, "statistics": document["statistics"]}


def main() -> int:
    connectome = connectomes.LOADERS[ORGANISM](cal.CONNECTOME_SEED)
    payload = {
        "model": model_record(),
        "sleep": sleep_record(),
        "glia": glia_record(),
        "plant": plant_record(),
        "network": worm_record(connectome),
        "human": human_record(),
        "fly": fly_record(),
        "speciesCurves": species_curves_record(),
        "thresholds": thresholds_record(),
        "validation": validation_record(),
        "outcomes": outcomes_record(),
        "inertia": inertia_record(),
        "predictions": predictions_record(),
        "plantClaims": plant_claims_record(),
    }
    notice = "\n".join(f" * {line}".rstrip() for line in f"{OPENWORM_MIT_NOTICE}\n\n{LAUSANNE_NOTICE}\n\n{FLYWIRE_NOTICE}".splitlines())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        f"/*\n * Generated by simulator/explainer_export.py; do not edit by hand.\n *\n{notice}\n */\n"
        f"globalThis.DPC_EXPLAINER_DATA = Object.freeze({json.dumps(payload, separators=(',', ':'))});\n"
    )
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
