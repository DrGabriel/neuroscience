"""The one pass rule of the DPC readout study.

A test passes for an organism when the lower bound of the Wilson 95% interval for the share of seeds in which it holds
lies above one half. Unlike a fixed share of 80%, it is a statement about the model's realisations ("most of them,
with 95% confidence") and it is stricter where seeds are few: 15 of 20, 9 of 10 and 6 of 6 seeds pass, while 14 of
20, 8 of 10 and 5 of 6 do not.
"""

from __future__ import annotations

import reporting

RELIABLE_SHARE = 0.5
PASSES, FAILS = "passes", "fails"
PASS_RULE = f"the Wilson 95% lower bound of the share of seeds in which the test holds lies above {RELIABLE_SHARE}"


def holds_reliably(outcome: reporting.CheckOutcome) -> bool:
    if outcome.runs_applicable == 0:
        return False
    low, _ = reporting.wilson_interval(outcome.runs_holding, outcome.runs_applicable)
    return low > RELIABLE_SHARE


def reliable_or_not(outcome: reporting.CheckOutcome) -> str:
    return PASSES if holds_reliably(outcome) else FAILS
