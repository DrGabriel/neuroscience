"""Round 3, monkey-level bootstrap of H2b and H3: the resampling structure and the commands, on synthetic results."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from analysis.open_data import group, monkey_bootstrap
from analysis.open_data.monkey_bootstrap import Nesting
from analysis.open_data.specs import Resampling

DRAWS = 4000
FREQUENCY_TOLERANCE = 0.03
QUARTER, HALF = 0.25, 0.5
SEED = 3
RESAMPLES = "60"
AGENTS = {"propofol": ("Chibi", "George"), "ketamine": ("Chibi", "George"), "ketamine-medetomidine": ("Chibi", "George", "Kin2", "Su")}
SESSIONS_PER_MONKEY_AND_AGENT = 2
BLOCKS_PER_STATE = 6
TAU, TAU_SPREAD = 0.3, 0.1
ROUNDING = 6
STRUCTURE_DRAWS = DRAWS // 10
ORDER_OUTER, ORDER_INNER = np.array(list("AABBCC")), np.array(["a1", "a2", "b1", "b2", "c1", "c2"])
SHUFFLE = np.array([5, 2, 0, 4, 1, 3])


def bootstrap(values: np.ndarray, nesting: Nesting, draws: int = DRAWS) -> np.ndarray:
    layout = monkey_bootstrap.nested_layout(nesting)
    return monkey_bootstrap.two_stage_bootstrap(lambda rows: float(np.mean(values[rows])), layout, Resampling(draws, np.random.default_rng(SEED)))


def shares(draws: np.ndarray) -> dict[float, float]:
    return {value: count / draws.size for value, count in Counter(np.round(draws, ROUNDING)).items()}


class ResamplingStructureTests(unittest.TestCase):
    def test_monkeys_are_drawn_whole_so_only_monkey_level_means_occur(self) -> None:
        outer = np.array(["A", "A", "B", "B"])
        nesting = Nesting(np.full(outer.size, "x"), outer, np.array(["a1", "a2", "b1", "b2"]))
        observed = shares(bootstrap(np.array([1.0, 1.0, 0.0, 0.0]), nesting))
        self.assertEqual(set(observed), {0.0, HALF, 1.0})
        for value, expected in ((0.0, QUARTER), (HALF, HALF), (1.0, QUARTER)):
            self.assertAlmostEqual(observed[value], expected, delta=FREQUENCY_TOLERANCE)

    def test_sessions_are_resampled_within_a_drawn_monkey(self) -> None:
        nesting = Nesting(np.full(2, "x"), np.array(["A", "A"]), np.array(["a1", "a2"]))
        observed = shares(bootstrap(np.array([0.0, 1.0]), nesting))
        self.assertAlmostEqual(observed[HALF], HALF, delta=FREQUENCY_TOLERANCE)

    def test_every_stratum_is_in_every_resample_and_sessions_stay_whole(self) -> None:
        strata = np.array(["p", "p", "p", "k", "k"])
        nesting = Nesting(strata, np.array(["A", "A", "B", "B", "B"]), np.array(["s1", "s1", "s2", "s3", "s3"]))
        layout = monkey_bootstrap.nested_layout(nesting)
        rng = np.random.default_rng(SEED)
        for _ in range(STRUCTURE_DRAWS):
            rows = monkey_bootstrap.two_stage_rows(layout, rng)
            self.assertEqual(set(strata[rows]), {"p", "k"})
            counts = Counter(nesting.inner[rows])
            self.assertTrue(all(counts[s] % 2 == 0 for s in ("s1", "s3")))

    def test_the_order_of_the_rows_does_not_change_the_draws(self) -> None:
        values = np.arange(float(ORDER_OUTER.size))
        nesting = Nesting(np.full(ORDER_OUTER.size, "x"), ORDER_OUTER, ORDER_INNER)
        shuffled = Nesting(nesting.strata[SHUFFLE], nesting.outer[SHUFFLE], nesting.inner[SHUFFLE])
        np.testing.assert_array_equal(bootstrap(values, nesting, STRUCTURE_DRAWS), bootstrap(values[SHUFFLE], shuffled, STRUCTURE_DRAWS))


@dataclass(frozen=True)
class SessionSpec:
    agent: str
    monkey: str
    index: int


def a_session(spec: SessionSpec, rng: np.random.Generator) -> dict:
    agent, monkey = spec.agent, spec.monkey
    name = f"{spec.index:02d}{agent}_{monkey}"
    blocks = []
    for state, shift in (("awake", 0.0), ("anaesthetised", 1.0)):
        for _ in range(BLOCKS_PER_STATE):
            blocks.append({
                "agent": agent, "monkey": monkey, "session_id": name, "state": state,
                "lag_variability_ms_z": 2 * shift + rng.normal(0, HALF),
                "mean_lag_ms_z": rng.normal(0, HALF),
                "log_power_z": (shift if agent == "ketamine" else -shift) + rng.normal(0, HALF),
            })
    h2b = {"variance": {"tau": TAU + abs(rng.normal(0, TAU_SPREAD))}, "autocorrelation": {"tau": TAU}}
    return {"experiment": name, "monkey": monkey, "agent": agent, "H2b": h2b, "H3_blocks": blocks}


def synthetic_sessions(rng: np.random.Generator) -> list[dict]:
    sessions = [a_session(SessionSpec(a, m, k), rng) for a, monkeys in AGENTS.items() for m in monkeys for k in range(SESSIONS_PER_MONKEY_AND_AGENT)]
    sleep = {**a_session(SessionSpec("propofol", "Chibi", len(sessions)), rng), "agent": "sleep"}
    excluded = {**a_session(SessionSpec("propofol", "George", len(sessions) + 1), rng), "H2b": {"excluded": "too short"}}
    return [*sessions, sleep, excluded]


class TargetTests(unittest.TestCase):
    def test_point_estimates_are_the_committed_statistics(self) -> None:
        sessions = [s for s in synthetic_sessions(np.random.default_rng(SEED)) if "excluded" not in s["H2b"] and s["agent"] != "sleep"]
        blocks = [b for s in sessions for b in s["H3_blocks"]]
        everything = np.arange(len(sessions))
        self.assertEqual(monkey_bootstrap.h2b_target(sessions).statistic(everything), group.h2_critical_slowing([s["H2b"] for s in sessions])["effect"])
        h3 = monkey_bootstrap.h3_target(blocks)
        self.assertAlmostEqual(h3.statistic(np.arange(len(blocks))), group.h3_lag_variability(blocks, n_resamples=2)["effect"])


class CommandTests(unittest.TestCase):
    def test_folder_and_list_give_the_same_session_and_monkey_level_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "results"
            folder.mkdir()
            for session in synthetic_sessions(np.random.default_rng(SEED)):
                (folder / f"neurotycho_{session['experiment']}.json").write_text(json.dumps(session))
            listing = Path(tmp) / "inputs.txt"
            listing.write_text("\n".join(str(p) for p in sorted(folder.glob("*.json"))))
            for source, name in ((folder, "from_folder.json"), (listing, "from_list.json")):
                monkey_bootstrap.main(["--inputs", str(source), "--out", str(Path(tmp) / name), "--resamples", RESAMPLES])
            results = [json.loads((Path(tmp) / n).read_text()) for n in ("from_folder.json", "from_list.json")]
        self.assertEqual(results[0]["H3"], results[1]["H3"])
        h2b, h3 = results[0]["H2b"], results[0]["H3"]
        self.assertEqual(results[0]["inference_unit"], "monkey")
        self.assertEqual(h2b["monkey_level"]["confidence_interval"], [TAU, TAU])
        self.assertEqual(h2b["monkey_level"]["sessions"], h2b["session_level"]["n"])
        self.assertEqual(h3["monkey_level"]["monkeys_per_stratum"], {a: len(m) for a, m in AGENTS.items()})
        self.assertEqual(h3["monkey_level"]["effect"], h3["session_level"]["effect"])
        self.assertEqual(h3["monkey_level"]["resamples"], int(RESAMPLES))


if __name__ == "__main__":
    unittest.main()
