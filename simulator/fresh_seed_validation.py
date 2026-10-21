"""The validation study of Appendix B.4 on seeds disjoint from calibration and from B.4 (Appendix C.14, analysis D).

The feedback was calibrated (calibrate_feedback.py) on the base seed plus 0 to 9 at 10,000 nodes, and B.4 used the base
seed plus 0 to 19 at every size with the same graph builder, so ten of B.4's seeds at 10,000 nodes were the
calibration networks themselves. This command reruns B.4's claims, observations and extension tests, with the same
code, sizes, seed count and pass rule (a claim holds only when it holds in every seed), on the base seed plus 7600 to
7619, and reports the loss-to-recovery concentration ratio at every size.

Usage:
    ../.venv/bin/python fresh_seed_validation.py            # full study: five network sizes, 20 seeds each
    ../.venv/bin/python fresh_seed_validation.py --smoke    # 302 nodes, one seed outside every block: seconds

Smoke reports are labelled quick, are ignored by git and are not results. Exit status is non-zero if any claim fails
for any seed at any size, as for B.4.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import asdict
from typing import Sequence

import provenance
import reporting
import validation_study as validation
from round3_study.fresh_validation import inertia_ratio, ratio_markdown, ratio_statistics
from round3_study.seeds import FRESH_VALIDATION_BLOCK, SMOKE_BLOCK

REPORT_KIND = "validation_fresh_seeds"
SMOKE_NODE_COUNTS = (validation.QUICK_NODE_COUNTS[0],)
SMOKE_SEEDS = 1
FIRST_SEED = FRESH_VALIDATION_BLOCK.seeds().start
FULL_DESIGN = validation.StudyDesign(reporting.RunLabel.FULL, validation.FULL_NODE_COUNTS, FRESH_VALIDATION_BLOCK.count, FIRST_SEED)
SMOKE_DESIGN = validation.StudyDesign(reporting.RunLabel.QUICK, SMOKE_NODE_COUNTS, SMOKE_SEEDS, SMOKE_BLOCK.seeds().start)


def parse_design(arguments: Sequence[str]) -> validation.StudyDesign:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="302 nodes, one seed")
    return SMOKE_DESIGN if parser.parse_args(arguments).smoke else FULL_DESIGN


def ratio_record(report: validation.StudyReport, node_counts: Sequence[int]) -> dict[str, object]:
    return {
        "inertia_ratio_by_seed": [[m.node_count, m.seed, inertia_ratio(m)] for m in report.measurements],
        "inertia_ratio_statistics": {str(n): asdict(distribution) for n, distribution in ratio_statistics(report.measurements, node_counts).items()},
    }


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    report = validation.run_study(design, os.cpu_count() or 1)
    markdown = "\n".join([validation.to_markdown(report), *ratio_markdown(report.measurements, design.node_counts)])
    document = validation.to_document(report) | {"label": design.label} | ratio_record(report, design.node_counts)
    reporting.publish(REPORT_KIND, document, markdown)
    return 0 if report.all_claims_hold else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
