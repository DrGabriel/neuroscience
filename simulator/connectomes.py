"""Empirical connectomes used by the cross-species study, with source, licence and integrity checks.

Raw files are downloaded into `data/raw/<dataset>/` and are not redistributed in this
repository. Each download is verified against a pinned SHA-256 digest before use.
Dependencies: numpy, scipy; pyarrow for the FlyWire table.
"""

from __future__ import annotations

import csv
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.cluster.vq import kmeans2
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import eigsh

from provenance import file_sha256

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "raw"

# Synapse-count threshold used by the FlyWire consortium to define a connection
# between two neurons (Dorkenwald et al., 2024).
FLYWIRE_MINIMUM_SYNAPSES = 5
# Spectral partition size for networks without an anatomical parcellation.
NODES_PER_SPECTRAL_MODULE = 25

# FlyWire neuropil of the antennal lobe, the first olfactory relay (left and right).
DROSOPHILA_SENSORY_NEUROPILS = ("AL_L", "AL_R")

# Sensory populations driven by the stimulus in the local-processing test (Section 6.4).
# Human: transverse temporal gyrus (Heschl's gyrus), the primary auditory cortex.
HUMAN_SENSORY_LABEL_SUFFIX = "TT"
# C. elegans: the twelve classes of amphid sensory neurons, left and right (White et al., 1986).
CELEGANS_AMPHID_SENSORY_CLASSES = ("ADF", "ADL", "AFD", "ASE", "ASG", "ASH", "ASI", "ASJ", "ASK", "AWA", "AWB", "AWC")


@dataclass(frozen=True)
class Connectome:
    """Directed, weighted network: edge e carries signal from sources[e] to targets[e]."""

    name: str
    organism: str
    node_count: int
    sources: np.ndarray
    targets: np.ndarray
    weights: np.ndarray
    modules: np.ndarray
    module_basis: str
    sensory_nodes: np.ndarray
    sensory_description: str
    lengths_mm: np.ndarray | None = None

    @property
    def edge_count(self) -> int:
        return int(self.sources.size)

    @property
    def module_count(self) -> int:
        return int(np.unique(self.modules).size)


@dataclass(frozen=True)
class DatasetSource:
    key: str
    organism: str
    url: str
    file_name: str
    sha256: str
    licence: str
    redistributed: bool
    citations: tuple[str, ...]

    @property
    def directory(self) -> Path:
        return RAW_DATA_DIRECTORY / self.key

    @property
    def path(self) -> Path:
        return self.directory / self.file_name


CELEGANS = DatasetSource(
    key="celegans_openworm",
    organism="Caenorhabditis elegans (hermaphrodite)",
    url="https://raw.githubusercontent.com/openworm/c302/master/c302/data/herm_full_edgelist.csv",
    file_name="herm_full_edgelist.csv",
    sha256="142693f17556148d7f962835b18ac6dd5af18b7467eef61815ebc1dd5474c0ca",
    licence="MIT (OpenWorm c302)",
    redistributed=False,
    citations=(
        "Cook, S. J., et al. (2019). Whole-animal connectomes of both Caenorhabditis elegans sexes. Nature, 571, 63-71.",
        "OpenWorm c302, https://github.com/openworm/c302 (MIT licence).",
    ),
)

DROSOPHILA = DatasetSource(
    key="drosophila_flywire783",
    organism="Drosophila melanogaster (adult female brain)",
    url="https://zenodo.org/api/records/10676866/files/proofread_connections_783.feather/content",
    file_name="proofread_connections_783.feather",
    # Zenodo publishes MD5 f48f972d262323a102aed49af1396b8a for this file; the download matched it.
    sha256="24f960ae3e7d4f8cd30db3b62e99fb5179cc3d1e76d8c155bfb441e9737d3faf",
    licence="CC BY 4.0 (FlyWire, Zenodo record 10676866)",
    redistributed=False,
    citations=(
        "Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. Nature, 634, 124-138.",
        "Buhmann, J., et al. (2021). Automatic detection of synaptic partners in a whole-brain Drosophila electron microscopy data set. Nature Methods, 18, 771-774.",
        "Heinrich, L., Funke, J., Pape, C., Nunez-Iglesias, J., & Saalfeld, S. (2018). Synaptic cleft segmentation in non-isotropic volume electron microscopy of the complete Drosophila brain. In MICCAI 2018, Lecture Notes in Computer Science (pp. 317-325). https://doi.org/10.1007/978-3-030-00934-2_36",
    ),
)

HUMAN = DatasetSource(
    key="human_tvb998",
    organism="Homo sapiens (998-region structural connectome)",
    url="https://raw.githubusercontent.com/the-virtual-brain/tvb-data/master/tvb_data/connectivity/connectivity_998.zip",
    file_name="connectivity_998.zip",
    sha256="31c65d4b6bf1760d06e0c4ab95c71c8dd499e48814e47bf2284e62a2b9301afd",
    licence="GPL-3.0 (The Virtual Brain data); used, not redistributed",
    redistributed=False,
    citations=(
        "Hagmann, P., et al. (2008). Mapping the structural core of human cerebral cortex. PLoS Biology, 6(7), e159.",
        "Sanz Leon, P., et al. (2013). The Virtual Brain: a simulator of primate brain network dynamics. Frontiers in Neuroinformatics, 7, 10.",
    ),
)


class IntegrityError(RuntimeError):
    pass


def fetch(source: DatasetSource) -> Path:
    """Download the dataset if absent, then verify its pinned digest."""
    if not source.path.exists():
        source.directory.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(source.url, source.path)
    observed = file_sha256(source.path)
    if source.sha256 and observed != source.sha256:
        raise IntegrityError(f"{source.path}: expected SHA-256 {source.sha256}, found {observed}")
    return source.path


# ---------------------------------------------------------------------------
# Module partitions
# ---------------------------------------------------------------------------


def spectral_modules(node_count: int, sources: np.ndarray, targets: np.ndarray, seed: int) -> np.ndarray:
    """k-means on the leading eigenvectors of the normalised adjacency (spectral clustering)."""
    module_count = max(2, round(node_count / NODES_PER_SPECTRAL_MODULE))
    adjacency = coo_matrix((np.ones(sources.size), (sources, targets)), shape=(node_count, node_count)).tocsr()
    symmetric = ((adjacency + adjacency.T) > 0).astype(float)
    degree = np.asarray(symmetric.sum(axis=1)).ravel()
    inverse_root_degree = diags(1 / np.sqrt(np.maximum(degree, 1)))
    normalised = inverse_root_degree @ symmetric @ inverse_root_degree
    _, vectors = eigsh(normalised, k=module_count, which="LA")
    rows = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), np.finfo(float).eps)
    _, labels = kmeans2(rows, module_count, minit="++", seed=seed)
    return labels.astype(np.int32)


def dense_indices(labels: list[str]) -> tuple[np.ndarray, list[str]]:
    names = sorted(set(labels))
    index = {name: position for position, name in enumerate(names)}
    return np.array([index[label] for label in labels], dtype=np.int32), names


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_celegans(seed: int) -> Connectome:
    """Chemical synapses (directed) and gap junctions (both directions), weighted by contact count."""
    with fetch(CELEGANS).open(newline="") as handle:
        rows = [
            (row["Source"].strip(), row["Target"].strip(), float(row["Weight"]), row["Type"].strip())
            for row in csv.DictReader(handle)
        ]
    node_index, names = dense_indices([name for source, target, _, _ in rows for name in (source, target)])
    pairs = node_index.reshape(-1, 2)
    weights = np.array([weight for _, _, weight, _ in rows])
    is_gap_junction = np.array([kind == "electrical" for _, _, _, kind in rows])
    sources = np.concatenate([pairs[:, 0], pairs[is_gap_junction, 1]])
    targets = np.concatenate([pairs[:, 1], pairs[is_gap_junction, 0]])
    weights = np.concatenate([weights, weights[is_gap_junction]])
    node_count = len(names)
    return Connectome(
        name="C. elegans",
        organism=CELEGANS.organism,
        node_count=node_count,
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=weights.astype(np.float32),
        modules=spectral_modules(node_count, sources, targets, seed),
        module_basis=f"spectral clustering, about {NODES_PER_SPECTRAL_MODULE} nodes per module",
        sensory_nodes=np.array(
            [index for index, name in enumerate(names) if name[:3] in CELEGANS_AMPHID_SENSORY_CLASSES and name[3:] in ("L", "R")],
            dtype=np.int32,
        ),
        sensory_description="amphid sensory neurons (12 classes, left and right)",
    )


def load_human(_: int) -> Connectome:
    """Hagmann 998-region connectome with tract lengths; modules are the atlas's 66 anatomical regions."""
    archive = fetch(HUMAN)
    with zipfile.ZipFile(archive) as bundle:
        weights_matrix = np.loadtxt(bundle.open("weights.txt"))
        tract_lengths = np.loadtxt(bundle.open("tract_lengths.txt"))
        region_labels = [line.split()[0] for line in bundle.open("centres.txt").read().decode().splitlines() if line.strip()]
    region_to_area, _ = dense_indices(region_labels)
    targets, sources = np.nonzero(weights_matrix.T)
    return Connectome(
        name="Human",
        organism=HUMAN.organism,
        node_count=weights_matrix.shape[0],
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=weights_matrix[sources, targets].astype(np.float32),
        modules=region_to_area,
        module_basis="66 anatomical regions (Hagmann et al., 2008), labels from the atlas centres file",
        sensory_nodes=np.array(
            [index for index, label in enumerate(region_labels) if label.endswith(HUMAN_SENSORY_LABEL_SUFFIX)], dtype=np.int32
        ),
        sensory_description="transverse temporal gyrus (primary auditory cortex), both hemispheres",
        lengths_mm=tract_lengths[sources, targets].astype(np.float32),
    )


def thresholded_connections(
    sources_by_row: np.ndarray, targets_by_row: np.ndarray, synapses: np.ndarray, node_count: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Synapses summed over neuropils for each neuron pair, keeping pairs at the FlyWire threshold."""
    pair_keys, pair_of_row = np.unique(sources_by_row.astype(np.int64) * node_count + targets_by_row, return_inverse=True)
    pair_synapses = np.bincount(pair_of_row, weights=synapses)
    kept = pair_synapses >= FLYWIRE_MINIMUM_SYNAPSES
    sources, targets = np.divmod(pair_keys[kept], node_count)
    return sources, targets, pair_synapses[kept]


def load_drosophila(_: int) -> Connectome:
    """FlyWire v783: synapses summed over neuropils per neuron pair, kept at 5 or more synapses.

    Each neuron's module is the neuropil in which it receives most of its input synapses.
    """
    import pyarrow.feather as feather

    columns = ["pre_pt_root_id", "post_pt_root_id", "neuropil", "syn_count"]
    table = feather.read_table(fetch(DROSOPHILA), columns=columns, memory_map=True)
    pre = table["pre_pt_root_id"].to_numpy()
    post = table["post_pt_root_id"].to_numpy()
    synapses = table["syn_count"].to_numpy().astype(np.float64)
    neuropil_codes = table["neuropil"].dictionary_encode().combine_chunks()
    neuropil_names = neuropil_codes.dictionary.to_pylist()
    row_neuropils = neuropil_codes.indices.to_numpy()

    _, neuron_index = np.unique(np.concatenate([pre, post]), return_inverse=True)
    node_count = int(neuron_index.max()) + 1
    sources_by_row, targets_by_row = neuron_index[: pre.size], neuron_index[pre.size :]
    sources, targets, pair_synapses = thresholded_connections(sources_by_row, targets_by_row, synapses, node_count)
    input_by_neuropil = coo_matrix(
        (synapses, (targets_by_row, row_neuropils)), shape=(node_count, len(neuropil_names))
    ).toarray()
    modules = input_by_neuropil.argmax(axis=1).astype(np.int32)
    sensory_codes = [neuropil_names.index(name) for name in DROSOPHILA_SENSORY_NEUROPILS]
    receives_input = input_by_neuropil.sum(axis=1) > 0
    return Connectome(
        name="Drosophila",
        organism=DROSOPHILA.organism,
        node_count=node_count,
        sources=sources.astype(np.int32),
        targets=targets.astype(np.int32),
        weights=pair_synapses.astype(np.float32),
        modules=modules,
        module_basis="neuropil receiving most of each neuron's input synapses (FlyWire, 79 neuropils)",
        sensory_nodes=np.flatnonzero(np.isin(modules, sensory_codes) & receives_input).astype(np.int32),
        sensory_description="neurons whose main input neuropil is the antennal lobe (first olfactory relay), left and right",
    )


LOADERS: dict[str, Callable[[int], Connectome]] = {
    "celegans": load_celegans,
    "drosophila": load_drosophila,
    "human": load_human,
}
DATASET_SOURCES = (CELEGANS, DROSOPHILA, HUMAN)
