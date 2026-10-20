"""Pre-specified robustness study: the phase-model results re-tested with a readout that implements P2 and P3.

Every earlier phase-model test judged quorum by global coherence at least half its awake value, which uses neither
the integration window of P2 nor the connected component of P3. This study reads the same simulations with
dpc_readout, in which a connection counts in a cycle only if it transmits and its signal arrives within W/2 of the
shared rhythm, and quorum holds when the counting connections link at least q* of the populations. On fresh seeds it
re-tests the agent results (T2a and T2b, with a rewired null model), asks where the readout departs from static
percolation and whether loss is a synchronisation or a percolation transition, adds a reference carried by the
connections themselves and a weaker coupling that leaves the awake network below full synchrony, re-tests the
fluctuation claim (T1b and T1c) at matched coherence, sensory disconnection (K1c) with the missing control, and
neural inertia in both models, each calibration on seeds disjoint from those that test it. The tests, conditions,
seeds and pass rule (readout_study.pass_rule) are written into the paper (Appendix C.12) before the full study runs.
The code is in the readout_study package; this file is its command.

Usage:
    ../.venv/bin/python dpc_readout_study.py            # full study
    ../.venv/bin/python dpc_readout_study.py --quick    # one seed per organism and condition, shortened integration
    ../.venv/bin/python dpc_readout_study.py --smoke    # C. elegans only, one seed, two concentrations: a few minutes

Smoke and quick reports are labelled quick, are ignored by git and are not results. Exit status is non-zero unless
every test passes for every organism on which it is evaluated. A failing test is a scientific result, not a software
error: the report is written either way.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

import provenance
import reporting
from readout_study.plans import StudyMode, run_all
from readout_study.report import assemble_report, every_evaluated_test_passes, to_markdown

REPORT_KIND = "dpc_readout"


def parse_mode(arguments: Sequence[str]) -> StudyMode:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    shortened = parser.add_mutually_exclusive_group()
    shortened.add_argument("--quick", action="store_true", help="one seed per organism and condition, shortened integration")
    shortened.add_argument("--smoke", action="store_true", help="C. elegans only, one seed, shortest integration, two concentrations")
    options = parser.parse_args(arguments)
    if options.smoke:
        return StudyMode.SMOKE
    return StudyMode.QUICK if options.quick else StudyMode.FULL


def main(arguments: Sequence[str]) -> int:
    provenance.record_launch()
    report = assemble_report(run_all(parse_mode(arguments)))
    reporting.publish(REPORT_KIND, report, to_markdown(report))
    return 0 if every_evaluated_test_passes(report) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
