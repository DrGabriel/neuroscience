"""Pre-specified pair-rule study (Appendix C.13): does the human result of C.12 depend on when a connection counts?

The DPC readout of Appendix C.12 took every directed arc as its own connection, so two populations linked both ways had
two chances in each cycle to be joined, and every fibre of the human connectome, which diffusion MRI records without
direction, is stored as two arcs. This study reads the agent conditions again, on fresh seeds, with one timing draw
per anatomical connection as the primary rule (connection_pairs), and reports the both-directions and
either-direction rules beside it. The tests, conditions, seeds and pass rule are written into the paper (Appendix
C.13) before the study runs. The code is in the pair_rule_study package; this file is its command.

Usage:
    ../.venv/bin/python dpc_pair_rule_study.py            # full study
    ../.venv/bin/python dpc_pair_rule_study.py --smoke    # C. elegans only, one seed, two concentrations: seconds

Smoke reports are labelled quick, are ignored by git and are not results. Exit status is non-zero unless every test
passes for every organism. A failing test is a scientific result, not a software error: the report is written either
way.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

import provenance
import reporting
from pair_rule_study.plan import run_study
from pair_rule_study.report import assemble_report, every_evaluated_test_passes, to_markdown
from readout_study.plans import StudyMode

REPORT_KIND = "dpc_pair_rule"


def parse_mode(arguments: Sequence[str]) -> StudyMode:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="C. elegans only, one seed, shortest integration, two concentrations")
    return StudyMode.SMOKE if parser.parse_args(arguments).smoke else StudyMode.FULL


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    report = assemble_report(run_study(parse_mode(arguments)))
    reporting.publish(REPORT_KIND, report, to_markdown(report))
    return 0 if every_evaluated_test_passes(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
