"""Loaders and pipelines end to end on synthetic files laid out exactly like the verified datasets."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import scipy.io as sio

from analysis.open_data import loaders, pipeline_michigan, pipeline_neurotycho, pipeline_prios, run
from analysis.open_data.loaders import RunLocation
from analysis.open_data.montage import Experiment
from analysis.open_data.pipeline_prios import PriosSession
from analysis.open_data.specs import Resampling
from analysis.open_data.settings import EVOKED, FMRI, HYSTERESIS
from analysis.open_data.stats import Verdict

SUBJECT = "sub-01"


def write_michigan(root: Path, n_parcels: int, n_volumes: int, rng: np.random.Generator, all_runs: bool = False) -> None:
    """Runs 1 (awake, concentration zero) and 2 (stepped induction), and with ``all_runs`` 3 and 4 (emergence)."""
    derivatives = root / "derivatives"
    derivatives.mkdir(parents=True)
    (derivatives / "LOR_ROR_Timing.csv").write_text(f"Subject,LOR time (TR in task2),ROR time (TR in task3)\nsub-01,200,{'300' if all_runs else 'N/A'}\n")
    infusion = derivatives / "Propofol_Infusion" / SUBJECT
    func = derivatives / loaders.XCPD_PRIMARY / SUBJECT / "func"
    timing = derivatives / "Squeeze_Force" / "Instruction_Timing"
    for d in (infusion, func, timing):
        d.mkdir(parents=True)
    steps = np.repeat(np.arange(0, 2.8, 0.4), int(np.ceil(n_volumes / 7)))[:n_volumes]
    runs = [(1, np.zeros(n_volumes)), (2, steps)]
    if all_runs:
        runs += [(3, steps[::-1].copy()), (4, np.full(n_volumes, steps[0]))]
    for number, effect_site in runs:
        np.savetxt(infusion / f"{SUBJECT}_task{number}_ESC.1D", effect_site)
        np.savetxt(infusion / f"{SUBJECT}_task{number}_PLAS.1D", effect_site)
        coupling = np.clip(0.5 - 0.2 * effect_site, 0, 1)
        shared = rng.standard_normal(n_volumes)
        bold = np.sqrt(coupling) * shared + np.sqrt(1 - coupling) * rng.standard_normal((n_parcels, n_volumes))
        header = "\t".join(f"P{i}" for i in range(n_parcels))
        stem = f"{SUBJECT}_task-imagery_run-{number}"
        np.savetxt(func / f"{stem}_space-MNI152NLin2009cAsym_seg-{loaders.PARCELLATION}_stat-mean_timeseries.tsv", bold.T, delimiter="\t", header=header, comments="")
        motion = "rot_x\tframewise_displacement\n" + "\n".join(f"0\t{0.1 if t else 0.0}" for t in range(n_volumes))
        (func / f"{stem}_motion.tsv").write_text(motion + "\n")
        for c in loaders.INSTRUCTION_CONDITIONS:
            np.savetxt(timing / f"Ideal_task{number}_{c}.xmat.1D", (rng.random(n_volumes) > 0.9).astype(float), header="<matrix", comments="# ")


class MichiganTests(unittest.TestCase):
    def test_run_loads_and_windows_track_concentration(self) -> None:
        rng = np.random.default_rng(0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_michigan(root, 12, 600, rng)
            awake, run = (loaders.load_michigan_run(RunLocation(root, SUBJECT, r)) for r in (1, 2))
            self.assertEqual(run.timeseries.shape, (12, 600))
            self.assertEqual(loaders.load_lor_ror(root)[SUBJECT], {"lor_volume": 200, "ror_volume": None})
            table = pipeline_michigan.induction_table(pipeline_michigan.Subject(awake, run, ()), run.effect_site, pipeline_michigan.edge_test(rng))
        per_run = len(range(0, 600 - FMRI.window_trs + 1, FMRI.step_trs))
        self.assertEqual(table["concentration"].size, 2 * per_run)
        self.assertEqual(len(table["windows"]), 2 * per_run)
        self.assertTrue(np.all(table["concentration"][table["run"] == 1] == 0))
        self.assertLess(np.corrcoef(table["concentration"], table["mean_coupling"])[0, 1], -0.8)

    def test_a_length_mismatch_is_refused(self) -> None:
        rng = np.random.default_rng(1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_michigan(root, 6, 300, rng)
            np.savetxt(root / "derivatives" / "Propofol_Infusion" / SUBJECT / f"{SUBJECT}_task2_ESC.1D", np.zeros(299))
            with self.assertRaises(ValueError):
                loaders.load_michigan_run(RunLocation(root, SUBJECT, 2))

    def test_order_parameter_series_has_one_value_per_kept_volume(self) -> None:
        rng = np.random.default_rng(2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_michigan(root, 10, 400, rng)
            awake, run = (loaders.load_michigan_run(RunLocation(root, SUBJECT, r)) for r in (1, 2))
            series, keep = pipeline_michigan.order_parameter_series(run, awake, rng)
        self.assertTrue(np.all(np.isfinite(series[keep])))
        self.assertTrue(np.all((series[keep] > 0) & (series[keep] <= 1)))


class CommandLineTests(unittest.TestCase):
    """The whole command line on synthetic files: per-subject and per-session results, then the family verdicts."""

    def test_michigan_neurotycho_and_group_commands_run_end_to_end(self) -> None:
        rng = np.random.default_rng(8)
        xy = NeurotychoTests.xy
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_michigan(tmp / "michigan", 12, 600, rng, all_runs=True)
            sio.savemat(tmp / "map.mat", {"X": xy[:, 0], "Y": xy[:, 1]})
            out = tmp / "results"
            run.main(["michigan", "--root", str(tmp / "michigan"), "--subject", SUBJECT, "--out", str(out), "--null-realisations", "3", "--surrogates", "20"])
            for k, name in enumerate((EXPERIMENT, EXPERIMENT.replace("PF", "KT").replace("20120730", "20120719"))):
                experiment = write_neurotycho(tmp / f"nt{k}", xy, rng).rename(tmp / name)
                run.main(["neurotycho", "--experiment", str(experiment), "--map", str(tmp / "map.mat"), "--channels", ",".join(str(c) for c in range(1, 13)), "--out", str(out), "--surrogates", "20"])
            run.main(["group", "--inputs", str(out), "--out", str(out / "verdicts.json")])
            subject = json.loads((out / f"michigan_{SUBJECT}.json").read_text())
            verdicts = json.loads((out / "verdicts.json").read_text())
        self.assertEqual(set(subject["H4"]), {"provided", *(f"ke0={k}" for k in HYSTERESIS.ke0_per_minute)})
        self.assertEqual(subject["H1"]["null_a_linear_decline"]["null_size"], 3)
        self.assertEqual(set(verdicts["primary"]), {"H1", "H2a", "H2b", "H3", "H4"})
        for result in verdicts["primary"].values():
            self.assertIn(result["verdict"], {v.value for v in Verdict})
        self.assertIn("module_sha256", verdicts["provenance"])
        self.assertEqual(set(verdicts["secondary_H1"]), {"null_b", "local_amplitude", "midpoint_minus_lor_ug_per_ml"})


EXPERIMENT = "20120730PF_Anesthesia+and+Sleep_Chibi_Toru+Yanagawa_mat_ECoG128"
FS = 1000


def ecog(xy: np.ndarray, seconds: int, jitter_ms: float, rng: np.random.Generator) -> np.ndarray:
    """40 Hz activity with a fixed phase gradient across the array; each electrode's timing jitters per second."""
    t = np.arange(seconds * FS) / FS
    base = 2 * np.pi * 40 * t
    out = []
    for x, y in xy:
        jitter = np.repeat(rng.normal(0, jitter_ms / 1000, seconds), FS)
        out.append(np.cos(base - 2 * np.pi * 40 * (0.002 * x + jitter)) * (1 + 0.3 * y) + 0.2 * rng.standard_normal(t.size))
    return np.array(out)


def write_neurotycho(root: Path, xy: np.ndarray, rng: np.random.Generator) -> Path:
    experiment = root / EXPERIMENT
    awake = ecog(xy, 130, 0.5, rng)
    induction_and_deep = np.concatenate([ecog(xy, 100, 1.0, rng), ecog(xy, 130, 6.0, rng)], axis=1)
    sessions = {
        "Session1": (awake, ["AwakeEyesClosed-Start", "AwakeEyesClosed-End"], [5000, 125000]),
        "Session2": (induction_and_deep, ["AnestheticInjection", "Anesthetized-Start", "Anesthetized-End"], [5000, 100000, 225000]),
    }
    for name, (data, labels, indices) in sessions.items():
        folder = experiment / name
        folder.mkdir(parents=True)
        sio.savemat(folder / "Condition.mat", {"ConditionLabel": np.array(labels, dtype=object), "ConditionIndex": np.array(indices, float), "ConditionTime": np.array(indices, float) / FS})
        for ch, row in enumerate(data, start=1):
            sio.savemat(folder / f"ECoG_ch{ch}.mat", {f"ECoGData_ch{ch}": np.round(row * 100).astype(np.int16)})
    return experiment


class NeurotychoTests(unittest.TestCase):
    xy = np.array([[x, y] for y in range(2) for x in range(6)], float) * 10

    def test_markers_and_agent_are_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            experiment = write_neurotycho(Path(tmp), self.xy, np.random.default_rng(3))
            markers = loaders.load_markers(experiment)
            self.assertEqual(loaders.parse_session_name(experiment)["agent"], "propofol")
            self.assertEqual(loaders.epoch(markers, ("Anesthetized-Start", "Anesthetized-End")), ("Session2", 100000, 225000))

    def test_jittered_timing_raises_lag_variability_in_the_anaesthetised_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            experiment = write_neurotycho(Path(tmp), self.xy, np.random.default_rng(4))
            rows = pipeline_neurotycho.session_blocks(Experiment(experiment, list(range(1, 13)), self.xy))
        awake = [r["lag_variability_ms_z"] for r in rows if r["state"] == "awake"]
        deep = [r["lag_variability_ms_z"] for r in rows if r["state"] == "anaesthetised"]
        self.assertEqual(len(awake), 4)
        self.assertGreater(min(deep), max(awake))

    def test_induction_order_parameter_and_its_indicators_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            experiment = write_neurotycho(Path(tmp), self.xy, np.random.default_rng(5))
            result = pipeline_neurotycho.critical_slowing(Experiment(experiment, list(range(1, 13)), self.xy), Resampling(20, np.random.default_rng(6)))
        self.assertEqual(result["points"], (100000 - 5000) // (2 * FS))
        self.assertIn("tau", result["variance"])


def write_brainvision(folder: Path, stem: str, jitter_ms: float, rng: np.random.Generator) -> None:
    fs, n_stim, spacing = 2048, 12, 4096
    names = ["A1", "A2", "R1"]
    data = 0.5 * rng.standard_normal((spacing * (n_stim + 2), len(names))).astype(np.float32)
    rows = ["onset\tduration\ttrial_type\tsub_type\telectrodes_involved_onset\telectrodes_involved_offset\toffset\tsample_start\tsample_end\telectrical_stimulation_type\telectrical_stimulation_site\telectrical_stimulation_current\telectrical_stimulation_frequency\telectrical_stimulation_pulsewidth\tnotes"]
    t_ms = np.arange(int(0.15 * fs)) / fs * 1000
    for k in range(n_stim):
        onset = spacing * (k + 1)
        latency = 30.0 + rng.normal(0, jitter_ms)
        data[onset : onset + t_ms.size, 2] += (-20 * np.exp(-0.5 * ((t_ms - latency) / 5.0) ** 2)).astype(np.float32)
        site = "A1-A2" if k % 2 else "A2-A1"
        rows.append(f"{onset / fs}\t0\telectrical_stimulation\tSPES\tn/a\tn/a\tn/a\t{onset}\t{onset}\tmonophasic\t{site}\t0.008\t0.2\t0.001\tn/a")
    (folder / f"{stem}_events.tsv").write_text("\n".join(rows) + "\n")
    data.tofile(folder / f"{stem}_ieeg.eeg")
    channel_lines = "\n".join(f"Ch{i + 1}={n},,1" for i, n in enumerate(names))
    (folder / f"{stem}_ieeg.vhdr").write_text(
        f"Brain Vision Data Exchange Header File Version 1.0\n[Common Infos]\nDataFile={stem}_ieeg.eeg\nDataFormat=BINARY\n"
        f"DataOrientation=MULTIPLEXED\nNumberOfChannels={len(names)}\nSamplingInterval={1e6 / fs}\n[Binary Infos]\n"
        f"BinaryFormat=IEEE_FLOAT_32\n[Channel Infos]\n{channel_lines}\n"
    )
    (folder / f"{stem}_channels.tsv").write_text("name\ttype\tstatus\n" + "\n".join(f"{n}\tECOG\tgood" for n in names) + "\n")


class PriosTests(unittest.TestCase):
    def test_variability_rising_without_a_change_in_mean_latency_is_positive(self) -> None:
        rng = np.random.default_rng(7)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            write_brainvision(folder, "sub-X_task-SPESclin", 1.0, rng)
            write_brainvision(folder, "sub-X_task-SPESprop", 4.0, rng)
            (folder / "electrodes.tsv").write_text("name\tx\ty\tz\nA1\t0\t0\t0\nA2\t0\t10\t0\nR1\t40\t0\t0\n")
            recording = loaders.load_brainvision(folder / "sub-X_task-SPESclin_ieeg.vhdr")
            self.assertEqual(recording.channels, ["A1", "A2", "R1"])
            self.assertAlmostEqual(recording.sampling_hz, 2048.0)
            result = pipeline_prios.subject_changes(PriosSession(folder, "sub-X_task-SPESclin", "sub-X_task-SPESprop", folder / "electrodes.tsv"), rng)
        self.assertEqual(len(result["connections"]), 1)
        connection = result["connections"][0]
        self.assertEqual(connection["site"], "A1-A2")
        self.assertGreater(connection["relative_change"], 0.5)
        self.assertAlmostEqual(connection["awake"]["mean_latency_ms"], 30.0, delta=2.0)

    def test_command_line_finds_both_runs_and_the_electrodes(self) -> None:
        rng = np.random.default_rng(9)
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp) / "sub-PRIOSX" / "ses-1"
            ieeg = session / "ieeg"
            ieeg.mkdir(parents=True)
            write_brainvision(ieeg, "sub-PRIOSX_ses-1_task-SPESclin_run-021358", 1.0, rng)
            write_brainvision(ieeg, "sub-PRIOSX_ses-1_task-SPESprop_run-080807", 4.0, rng)
            (ieeg / "sub-PRIOSX_ses-1_electrodes.tsv").write_text("name\tx\ty\tz\nA1\t0\t0\t0\nA2\t0\t10\t0\nR1\t40\t0\t0\n")
            run.main(["prios", "--session-dir", str(session), "--out", str(Path(tmp) / "out")])
            result = json.loads((Path(tmp) / "out" / "prios_sub-PRIOSX.json").read_text())
        self.assertEqual(result["runs"]["SPESprop"], "sub-PRIOSX_ses-1_task-SPESprop_run-080807")
        self.assertEqual(len(result["H5a"]["connections"]), 1)

    def test_pulses_with_a_deviation_note_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.tsv"
            path.write_text(
                "trial_type\tsample_start\telectrical_stimulation_site\telectrical_stimulation_current\tnotes\n"
                "electrical_stimulation\t10\tA1-A2\t0.008\tn/a\n"
                "electrical_stimulation\t20\tA1-A2\t0.008\tCurrent is lower than requested\n"
                "artefact\t30\tn/a\tn/a\tn/a\n"
            )
            self.assertEqual([e["sample"] for e in loaders.load_stimulation_events(path)], [10])

    def test_minimum_distance_excludes_the_stimulated_and_nearby_electrodes(self) -> None:
        positions = {"A1": np.zeros(3), "A2": np.array([0, 10.0, 0]), "N": np.array([5.0, 5, 0]), "F": np.array([60.0, 0, 0])}
        self.assertFalse(pipeline_prios.far_enough("A1", "A1-A2", positions))
        self.assertFalse(pipeline_prios.far_enough("N", "A1-A2", positions))
        self.assertTrue(pipeline_prios.far_enough("F", "A1-A2", positions))
        self.assertGreaterEqual(EVOKED.min_distance_mm, 10.0)


if __name__ == "__main__":
    unittest.main()
