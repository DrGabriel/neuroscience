"""Percolation and quorum thresholds of empirical connectomes: formulas against measurement.

Two thresholds are computed for each connectome treated as undirected, and the quorum threshold
is also measured on the directed wiring:

1. Onset π_c: below it no giant component exists in a random network with the same degree
   distribution, π_c = <k> / (<k²> − <k>) (Callaway et al., 2000).
2. Quorum π_q: the occupation at which the giant component first contains a fraction q* of
   all nodes. For a random network with degree distribution p_k it follows from the
   generating functions G0(x) = Σ p_k x^k and G1(x) = G0'(x) / <k> (Newman, 2010; Callaway
   et al., 2000): S = 1 − G0(u), where u = 1 − π + π G1(u). This is the general formula: it
   needs only an organism's degree distribution and the quorum.

π_q is also measured on the real wiring with the Newman-Ziff algorithm. Agreement needs signals
to travel both ways, so on the directed wiring the quorum is measured on the largest strongly
connected component, whose members can each reach every other member. Both are converted
into the critical transmission failure and critical timing jitter of the coherence model
(Section 4.1), π = (1 − p) · erf(W / (2√2 σ)):

    p_q = 1 − π_q / erf(W / (2√2 σ_baseline))     (baseline jitter only)
    σ_q = W / (2√2 · erf⁻¹(π_q))                 (no transmission failure)

Usage: ../.venv/bin/python percolation_thresholds.py [--quick]
Dependencies: numpy, scipy (for erf⁻¹); dpc_simulator for the Newman-Ziff curve.
"""

from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.special import erfinv

import calibration as cal
import connectomes
import dpc_simulator as dpc
import provenance
import reporting

REPORTED_PACKAGES = (*provenance.NUMERICAL_PACKAGES, "pyarrow")
OCCUPATION_RESOLUTION = 1e-4
FIXED_POINT_ITERATIONS = 2000
BISECTION_STEPS = 60
DIRECTED_BISECTION_STEPS = 16
FULL_SEEDS = 10
QUICK_SEEDS = 2


@dataclass(frozen=True)
class OrganismThreshold:
    organism: str
    node_count: int
    undirected_edge_count: int
    mean_degree: float
    mean_square_degree: float
    onset_threshold_formula: float
    quorum_threshold_formula: float
    quorum_threshold_measured_mean: float
    quorum_threshold_measured_sd: float
    critical_failure_formula: float
    critical_failure_measured: float
    critical_jitter_ms_formula: float
    critical_jitter_ms_measured: float
    quorum_threshold_directed_mean: float
    quorum_threshold_directed_sd: float
    critical_failure_directed: float
    critical_jitter_ms_directed: float
    quorum_threshold_measured_by_seed: tuple[float, ...]
    quorum_threshold_directed_by_seed: tuple[float, ...]


def undirected_graph(connectome: connectomes.Connectome) -> dpc.Graph:
    low = np.minimum(connectome.sources, connectome.targets)
    high = np.maximum(connectome.sources, connectome.targets)
    keep = low != high
    pairs = np.unique(np.stack([low[keep], high[keep]], axis=1), axis=0)
    return dpc.Graph(connectome.node_count, tuple(map(tuple, pairs.tolist())))


def onset_threshold(degrees: np.ndarray) -> tuple[float, float, float]:
    mean, mean_square = degrees.mean(), (degrees**2).mean()
    return mean, mean_square, mean / (mean_square - mean)


@dataclass(frozen=True)
class DegreeDistribution:
    """Degree distribution p_k and excess-degree distribution k p_k / <k> of a network."""

    degrees: np.ndarray
    probabilities: np.ndarray
    excess: np.ndarray

    @classmethod
    def of(cls, degrees: np.ndarray) -> DegreeDistribution:
        counts = np.bincount(degrees.astype(int))
        probabilities = counts / counts.sum()
        k = np.arange(probabilities.size)
        return cls(k, probabilities, k * probabilities / (k * probabilities).sum())

    def giant_fraction(self, occupation: float) -> float:
        """Expected giant-component fraction from the generating functions G0 and G1."""
        k = self.degrees
        u = 0.0
        for _ in range(FIXED_POINT_ITERATIONS):
            following = 1 - occupation + occupation * float(np.sum(self.excess[1:] * u ** (k[1:] - 1)))
            if following == u:
                break
            u = following
        return 1 - float(np.sum(self.probabilities * u**k))

    def quorum_threshold(self, quorum: float) -> float:
        """Smallest occupation at which the giant component reaches the quorum, by bisection."""
        return dpc.smallest_crossing(lambda occupation: self.giant_fraction(occupation) >= quorum, BISECTION_STEPS)


def quorum_threshold_measured(graph: dpc.Graph, quorum: float, seed: int) -> float:
    curve = dpc.PercolationCurve.from_graph(graph, random.Random(seed))
    occupations = np.arange(0.0, 1.0 + OCCUPATION_RESOLUTION, OCCUPATION_RESOLUTION)
    return float(next(p for p in occupations if curve.giant_fraction(p) >= quorum))


def largest_strong_component_share(connectome: connectomes.Connectome, kept: np.ndarray) -> float:
    adjacency = csr_matrix(
        (np.ones(int(kept.sum())), (connectome.sources[kept], connectome.targets[kept])),
        shape=(connectome.node_count, connectome.node_count),
    )
    _, labels = connected_components(adjacency, directed=True, connection="strong")
    return float(np.bincount(labels).max() / connectome.node_count)


def quorum_threshold_directed(connectome: connectomes.Connectome, quorum: float, seed: int) -> float:
    """Smallest occupation at which the largest strongly connected component reaches the quorum."""
    draws = np.random.default_rng(seed).random(connectome.edge_count)
    return dpc.smallest_crossing(lambda occupation: largest_strong_component_share(connectome, draws < occupation) >= quorum, DIRECTED_BISECTION_STEPS)


def critical_failure(threshold: float) -> float:
    """Transmission failure at which baseline-jitter coherence falls to the threshold."""
    coherent_share = dpc.within_window(dpc.REFERENCE_INTEGRATION_WINDOW_MS, dpc.REFERENCE_BASELINE_JITTER_MS)
    return max(0.0, 1 - threshold / coherent_share)


def critical_jitter_ms(threshold: float) -> float:
    """Timing jitter at which coherence falls to the threshold with no transmission failure."""
    return dpc.REFERENCE_INTEGRATION_WINDOW_MS / (2 * math.sqrt(2) * float(erfinv(threshold)))


def threshold_for(organism: str, seeds: int) -> OrganismThreshold:
    connectome = connectomes.LOADERS[organism](cal.CONNECTOME_SEED)
    graph = undirected_graph(connectome)
    degrees = np.asarray(graph.degrees(), dtype=float)
    mean, mean_square, onset = onset_threshold(degrees)
    formula = DegreeDistribution.of(degrees).quorum_threshold(cal.QUORUM_FRACTION)
    measured = [quorum_threshold_measured(graph, cal.QUORUM_FRACTION, cal.BASE_SEED + index) for index in range(seeds)]
    measured_mean = statistics.fmean(measured)
    directed = [quorum_threshold_directed(connectome, cal.QUORUM_FRACTION, cal.BASE_SEED + index) for index in range(seeds)]
    directed_mean = statistics.fmean(directed)
    return OrganismThreshold(
        organism=cal.ORGANISMS[organism].display_name,
        node_count=graph.node_count,
        undirected_edge_count=len(graph.edges),
        mean_degree=mean,
        mean_square_degree=mean_square,
        onset_threshold_formula=onset,
        quorum_threshold_formula=formula,
        quorum_threshold_measured_mean=measured_mean,
        quorum_threshold_measured_sd=statistics.stdev(measured) if len(measured) > 1 else 0.0,
        critical_failure_formula=critical_failure(formula),
        critical_failure_measured=critical_failure(measured_mean),
        critical_jitter_ms_formula=critical_jitter_ms(formula),
        critical_jitter_ms_measured=critical_jitter_ms(measured_mean),
        quorum_threshold_directed_mean=directed_mean,
        quorum_threshold_directed_sd=statistics.stdev(directed) if len(directed) > 1 else 0.0,
        critical_failure_directed=critical_failure(directed_mean),
        critical_jitter_ms_directed=critical_jitter_ms(directed_mean),
        quorum_threshold_measured_by_seed=tuple(measured),
        quorum_threshold_directed_by_seed=tuple(directed),
    )


def to_markdown(document: dict[str, object]) -> str:
    rows = [
        [
            t["organism"],
            f"{t['node_count']:,}",
            f"{t['undirected_edge_count']:,}",
            f"{t['mean_degree']:.1f}",
            f"{t['onset_threshold_formula']:.4f}",
            f"{t['quorum_threshold_formula']:.4f}",
            f"{t['quorum_threshold_measured_mean']:.4f} ± {t['quorum_threshold_measured_sd']:.4f}",
            f"{t['critical_failure_formula']:.3f} / {t['critical_failure_measured']:.3f}",
            f"{t['critical_jitter_ms_formula']:.1f} / {t['critical_jitter_ms_measured']:.1f}",
        ]
        for t in document["thresholds"]
    ]
    header = [
        "Organism", "Nodes", "Connections", "Mean degree", "Onset π_c (formula)", f"Quorum π_q, q* = {cal.QUORUM_FRACTION} (formula)",
        "Quorum π_q (measured)", "Critical failure p_q (formula / measured)", "Critical jitter σ_q, ms (formula / measured)",
    ]
    directed_rows = [
        [
            t["organism"],
            f"{t['quorum_threshold_measured_mean']:.4f}",
            f"{t['quorum_threshold_directed_mean']:.4f} ± {t['quorum_threshold_directed_sd']:.4f}",
            f"{t['critical_failure_directed']:.3f}",
            f"{t['critical_jitter_ms_directed']:.1f}",
        ]
        for t in document["thresholds"]
    ]
    directed_header = ["Organism", "Quorum π_q, undirected", "Quorum π_q, directed (strong component)", "Critical failure p_q", "Critical jitter σ_q, ms"]
    return "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        "### Percolation and quorum thresholds (connectomes treated as undirected)",
        "",
        *reporting.markdown_table(header, rows),
        "",
        "### Quorum threshold on the directed wiring (largest strongly connected component)",
        "",
        *reporting.markdown_table(directed_header, directed_rows),
        "",
    ])


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true")
    quick = parser.parse_args(arguments).quick
    started = datetime.now(timezone.utc)
    seeds = QUICK_SEEDS if quick else FULL_SEEDS
    thresholds = []
    for done, organism in enumerate(cal.ORGANISMS, start=1):
        thresholds.append(threshold_for(organism, seeds))
        reporting.report_progress(reporting.Progress("percolation thresholds", done, len(cal.ORGANISMS), (datetime.now(timezone.utc) - started).total_seconds()))
    document = {
        "label": reporting.RunLabel.QUICK if quick else reporting.RunLabel.FULL,
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), REPORTED_PACKAGES),
        "seeds": [cal.BASE_SEED + index for index in range(seeds)],
        "thresholds": [asdict(t) for t in thresholds],
    }
    reporting.publish("percolation", document, to_markdown(document))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
