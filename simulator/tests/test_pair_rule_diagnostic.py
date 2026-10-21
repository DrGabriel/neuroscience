"""The static pair-rule diagnostic of Appendix C.13, on values whose answer is known."""

from __future__ import annotations

import unittest

import numpy as np

import calibration as cal
import pair_rule_diagnostic as diagnostic
from connection_pairs import AnatomicalConnections, PairRule
from tests.test_connection_pairs import two_way_ring, wired

POPULATIONS = 3
# The figures C.13 quotes for the static draw at three times the EC50.
QUOTED_SIGMA_MS, SIGMA_PLACES = 39.6, 1
QUOTED_ON_TIME, ON_TIME_PLACES = 0.024, 3
EVERY_ARC = 1.0


class StaticDrawTests(unittest.TestCase):
    def test_the_on_time_probability_at_three_times_the_ec50_is_the_one_quoted_in_c13(self) -> None:
        draw = diagnostic.StaticDraw(cal.NMDA_ANTAGONIST_AGENT, diagnostic.CONCENTRATION_OVER_EC50)
        self.assertAlmostEqual(draw.sigma_ms(), QUOTED_SIGMA_MS, places=SIGMA_PLACES)
        self.assertAlmostEqual(draw.on_time_probability(), QUOTED_ON_TIME, places=ON_TIME_PLACES)

    def test_every_arc_on_time_joins_every_population_under_every_rule(self) -> None:
        shares = diagnostic.mean_giant_shares(AnatomicalConnections.of(wired(two_way_ring(POPULATIONS))), EVERY_ARC, np.random.default_rng(0))
        self.assertEqual(shares, {rule: EVERY_ARC for rule in PairRule})


if __name__ == "__main__":
    unittest.main()
