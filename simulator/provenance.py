"""Run provenance: the machine, software and exact source that produced a result.

Standard library only, so every study in this directory can record the same metadata.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Sequence

SIMULATOR_DIRECTORY = Path(__file__).resolve().parent
# Third-party packages whose versions every phase-model or Wilson-Cowan report records; studies add their own.
NUMERICAL_PACKAGES = ("numpy", "scipy")
BYTES_PER_GIBIBYTE = 1024**3
HASH_CHUNK_BYTES = 1 << 20
SYSCTL_KEYS = (
    "hw.model",
    "machdep.cpu.brand_string",
    "hw.memsize",
    "hw.ncpu",
    "hw.perflevel0.physicalcpu",
    "hw.perflevel1.physicalcpu",
)


def command_output(command: Sequence[str]) -> str:
    """Output of a command, or an explicit 'unavailable' note that keeps the failure visible."""
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return f"unavailable (exit {completed.returncode}: {completed.stderr.strip()})"
    return completed.stdout.strip()


def file_sha256(path: Path) -> str:
    """SHA-256 of a file, read in chunks so that large datasets are not loaded into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_simulator_source(path: Path) -> bool:
    """In the simulator directory or one of its packages."""
    return SIMULATOR_DIRECTORY in path.parents


def source_name(path: Path) -> str:
    """A module's name in reports: its path from the simulator directory, which is its file name at the top level."""
    return path.relative_to(SIMULATOR_DIRECTORY).as_posix()


def loaded_sources() -> tuple[Path, ...]:
    """Every simulator module imported by the running study, including those of its packages, so the hashes cover
    all code that ran."""
    paths = {
        Path(module.__file__).resolve()
        for module in list(sys.modules.values())
        if getattr(module, "__file__", None) and is_simulator_source(Path(module.__file__).resolve())
    }
    return tuple(sorted(paths))


def installed_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "not installed"


# The source record taken when a study starts (record_launch), so that a report describes the code that ran,
# even if files change on disk while it runs.
_LAUNCH: dict[str, object] = {}


def source_record(source_files: Sequence[Path], captured: str) -> dict[str, object]:
    repository = source_files[0].parent if source_files else Path.cwd()
    return {
        "git_commit": command_output(["git", "-C", str(repository), "rev-parse", "HEAD"]),
        "git_working_tree_dirty": bool(command_output(["git", "-C", str(repository), "status", "--porcelain", "--", "*.py"])),
        "sha256": {source_name(path): file_sha256(path) for path in source_files},
        "captured": captured,
    }


def record_launch() -> None:
    """Call at the start of a study, after its imports, to fix the source record of its report."""
    _LAUNCH.clear()
    _LAUNCH.update(source_record(loaded_sources(), "at launch"))


def collect(source_files: Sequence[Path], packages: Sequence[str] = ()) -> dict[str, object]:
    hardware = {key: command_output(["sysctl", "-n", key]) for key in SYSCTL_KEYS}
    memory_bytes = hardware["hw.memsize"]
    launched = dict(_LAUNCH) if {source_name(path) for path in source_files} <= set(_LAUNCH.get("sha256", {})) else None
    return {
        "hardware": hardware,
        "memory_gibibytes": int(memory_bytes) / BYTES_PER_GIBIBYTE if memory_bytes.isdigit() else memory_bytes,
        "operating_system": {
            "product_version": command_output(["sw_vers", "-productVersion"]),
            "build_version": command_output(["sw_vers", "-buildVersion"]),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "python": {
            "implementation": platform.python_implementation(),
            "version": sys.version.split()[0],
            "packages": {package: installed_version(package) for package in packages} or "standard library only",
        },
        "source": launched or source_record(source_files, "at the end of the run"),
    }


def markdown_rows(provenance: dict[str, object]) -> list[str]:
    hardware = provenance["hardware"]
    operating_system = provenance["operating_system"]
    python = provenance["python"]
    source = provenance["source"]
    packages = python["packages"]
    package_text = packages if isinstance(packages, str) else ", ".join(f"{name} {version}" for name, version in packages.items())
    memory = provenance["memory_gibibytes"]
    memory_text = f"{memory:.0f} GiB" if isinstance(memory, float) else memory
    return [
        f"| Machine | {hardware['hw.model']}, {hardware['machdep.cpu.brand_string']} |",
        f"| CPU cores | {hardware['hw.ncpu']} ({hardware['hw.perflevel0.physicalcpu']} performance, {hardware['hw.perflevel1.physicalcpu']} efficiency) |",
        f"| Memory | {memory_text} |",
        f"| Operating system | macOS {operating_system['product_version']} (build {operating_system['build_version']}), {operating_system['machine']} |",
        f"| Python | {python['implementation']} {python['version']}; {package_text} |",
        f"| Git commit | `{source['git_commit']}` (working tree dirty: {source['git_working_tree_dirty']}) |",
        *[f"| SHA-256 `{name}` | `{digest}` |" for name, digest in source["sha256"].items()],
    ]
