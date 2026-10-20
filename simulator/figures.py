"""Figures for the paper, drawn from the latest full result files (and, for Figure 1, the model).

Usage: ../.venv/bin/python figures.py
Writes PNG and SVG files to ../figures/. Dependencies: matplotlib, numpy.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Callable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import calibration as cal
import comparisons
import dpc_simulator as dpc
import plant_tissue
import reporting
from species_study import ConditionName

FIGURES_DIRECTORY = Path(__file__).resolve().parent.parent / "figures"

# Validated categorical palette, first three slots, light mode (see NOTICE.md for provenance).
SERIES = ("#2a78d6", "#eb6834", "#1baf7a")
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
LINE_WIDTH = 2.0
BAND_OPACITY = 0.18
RESOLUTION_DPI = 200
PANEL_SIZE_INCHES = (4.2, 3.0)

FIGURE_ONE_NODE_COUNT = 10_000
COMPENSATION_LABELS = {"none": "no compensation", "slow": "slow compensation", "fast": "fast compensation"}
FIGURE_ONE_STEP = 0.01


def latest(kind: str) -> dict[str, object]:
    paths = sorted(reporting.RESULTS_DIRECTORY.glob(f"{kind}_full_*.json"))
    if not paths:
        raise FileNotFoundError(f"No full {kind} report in {reporting.RESULTS_DIRECTORY}")
    return json.loads(paths[-1].read_text())


def style(axis: plt.Axes, title: str, x_label: str, y_label: str) -> None:
    axis.set_facecolor(SURFACE)
    axis.set_title(title, loc="left", fontsize=10, color=TEXT_PRIMARY)
    axis.set_xlabel(x_label, fontsize=9, color=TEXT_SECONDARY)
    axis.set_ylabel(y_label, fontsize=9, color=TEXT_SECONDARY)
    axis.grid(color=GRID, linewidth=0.8)
    axis.tick_params(colors=TEXT_SECONDARY, labelsize=8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(GRID)


def label_end(axis: plt.Axes, x: Sequence[float], y: Sequence[float], text: str, colour: str) -> None:
    axis.annotate(text, (x[-1], y[-1]), xytext=(4, 0), textcoords="offset points", fontsize=8, color=TEXT_PRIMARY, va="center")
    axis.plot([x[-1]], [y[-1]], marker="o", markersize=4, color=colour)


def save(figure: plt.Figure, name: str) -> None:
    FIGURES_DIRECTORY.mkdir(exist_ok=True)
    figure.patch.set_facecolor(SURFACE)
    figure.tight_layout()
    for suffix in ("png", "svg"):
        figure.savefig(FIGURES_DIRECTORY / f"{name}.{suffix}", dpi=RESOLUTION_DPI, facecolor=SURFACE)
    plt.close(figure)


def mean_and_spread(rows: Sequence[Sequence[float | None]]) -> tuple[np.ndarray, np.ndarray]:
    values = np.array([[np.nan if v is None else v for v in row] for row in rows], dtype=float)
    return np.nanmean(values, axis=0), np.nanstd(values, axis=0, ddof=1 if values.shape[0] > 1 else 0)


def figure_percolation_hysteresis() -> None:
    """Figure 1: coherent fraction during induction and emergence, without and with reference feedback."""
    base = replace(
        dpc.REFERENCE_SCENARIO,
        graph_builder=dpc.REFERENCE_SCENARIO.graph_builder.resized(FIGURE_ONE_NODE_COUNT),
        grid=dpc.ConcentrationGrid(dpc.REFERENCE_MAX_RELATIVE_CONCENTRATION, FIGURE_ONE_STEP),
    )
    panels = (("No reference feedback (λ = 0)", 0.0), (f"Calibrated feedback (λ = {dpc.REFERENCE_FEEDBACK_JITTER_MS:g} ms)", dpc.REFERENCE_FEEDBACK_JITTER_MS))
    figure, axes = plt.subplots(1, 2, figsize=(2 * PANEL_SIZE_INCHES[0], PANEL_SIZE_INCHES[1]), sharey=True)
    for axis, (title, feedback) in zip(axes, panels):
        result = dpc.run_scenario(replace(base, timing=replace(base.timing, feedback_jitter_ms=feedback)))
        for points, name, colour in ((result.induction, "induction", SERIES[0]), (tuple(reversed(result.emergence)), "emergence", SERIES[1])):
            x = [p.concentration for p in points]
            y = [p.coherent_fraction for p in points]
            axis.plot(x, y, color=colour, linewidth=LINE_WIDTH, label=name)
        axis.axhline(dpc.REFERENCE_QUORUM_FRACTION, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
        axis.annotate("quorum", (0.05, dpc.REFERENCE_QUORUM_FRACTION), xytext=(0, 3), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
        if result.hysteresis_width is not None and comparisons.equals(result.hysteresis_width, 0):
            axis.annotate("curves coincide: no hysteresis", (1.6, 0.2), fontsize=8, color=TEXT_SECONDARY)
        style(axis, title, "Concentration (× EC50)", "Coherent fraction S")
        axis.legend(frameon=False, fontsize=8, loc="upper right")
    save(figure, "figure_1_percolation_hysteresis")


def figure_finite_size(report: dict[str, object]) -> None:
    """Figure 2: loss and recovery concentrations against network size."""
    statistics = report["statistics"]
    sizes = [int(n) for n in report["provenance"]["design"]["node_counts"]]
    figure, axis = plt.subplots(figsize=PANEL_SIZE_INCHES)
    for label, quantity, colour in (("loss (c_off)", "c_off, GABAergic-like", SERIES[0]), ("recovery (c_on)", "c_on, GABAergic-like", SERIES[1])):
        means = [statistics[quantity][str(n)]["mean"] for n in sizes]
        spreads = [statistics[quantity][str(n)]["standard_deviation"] for n in sizes]
        axis.errorbar(sizes, means, yerr=spreads, color=colour, linewidth=LINE_WIDTH, marker="o", markersize=4, capsize=3)
        label_end(axis, sizes, means, label, colour)
    axis.set_xscale("log")
    style(axis, "Loss and recovery concentrations by network size", "Network size N (nodes)", "Concentration (× EC50)")
    save(figure, "figure_2_finite_size")


def figure_species_coherence(report: dict[str, object]) -> None:
    """Figure 3: global coherence during induction and emergence, one panel per organism."""
    organisms = [o for o in cal.ORGANISMS if any(r["organism"] == o for r in report["runs"])]
    figure, axes = plt.subplots(1, len(organisms), figsize=(len(organisms) * PANEL_SIZE_INCHES[0], PANEL_SIZE_INCHES[1]), sharey=True)
    for axis, organism in zip(np.atleast_1d(axes), organisms):
        runs = [r for r in report["runs"] if r["organism"] == organism and r["condition"] == ConditionName.GABAERGIC]
        x = runs[0]["concentrations"]
        for field, name, colour in (("induction_coherence", "induction", SERIES[0]), ("emergence_coherence", "emergence", SERIES[1])):
            relative = [[value / run["induction_coherence"][0] for value in run[field]] for run in runs]
            mean, spread = mean_and_spread(relative)
            axis.plot(x, mean, color=colour, linewidth=LINE_WIDTH, label=name)
            axis.fill_between(x, mean - spread, mean + spread, color=colour, alpha=BAND_OPACITY, linewidth=0)
        axis.axhline(cal.QUORUM_FRACTION, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
        axis.annotate("quorum", (x[0], cal.QUORUM_FRACTION), xytext=(0, 3), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
        style(axis, f"{cal.ORGANISMS[organism].display_name} (n = {len(runs)})", "Concentration (× EC50)", "Global coherence / awake")
        axis.legend(frameon=False, fontsize=8, loc="upper right")
    save(figure, "figure_3_species_coherence")


def figure_broadcast(report: dict[str, object]) -> None:
    """Figure 4: how far a sensory stimulus propagates, one panel per organism."""
    organisms = [o for o in cal.ORGANISMS if any(r["organism"] == o for r in report["runs"])]
    figure, axes = plt.subplots(1, len(organisms), figsize=(len(organisms) * PANEL_SIZE_INCHES[0], PANEL_SIZE_INCHES[1]), sharey=True)
    for axis, organism in zip(np.atleast_1d(axes), organisms):
        runs = [r for r in report["runs"] if r["organism"] == organism and r["condition"] == ConditionName.SENSORY_STIMULUS]
        x = runs[0]["concentrations"]
        mean, spread = mean_and_spread([r["induction_broadcast_ratio"] for r in runs])
        axis.plot(x, mean, color=SERIES[0], linewidth=LINE_WIDTH)
        axis.fill_between(x, mean - spread, mean + spread, color=SERIES[0], alpha=BAND_OPACITY, linewidth=0)
        losses = [r["loss_concentration"] for r in runs if r["loss_concentration"] is not None]
        if losses:
            axis.axvline(float(np.mean(losses)), color=TEXT_SECONDARY, linewidth=1, linestyle="--")
            axis.annotate("loss of quorum", (float(np.mean(losses)), 0.95), xytext=(4, 0), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
        style(axis, f"{cal.ORGANISMS[organism].display_name}: stimulus broadcast", "Concentration (× EC50)", "Rest-of-network / sensory entrainment")
    save(figure, "figure_4_broadcast")


def figure_plant(report: dict[str, object]) -> None:
    """Figure 5: open-junction fraction at which action-potential propagation fails."""
    conductances = list(cal.PLANT_JUNCTION_CONDUCTANCES)
    rows = [[p["block_open_fraction"] for p in report["plant_runs"] if p["junction_conductance"] == g] for g in conductances]
    means = [float(np.mean(r)) for r in rows]
    spreads = [float(np.std(r, ddof=1)) if len(r) > 1 else 0.0 for r in rows]
    figure, axis = plt.subplots(figsize=PANEL_SIZE_INCHES)
    axis.errorbar(conductances, means, yerr=spreads, color=SERIES[0], linewidth=LINE_WIDTH, marker="o", markersize=4, capsize=3)
    axis.axhline(plant_tissue.SQUARE_LATTICE_BOND_THRESHOLD, color=TEXT_SECONDARY, linewidth=1, linestyle="--")
    axis.annotate("bond-percolation threshold, 1/2 (Kesten, 1980)", (conductances[0], plant_tissue.SQUARE_LATTICE_BOND_THRESHOLD), xytext=(0, 4), textcoords="offset points", fontsize=8, color=TEXT_SECONDARY)
    axis.set_xscale("log", base=2)
    axis.set_ylim(0.4, 1.0)
    style(axis, "Plant tissue: propagation block", "Junction conductance G", "Open-junction fraction at block")
    save(figure, "figure_5_plant_tissue")


def figure_congestion(report: dict[str, object]) -> None:
    """Figure 6: hub activity and global synchrony during induction, Wilson-Cowan human connectome."""
    coupling = 1.0
    figure, axes = plt.subplots(1, 2, figsize=(2 * PANEL_SIZE_INCHES[0], PANEL_SIZE_INCHES[1]))
    for colour, mode in zip(SERIES, ("none", "slow", "fast")):
        runs = [r for r in report["runs"] if r["compensation"] == mode and r["global_coupling"] == coupling]
        x = runs[0]["concentrations"]
        activity, _ = mean_and_spread([[v / r["low_load_hub_activity"][0] for v in r["low_load_hub_activity"]] for r in runs])
        axes[0].plot(x, activity, color=colour, linewidth=LINE_WIDTH, label=COMPENSATION_LABELS[mode])
    style(axes[0], "Hub activity during induction", "Concentration (× EC50)", "Hub activity / awake")
    axes[0].legend(frameon=False, fontsize=8)
    runs = [r for r in report["runs"] if r["compensation"] == "none" and r["global_coupling"] == coupling]
    x = runs[0]["concentrations"]
    for field, name, colour in (("low_load_synchrony", "low sensory load", SERIES[0]), ("high_load_synchrony", "high sensory load", SERIES[1])):
        mean, spread = mean_and_spread([[v / r[field][0] for v in r[field]] for r in runs])
        axes[1].plot(x, mean, color=colour, linewidth=LINE_WIDTH, label=name)
        axes[1].fill_between(x, mean - spread, mean + spread, color=colour, alpha=BAND_OPACITY, linewidth=0)
    style(axes[1], "Global synchrony during induction (no compensation)", "Concentration (× EC50)", "Synchrony χ / awake")
    axes[1].legend(frameon=False, fontsize=8)
    save(figure, "figure_6_congestion")


# Each figure with the report it is drawn from, so that figures can be redrawn after every study.
REPORT_FIGURES: tuple[tuple[str, Callable[[dict[str, object]], None]], ...] = (
    ("validation", figure_finite_size),
    ("species", figure_species_coherence),
    ("species", figure_broadcast),
    ("species", figure_plant),
    ("congestion", figure_congestion),
)


def main() -> None:
    figure_percolation_hysteresis()
    reports: dict[str, dict[str, object]] = {}
    for kind, draw in REPORT_FIGURES:
        if kind not in reports:
            try:
                reports[kind] = latest(kind)
            except FileNotFoundError:
                print(f"Skipped {draw.__name__}: no full {kind} report yet")
                continue
        draw(reports[kind])
    print(f"Figures written to {FIGURES_DIRECTORY.name}/")


if __name__ == "__main__":
    main()
