"""What the downloader fetches for each dataset: exactly the files the open-data tests read."""

from __future__ import annotations

from pathlib import Path

from .constants import Dataset
from .transfer import Item, get_json, post_json

REPO = Path(__file__).resolve().parents[2]
DESTINATION = REPO / "data_external"
OPENNEURO_S3 = "https://s3.amazonaws.com/openneuro.org"
OPENNEURO_GRAPHQL = "https://openneuro.org/crn/graphql"
NEUROTYCHO_CATALOGUE = "https://neurotycho.org/data/detail.json"
NEUROTYCHO_ANAESTHESIA_TASK, NEUROTYCHO_MAP_TASK = "78", "74"
NEUROTYCHO_AGENTS = ("KTMD", "PF", "KT", "MD")
MICHIGAN, MICHIGAN_TAG = "ds006623", "1.0.0"
PRIOS, PRIOS_TAG = "ds004370", "1.0.2"
IMAGERY_RUNS = (1, 2, 3, 4)
INSTRUCTIONS = ("action", "navi", "squeeze", "tennis")
INFUSION_KINDS = ("ESC", "PLAS")
SUBJECT_PREFIX = "sub-"
INSECURE, SECURE = "http://", "https://"
FIRST_DOWNLOAD = 0
MICHIGAN_SHARED = ("derivatives/LOR_ROR_Timing.csv", "derivatives/Participant_Info.csv", "README.md", "dataset_description.json")
PRIOS_SHARED = ("README.txt", "participants.tsv", "dataset_description.json")


def openneuro_listing(dataset: str, tag: str, tree: str | None = None) -> list[dict]:
    clause = f', tree: "{tree}"' if tree else ""
    query = f'{{ snapshot(datasetId: "{dataset}", tag: "{tag}") {{ files(recursive: false{clause}) {{ id filename size directory }} }} }}'
    payload = post_json(OPENNEURO_GRAPHQL, {"query": query})
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0]["message"])
    return payload["data"]["snapshot"]["files"]


def openneuro_walk(dataset: str, tag: str, path: str) -> list[dict]:
    """Files directly inside ``path`` (slash-separated), each with its size."""
    entries = openneuro_listing(dataset, tag)
    for part in path.split("/"):
        match = [e for e in entries if e["filename"] == part and e["directory"]]
        if not match:
            raise FileNotFoundError(f"{dataset}: no folder {path}")
        entries = openneuro_listing(dataset, tag, match[0]["id"])
    return [e for e in entries if not e["directory"]]


def openneuro_subjects(dataset: str, tag: str) -> list[str]:
    return [e["filename"] for e in openneuro_listing(dataset, tag) if e["directory"] and e["filename"].startswith(SUBJECT_PREFIX)]


def michigan_subject_paths(subject: str) -> list[str]:
    func = f"derivatives/xcp_d_without_GSR_bandpass_output/{subject}/func"
    infusion = [f"derivatives/Propofol_Infusion/{subject}/{subject}_task{r}_{kind}.1D" for r in IMAGERY_RUNS for kind in INFUSION_KINDS]
    motion = [f"{func}/{subject}_task-imagery_run-{r}_motion.tsv" for r in IMAGERY_RUNS]
    bold = [f"{func}/{subject}_task-imagery_run-{r}_space-MNI152NLin2009cAsym_seg-4S156Parcels_stat-mean_timeseries.tsv" for r in IMAGERY_RUNS]
    return infusion + motion + bold


def michigan_items(limit: int | None) -> list[Item]:
    root = DESTINATION / MICHIGAN
    shared = list(MICHIGAN_SHARED) + [f"derivatives/Squeeze_Force/Instruction_Timing/Ideal_task{r}_{c}.xmat.1D" for r in IMAGERY_RUNS for c in INSTRUCTIONS]
    subject_paths = [p for s in openneuro_subjects(MICHIGAN, MICHIGAN_TAG)[:limit] for p in michigan_subject_paths(s)]
    return [Item(f"{OPENNEURO_S3}/{MICHIGAN}/{p}", root / p) for p in shared + subject_paths]


def prios_items(limit: int | None) -> list[Item]:
    root = DESTINATION / PRIOS
    items = [Item(f"{OPENNEURO_S3}/{PRIOS}/{p}", root / p) for p in PRIOS_SHARED]
    for subject in openneuro_subjects(PRIOS, PRIOS_TAG)[:limit]:
        folder = f"{subject}/ses-1/ieeg"
        entries = openneuro_walk(PRIOS, PRIOS_TAG, folder)
        items += [Item(f"{OPENNEURO_S3}/{PRIOS}/{folder}/{e['filename']}", root / folder / e["filename"], int(e["size"])) for e in entries]
    return items


def neurotycho_items(limit: int | None) -> list[Item]:
    catalogue = get_json(NEUROTYCHO_CATALOGUE)["expdata"]
    root = DESTINATION / "neurotycho" / "zips"
    chosen = [e for e in catalogue if e["taskid"] == NEUROTYCHO_ANAESTHESIA_TASK and e["Session"] in NEUROTYCHO_AGENTS]
    maps = [e for e in catalogue if e["taskid"] == NEUROTYCHO_MAP_TASK]
    urls = [e["Download"][FIRST_DOWNLOAD]["filename"].replace(INSECURE, SECURE) for e in maps + chosen[:limit]]
    return [Item(url, root / Path(url).name, extract=True) for url in urls]


CATALOGUES = {Dataset.MICHIGAN: michigan_items, Dataset.NEUROTYCHO: neurotycho_items, Dataset.PRIOS: prios_items}
