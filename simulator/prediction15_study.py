"""Pre-specified test of prediction 15 in the percolation model (Appendix C.14, analysis A).

At the calibrated reference feedback, each seed's bistable window [c_on, c_off] is found as in Appendix B.4. From the
unconscious state that induction leaves, the arousal drive is raised for a fixed number of steps of the model's
self-consistency map and then returned to baseline, at the midpoint of the window (P15a: quorum should persist) and at
c_off + 0.1 EC50 (P15b: quorum should be lost again). The tests, conditions, seeds and pass rule are fixed in
analysis/2026-10-21_round3_simulator_prespecification.md before the study runs. The code is in round3_study.

Usage:
    ../.venv/bin/python prediction15_study.py            # full study: five network sizes, 20 seeds each
    ../.venv/bin/python prediction15_study.py --smoke    # 302 nodes, one seed outside every block: seconds

Smoke reports are labelled quick, are ignored by git and are not results. Exit status is non-zero unless both tests
pass at every network size; a failing test is a scientific result, and the report is written either way.
Standard library only.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Sequence

import provenance
import reporting
import validation_study as validation
from round3_study.pulse_checks import measure_seed
from round3_study.pulse_report import PulseStudy, assemble_report, every_test_passes, to_markdown
from round3_study.seeds import PULSE_BLOCK, SMOKE_BLOCK

REPORT_KIND = "prediction15"
SMOKE_NODE_COUNTS = (validation.QUICK_NODE_COUNTS[0],)
SMOKE_SEEDS = 1
FULL_DESIGN = validation.StudyDesign(reporting.RunLabel.FULL, validation.FULL_NODE_COUNTS, PULSE_BLOCK.count, PULSE_BLOCK.seeds().start)
SMOKE_DESIGN = validation.StudyDesign(reporting.RunLabel.QUICK, SMOKE_NODE_COUNTS, SMOKE_SEEDS, SMOKE_BLOCK.seeds().start)


def parse_design(arguments: Sequence[str]) -> validation.StudyDesign:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="302 nodes, one seed")
    return SMOKE_DESIGN if parser.parse_args(arguments).smoke else FULL_DESIGN


def run_study(design: validation.StudyDesign, worker_count: int) -> PulseStudy:
    started = datetime.now(timezone.utc).isoformat()
    measurements = reporting.run_in_parallel(measure_seed, design.tasks(), reporting.ParallelRun(REPORT_KIND, worker_count))
    return PulseStudy(design, started, datetime.now(timezone.utc).isoformat(), worker_count, measurements)


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    design = parse_design(arguments)
    report = assemble_report(run_study(design, os.cpu_count() or 1))
    reporting.publish(REPORT_KIND, report, to_markdown(report))
    return 0 if every_test_passes(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
