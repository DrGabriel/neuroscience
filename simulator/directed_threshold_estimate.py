"""Directed generating-function estimate of the quorum threshold, against the directed measurement of Appendix B.5
(Appendix C.14, analysis B).

For each connectome's directed wiring, the onset of a giant strongly connected component in an uncorrelated directed
network with the same joint in/out-degree distribution, pi_c = <k> / <k_in k_out> (Newman, Strogatz and Watts, 2001;
Dorogovtsev, Mendes and Samukhin, 2001), and the occupation at which the estimated strong component reaches the quorum
(round3_study.directed_estimate), are compared with the directed quorum threshold that Appendix B.5 measured on the
real wiring. The computation is deterministic and is reported without a verdict; the estimate ignores degree
correlations, among them reciprocity.

Usage:
    ../.venv/bin/python directed_threshold_estimate.py            # C. elegans, Drosophila and the human connectome
    ../.venv/bin/python directed_threshold_estimate.py --smoke    # C. elegans only: seconds

Smoke reports are labelled quick, are ignored by git and are not results.
Dependencies: numpy, scipy, pyarrow (to load the connectomes).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

import calibration as cal
import connectomes
import percolation_thresholds as thresholds
import provenance
import reporting
from round3_study.directed_estimate import JointDegrees

REPORT_KIND = "directed_threshold_estimate"
# The report of Appendix B.5, whose directed measurement the estimate is compared with.
MEASURED_REPORT = "percolation_full_20261020T011339Z.json"
FULL_ORGANISMS = ("celegans", "drosophila", "human")
SMOKE_ORGANISMS = ("celegans",)


@dataclass(frozen=True)
class DirectedEstimate:
    organism: str
    population_count: int
    arc_count: int
    mean_degree: float
    mean_in_out_product: float
    onset_threshold: float
    quorum_threshold: float
    measured_quorum_threshold_mean: float
    measured_quorum_threshold_sd: float

    @property
    def estimate_over_measurement(self) -> float:
        return self.quorum_threshold / self.measured_quorum_threshold_mean


def measured_directed_thresholds(report: dict[str, object]) -> dict[str, tuple[float, float]]:
    """Mean and SD of the directed quorum threshold that B.5 measured, by display name."""
    return {t["organism"]: (t["quorum_threshold_directed_mean"], t["quorum_threshold_directed_sd"]) for t in report["thresholds"]}


def estimate_for(organism: str, measured: dict[str, tuple[float, float]]) -> DirectedEstimate:
    connectome = connectomes.LOADERS[organism](cal.CONNECTOME_SEED)
    joint = JointDegrees.of(connectome)
    measured_mean, measured_sd = measured[cal.ORGANISMS[organism].display_name]
    return DirectedEstimate(
        organism=cal.ORGANISMS[organism].display_name,
        population_count=connectome.node_count,
        arc_count=int((connectome.sources != connectome.targets).sum()),
        mean_degree=joint.mean_degree(),
        mean_in_out_product=joint.mean_in_out_product(),
        onset_threshold=joint.onset_threshold(),
        quorum_threshold=joint.quorum_threshold(cal.QUORUM_FRACTION),
        measured_quorum_threshold_mean=measured_mean,
        measured_quorum_threshold_sd=measured_sd,
    )


def estimate_row(estimate: dict[str, object]) -> list[str]:
    return [
        estimate["organism"],
        f"{estimate['population_count']:,}",
        f"{estimate['arc_count']:,}",
        f"{estimate['mean_degree']:.2f}",
        f"{estimate['mean_in_out_product']:.1f}",
        f"{estimate['onset_threshold']:.4f}",
        f"{estimate['quorum_threshold']:.4f}",
        f"{estimate['measured_quorum_threshold_mean']:.4f} ± {estimate['measured_quorum_threshold_sd']:.4f}",
        f"{estimate['estimate_over_measurement']:.2f}",
        f"{thresholds.critical_failure(estimate['quorum_threshold']):.3f}",
        f"{thresholds.critical_jitter_ms(estimate['quorum_threshold']):.1f}",
    ]


HEADER = [
    "Organism", "Populations", "Arcs", "Mean degree <k>", "<k_in k_out>", "Onset π_c = <k>/<k_in k_out>",
    f"Quorum π_q, q* = {cal.QUORUM_FRACTION} (estimate)", "Quorum π_q, directed (B.5, measured)", "Estimate / measured",
    "Critical failure p_q (estimate)", "Critical jitter σ_q, ms (estimate)",
]


def to_markdown(document: dict[str, object]) -> str:
    return "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        f"Measured thresholds from `{document['measured_report']}` (Appendix B.5). Deterministic estimate, reported without a verdict;",
        "it assumes an uncorrelated directed network and so ignores degree correlations, reciprocity among them.",
        "",
        "### Giant strongly connected component: generating-function estimate against the directed measurement",
        "",
        *reporting.markdown_table(HEADER, [estimate_row(e) for e in document["estimates"]]),
        "",
    ])


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="C. elegans only")
    smoke = parser.parse_args(arguments).smoke
    started = datetime.now(timezone.utc).isoformat()
    measured = measured_directed_thresholds(json.loads((reporting.RESULTS_DIRECTORY / MEASURED_REPORT).read_text()))
    estimates = [estimate_for(organism, measured) for organism in (SMOKE_ORGANISMS if smoke else FULL_ORGANISMS)]
    document = {
        "label": reporting.RunLabel.QUICK if smoke else reporting.RunLabel.FULL,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), thresholds.REPORTED_PACKAGES),
        "measured_report": MEASURED_REPORT,
        "estimates": [asdict(e) | {"estimate_over_measurement": e.estimate_over_measurement} for e in estimates],
    }
    reporting.publish(REPORT_KIND, document, to_markdown(document))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
