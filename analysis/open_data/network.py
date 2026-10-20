"""Functional networks, their surrogate-based edge thresholds and the giant component (the order parameter S)."""

from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components

from .specs import EdgeTest

DC_BIN = 0


def phase_randomise(x: np.ndarray, rng: np.random.Generator, common: bool = False) -> np.ndarray:
    """Surrogate with each row's power spectrum kept and its phases replaced.

    With ``common`` the same random phases are added to every row, which keeps the cross-correlations;
    without it the rows become independent.
    """
    x = np.atleast_2d(x)
    spectrum = np.fft.rfft(x, axis=-1)
    n_freq = spectrum.shape[-1]
    shape = (1, n_freq) if common else (x.shape[0], n_freq)
    phases = rng.uniform(0.0, 2 * np.pi, size=shape)
    phases[:, DC_BIN] = 0.0
    if x.shape[-1] % 2 == 0:
        phases[:, -1] = 0.0
    return np.fft.irfft(spectrum * np.exp(1j * phases), n=x.shape[-1], axis=-1)


def zscore_rows(x: np.ndarray) -> np.ndarray:
    centred = x - x.mean(axis=-1, keepdims=True)
    scale = centred.std(axis=-1, keepdims=True)
    scale[scale == 0] = 1.0
    return centred / scale


def off_diagonal(matrix: np.ndarray) -> np.ndarray:
    return matrix[np.triu_indices(matrix.shape[0], k=1)]


def surrogate_correlation_threshold(x: np.ndarray, test: EdgeTest) -> float:
    """Upper (1 - alpha) quantile of correlations between independent surrogates of the same rows, pooled over pairs."""
    pooled = [off_diagonal(np.corrcoef(phase_randomise(x, test.rng))) for _ in range(test.surrogates.count)]
    return float(np.quantile(np.concatenate(pooled), 1.0 - test.surrogates.alpha))


def adjacency_above(weights: np.ndarray, threshold: float) -> np.ndarray:
    adjacency = weights > threshold
    np.fill_diagonal(adjacency, False)
    return adjacency


def giant_component_fraction(adjacency: np.ndarray) -> float:
    """Share of nodes in the largest connected component (undirected)."""
    n_nodes = adjacency.shape[0]
    if n_nodes == 0:
        raise ValueError("empty network")
    _, labels = connected_components(csr_matrix(adjacency | adjacency.T), directed=False)
    return float(np.bincount(labels).max() / n_nodes)


def correlation_network(window: np.ndarray, test: EdgeTest) -> dict:
    """Giant component and mean coupling of one window of node time series (nodes x samples)."""
    correlation = np.corrcoef(window)
    threshold = surrogate_correlation_threshold(window, test)
    return {
        "giant_component": giant_component_fraction(adjacency_above(correlation, threshold)),
        "mean_coupling": float(off_diagonal(correlation).mean()),
        "threshold": threshold,
    }
