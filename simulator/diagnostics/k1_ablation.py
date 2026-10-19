"""Diagnostic, post hoc, no verdict: which code change moved the worm's K1 result (19 October 2026).

In the overnight species run (species_full_20261019T025707Z) the NMDA-antagonist-like agent on sensory pathways
left the worm's broadcast at a median 109% of awake; in the rerun on corrected code, 47%. Five changes between the
two runs can affect that condition. Each is undone on its own, on the current code. Two variants check the harness:
undoing nothing must reproduce the rerun, and undoing all five must reproduce the overnight run, seed for seed.

Usage: ../.venv/bin/python diagnostics/k1_ablation.py
"""

from __future__ import annotations

import csv
import enum
import json
import pickle
import subprocess
import sys
import types
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path

import numpy as np

SIMULATOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SIMULATOR))

import calibration as cal  # noqa: E402
import connectomes  # noqa: E402
import phase_dynamics as dynamics  # noqa: E402
import provenance  # noqa: E402
import species_study as study  # noqa: E402

ORGANISM = "celegans"
OLD_MEASUREMENT_STEPS = 600
WORKER_PROCESSES = 4
OLD_CODE_COMMIT = "4fc14f4"
OVERNIGHT_REPORT = SIMULATOR / "results" / "species_full_20261019T025707Z.json"
RERUN_CHECKPOINT = SIMULATOR / "results" / "live" / "species_c_elegans.pickle"
OUTPUT_DIRECTORY = SIMULATOR / "results" / "diagnostics"
COMPARED_FIELDS = ("deepest_coherence_fraction", "awake_broadcast_ratio", "deepest_broadcast_ratio")
REPRODUCTION_TOLERANCE = 1e-9


class Change(enum.Enum):
    WINDOW = "measurement window of 600 steps instead of two whole stimulus cycles"
    QUADRATURE = "timing errors summed instead of combined in quadrature"
    NEURONS_ONLY = "muscles and other cells kept in the graph"
    SELF_LOOPS = "chemical self-connections kept"
    GAP_JUNCTIONS = "gap junctions as listed and mirrored, so most count twice per direction"


VARIANTS: dict[str, frozenset[Change]] = {
    "none undone (must match the rerun)": frozenset(),
    **{f"undo: {change.value}": frozenset({change}) for change in Change},
    "all undone (must match the overnight run)": frozenset(Change),
}


@dataclass(frozen=True)
class AblationTask:
    variant: str
    seed: int


def celegans_edges(pairs: np.ndarray, weights: np.ndarray, is_gap_junction: np.ndarray, undone: frozenset[Change]) -> tuple[np.ndarray, ...]:
    """Sources, targets and weights. With both edge changes undone, the order is the old loader's, row for row."""
    chemical = ~is_gap_junction if Change.SELF_LOOPS in undone else ~is_gap_junction & (pairs[:, 0] != pairs[:, 1])
    if Change.GAP_JUNCTIONS in undone:
        listed = chemical | is_gap_junction
        return (
            np.concatenate([pairs[listed, 0], pairs[is_gap_junction, 1]]),
            np.concatenate([pairs[listed, 1], pairs[is_gap_junction, 0]]),
            np.concatenate([weights[listed], weights[is_gap_junction]]),
        )
    junctions, junction_weights = connectomes.undirected_gap_junctions(pairs[is_gap_junction], weights[is_gap_junction])
    return (
        np.concatenate([pairs[chemical, 0], junctions[:, 0], junctions[:, 1]]),
        np.concatenate([pairs[chemical, 1], junctions[:, 1], junctions[:, 0]]),
        np.concatenate([weights[chemical], junction_weights, junction_weights]),
    )


def load_celegans_variant(undone: frozenset[Change]) -> connectomes.Connectome:
    """connectomes.load_celegans with the chosen loader changes undone."""
    keeps_every_cell = Change.NEURONS_ONLY in undone
    with connectomes.fetch(connectomes.CELEGANS).open(newline="") as handle:
        rows = [
            (row["Source"].strip(), row["Target"].strip(), float(row["Weight"]), row["Type"].strip())
            for row in csv.DictReader(handle)
            if keeps_every_cell or (connectomes.is_celegans_neuron(row["Source"].strip()) and connectomes.is_celegans_neuron(row["Target"].strip()))
        ]
    node_index, names = connectomes.dense_indices([name for source, target, _, _ in rows for name in (source, target)])
    pairs = node_index.reshape(-1, 2)
    is_gap_junction = np.array([kind == "electrical" for _, _, _, kind in rows])
    sources, targets, weights = celegans_edges(pairs, np.array([weight for _, _, weight, _ in rows]), is_gap_junction, undone)
    node_count = len(names)
    return connectomes.Connectome(
        name="C. elegans",
        organism=connectomes.CELEGANS.organism,
        node_count=node_count,
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=weights.astype(np.float32),
        modules=connectomes.spectral_modules(node_count, sources, targets, cal.CONNECTOME_SEED),
        module_basis=f"spectral clustering, about {connectomes.NODES_PER_SPECTRAL_MODULE} nodes per module",
        sensory_nodes=np.array(
            [index for index, name in enumerate(names) if name[:3] in connectomes.CELEGANS_AMPHID_SENSORY_CLASSES and name[3:] in ("L", "R")],
            dtype=np.int32,
        ),
        sensory_description="amphid sensory neurons (12 classes, left and right)",
    )


CURRENT_IMPAIRMENT_AT = dynamics.ConnectionImpairment.at


def summed_impairment_at(self: dynamics.ConnectionImpairment, concentration: float) -> dynamics.ImpairedConnectivity:
    """ConnectionImpairment.at as committed in OLD_CODE_COMMIT: the two standard deviations added, not in quadrature."""
    transmits = self._failure_draws >= self._agent.transmission_failure(concentration)
    jitter_ms = self._dynamics.baseline_jitter_ms * self._baseline_weights + self._agent.added_jitter_ms(concentration) * self._agent_weights
    frequency_hz = dynamics.reference_frequency_hz(self._dynamics, self._agent, concentration)
    jitter_sd = dynamics.milliseconds_to_radians(jitter_ms, frequency_hz)
    fixed_lags = dynamics.milliseconds_to_radians(self._delays_ms, frequency_hz)
    if self._jitter_dynamics is dynamics.JitterDynamics.FIXED:
        fixed_lags, jitter_sd = fixed_lags + self._jitter_draws * jitter_sd, np.zeros_like(jitter_sd)
    return dynamics.ImpairedConnectivity(
        sources=self._connectome.sources[transmits],
        targets=self._connectome.targets[transmits],
        weights=self._weights[transmits],
        fixed_lags=fixed_lags[transmits],
        jitter_sd=np.broadcast_to(jitter_sd, transmits.shape)[transmits],
    )


def ketamine_task(seed: int) -> study.RunTask:
    condition = next(c for c in study.build_conditions(cal.FULL_INTEGRATION) if c.name == study.ConditionName.KETAMINE_PATHWAYS)
    return study.RunTask(ORGANISM, condition, seed)


def run_ablation_task(task: AblationTask) -> tuple[str, int, dict[str, float | None]]:
    undone = VARIANTS[task.variant]
    connectomes.LOADERS[ORGANISM] = lambda _seed: load_celegans_variant(undone)
    study.load_connectome.cache_clear()  # cached per organism: without this a worker reuses the previous variant's graph
    dynamics.ConnectionImpairment.at = summed_impairment_at if Change.QUADRATURE in undone else CURRENT_IMPAIRMENT_AT
    run = ketamine_task(task.seed)
    design = study.design_for(run)
    if Change.WINDOW in undone:
        design = replace(design, integration=replace(design.integration, measurement_steps=OLD_MEASUREMENT_STEPS))
    summary = study.run_task(run, design)
    return task.variant, task.seed, {field: getattr(summary, field) for field in COMPARED_FIELDS}


def old_loader() -> types.FunctionType:
    """load_celegans exactly as committed in OLD_CODE_COMMIT, run against the current helpers and data."""
    source = subprocess.run(["git", "show", f"{OLD_CODE_COMMIT}:simulator/connectomes.py"], cwd=SIMULATOR, capture_output=True, text=True, check=True).stdout
    module = types.ModuleType("connectomes_old")
    module.__file__ = str(SIMULATOR / "connectomes.py")
    sys.modules[module.__name__] = module
    exec(compile(source, "connectomes_old.py", "exec"), module.__dict__)
    return module.load_celegans


def same_graph(first: connectomes.Connectome, second: connectomes.Connectome) -> bool:
    return all(np.array_equal(getattr(first, field), getattr(second, field)) for field in ("sources", "targets", "weights", "sensory_nodes", "modules")) and first.node_count == second.node_count


def check_loaders() -> dict[str, bool]:
    return {
        "nothing undone equals the current loader": same_graph(load_celegans_variant(frozenset()), connectomes.load_celegans(cal.CONNECTOME_SEED)),
        "all loader changes undone equals the old loader": same_graph(
            load_celegans_variant(frozenset({Change.NEURONS_ONLY, Change.SELF_LOOPS, Change.GAP_JUNCTIONS})), old_loader()(cal.CONNECTOME_SEED)
        ),
    }


class StudyUnpickler(pickle.Unpickler):
    """The checkpoint was written by species_study run as a script, so its classes are recorded under __main__."""

    def find_class(self, module: str, name: str) -> object:
        return super().find_class(study.__name__ if module == "__main__" else module, name)


def rerun_values() -> dict[int, dict[str, float | None]]:
    runs = []
    with RERUN_CHECKPOINT.open("rb") as handle:
        unpickler = StudyUnpickler(handle)
        while True:
            try:
                runs.append(unpickler.load()[1])
            except EOFError:
                break
    return {r.seed: {field: getattr(r, field) for field in COMPARED_FIELDS} for r in runs if r.condition == study.ConditionName.KETAMINE_PATHWAYS}


def overnight_values() -> dict[int, dict[str, float | None]]:
    runs = json.loads(OVERNIGHT_REPORT.read_text())["runs"]
    return {r["seed"]: {field: r[field] for field in COMPARED_FIELDS} for r in runs if r["organism"] == ORGANISM and r["condition"] == study.ConditionName.KETAMINE_PATHWAYS}


def largest_difference(found: dict[int, dict[str, float | None]], expected: dict[int, dict[str, float | None]]) -> float:
    return max(abs(found[seed][field] - expected[seed][field]) for seed in expected for field in COMPARED_FIELDS)


def variant_summary(values: dict[int, dict[str, float | None]]) -> dict[str, object]:
    relative = [v["deepest_broadcast_ratio"] / v["awake_broadcast_ratio"] for v in values.values()]
    holds = [study.disconnected_but_internally_coherent(types.SimpleNamespace(**v)) for v in values.values()]
    return {
        "median_broadcast_share_of_awake": float(np.median(relative)),
        "quorum_held": sum(v["deepest_coherence_fraction"] >= cal.QUORUM_FRACTION for v in values.values()),
        "k1_holds": sum(holds),
        "runs": len(values),
    }


def to_markdown(document: dict[str, object]) -> str:
    lines = [
        "# K1 diagnostic: which code change moved the worm's result",
        "",
        "Post hoc diagnostic, no verdict. Script: `simulator/diagnostics/k1_ablation.py`.",
        "",
        "| Check | Result |",
        "|---|---|",
        *(f"| {name} | {result} |" for name, result in document["checks"].items()),
        "",
        "| Variant | Broadcast at deepest dose, median share of awake | Quorum held | K1 holds |",
        "|---|---|---|---|",
        *(
            f"| {name} | {summary['median_broadcast_share_of_awake']:.0%} | {summary['quorum_held']}/{summary['runs']} | {summary['k1_holds']}/{summary['runs']} |"
            for name, summary in document["summaries"].items()
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    provenance.record_launch()
    started = datetime.now(timezone.utc)
    checks: dict[str, object] = dict(check_loaders())
    rerun, overnight = rerun_values(), overnight_values()  # read first: the rerun deletes its checkpoint when it ends
    seeds = [cal.BASE_SEED + index for index in range(cal.ORGANISMS[ORGANISM].full_study_seeds)]
    tasks = [AblationTask(variant, seed) for variant in VARIANTS for seed in seeds]
    values: dict[str, dict[int, dict[str, float | None]]] = {variant: {} for variant in VARIANTS}
    with Pool(WORKER_PROCESSES) as pool:
        for done, (variant, seed, result) in enumerate(pool.imap_unordered(run_ablation_task, tasks), start=1):
            values[variant][seed] = result
            print(f"{done}/{len(tasks)}", flush=True)
    names = list(VARIANTS)
    checks["largest difference from the rerun, nothing undone"] = largest_difference(values[names[0]], rerun)
    checks["largest difference from the overnight run, all undone"] = largest_difference(values[names[-1]], overnight)
    document = {
        "label": "diagnostic",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), ("numpy", "scipy")),
        "old_code_commit": OLD_CODE_COMMIT,
        "checks": checks,
        "summaries": {variant: variant_summary(values[variant]) for variant in VARIANTS},
        "runs": {variant: {str(seed): v for seed, v in sorted(values[variant].items())} for variant in VARIANTS},
    }
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    stem = f"k1_ablation_{started.strftime('%Y%m%dT%H%M%SZ')}"
    (OUTPUT_DIRECTORY / f"{stem}.json").write_text(json.dumps(document, indent=2))
    (OUTPUT_DIRECTORY / f"{stem}.md").write_text(to_markdown(document))
    print(to_markdown(document))
    return 0


if __name__ == "__main__":
    sys.exit(main())
