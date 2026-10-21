"""Static reciprocity and maximal-timing-error estimates on the human connectome (Appendix C.14, analysis C).

Post hoc static estimates requested by referees, reported without a verdict. No oscillators run: as in
pair_rule_diagnostic.py, every arc is on time independently with the static probability at three times the EC50 of the
NMDA-antagonist-like agent, and the giant component is read under the either-direction rule of Appendix C.12. (i) A
share r of the 17,865 human fibres is made two-way and the rest one-way in a random direction, for r from 0 to 1;
(ii) with every fibre two-way, the agent's maximal added timing error is swept from 20 to 80 ms. For each sweep the
value at which the mean giant component first falls below q* = 0.5 is interpolated (round3_study.reciprocity).

Usage:
    ../.venv/bin/python reciprocity_estimate.py            # both sweeps, 10 assignments of 20 draws per value
    ../.venv/bin/python reciprocity_estimate.py --smoke    # two values of r, one timing error, one assignment of two
                                                           # draws, on seeds outside every block

Smoke reports are labelled quick, are ignored by git and are not results.
Dependencies: numpy, scipy, pyarrow (to load the connectomes).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

import numpy as np

import calibration as cal
import connectomes
import percolation_thresholds as thresholds
import provenance
import reporting
from connection_pairs import AnatomicalConnections
from round3_study import reciprocity as estimate
from round3_study.seeds import RECIPROCITY_BLOCK, SMOKE_BLOCK, SeedBlock

REPORT_KIND = "reciprocity_estimate"
ORGANISM = "human"
NOT_CROSSED = "not crossed in the range swept"


@dataclass(frozen=True)
class EstimateDesign:
    label: str
    reciprocal_shares: tuple[float, ...]
    maximal_timing_errors_ms: tuple[float, ...]
    size: estimate.SweepSize
    seeds: SeedBlock


FULL_DESIGN = EstimateDesign(reporting.RunLabel.FULL, estimate.RECIPROCAL_SHARES, estimate.MAXIMAL_TIMING_ERRORS_MS, estimate.FULL_SIZE, RECIPROCITY_BLOCK)
SMOKE_DESIGN = EstimateDesign(
    reporting.RunLabel.QUICK, (0.0, estimate.FULLY_RECIPROCAL), (estimate.REFERENCE_TIMING_ERROR_MS,), estimate.SweepSize(1, 2), SMOKE_BLOCK,
)


def parse_design(arguments: Sequence[str]) -> EstimateDesign:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="two values of r, one timing error, one assignment of two draws")
    return SMOKE_DESIGN if parser.parse_args(arguments).smoke else FULL_DESIGN


def run_sweeps(design: EstimateDesign, fibres: AnatomicalConnections) -> list[estimate.StaticSweep]:
    reciprocity_seed, timing_seed = design.seeds.seeds()
    reciprocity = estimate.StaticEstimator(fibres, design.size, np.random.default_rng(reciprocity_seed))
    timing = estimate.StaticEstimator(fibres, design.size, np.random.default_rng(timing_seed))
    return [reciprocity.reciprocity_sweep(design.reciprocal_shares), timing.timing_error_sweep(design.maximal_timing_errors_ms)]


def sweep_lines(sweep: dict[str, object]) -> list[str]:
    crossing = NOT_CROSSED if sweep["crossing"] is None else f"{sweep['crossing']:.3f}"
    rows = [[f"{p['parameter']:g}", f"{p['giant_share']:.3f}"] for p in sweep["points"]]
    return [
        f"### Mean giant component against the {sweep['parameter']}",
        "",
        *reporting.markdown_table([sweep["parameter"], "Mean giant-component share"], rows),
        "",
        f"First falls below q* = {cal.QUORUM_FRACTION} at {sweep['parameter']} = {crossing} (linear interpolation).",
        "",
    ]


def to_markdown(document: dict[str, object]) -> str:
    design = document["design"]
    return "\n".join([
        *reporting.run_metadata_section(document, provenance.markdown_rows(document["provenance"])),
        "Post hoc static estimates requested by referees, reported without a verdict. No oscillator dynamics; either-direction rule",
        f"(Appendix C.12); NMDA-antagonist-like agent at three times the EC50; {design['size']['assignments']} assignments of direction of",
        f"{design['size']['draws']} timing draws per value; seeds {document['seeds']}. Arc on time with probability",
        f"{document['on_time_at_reference_error']:.4f} at the reference maximal timing error of {estimate.REFERENCE_TIMING_ERROR_MS:g} ms.",
        "",
        *[line for sweep in document["sweeps"] for line in sweep_lines(sweep)],
    ])


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    started = datetime.now(timezone.utc).isoformat()
    fibres = AnatomicalConnections.of(connectomes.LOADERS[ORGANISM](cal.CONNECTOME_SEED))
    sweeps = run_sweeps(design, fibres)
    document = {
        "label": design.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance.collect(provenance.loaded_sources(), thresholds.REPORTED_PACKAGES),
        "design": asdict(design) | {"read_rule": estimate.READ_RULE.value, "anatomical_connections": fibres.count},
        "seeds": list(design.seeds.seeds()),
        "on_time_at_reference_error": estimate.on_time_probability(estimate.REFERENCE_TIMING_ERROR_MS),
        "on_time_by_timing_error": {f"{e:g}": estimate.on_time_probability(e) for e in design.maximal_timing_errors_ms},
        "sweeps": [asdict(sweep) for sweep in sweeps],
    }
    reporting.publish(REPORT_KIND, document, to_markdown(document))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
