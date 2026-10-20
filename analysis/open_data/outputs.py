"""Result files: provenance, JSON serialisation, and exclusions recorded with their reasons rather than hidden."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path

import numpy as np
import scipy

from . import settings

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GIT_HEAD = REPO / ".git" / "HEAD"
REF_PREFIX = "ref: "
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
EXCLUDED = "excluded"
SECONDS_DECIMALS = 1
JSON_INDENT = 1


@dataclass(frozen=True)
class Output:
    """Where a result goes, the command-line arguments that produced it, and when the work started."""

    path: Path
    arguments: argparse.Namespace
    started: float


def git_commit() -> str | None:
    if not GIT_HEAD.exists():
        return None
    head = GIT_HEAD.read_text().strip()
    if not head.startswith(REF_PREFIX):
        return head
    ref = REPO / ".git" / head.removeprefix(REF_PREFIX)
    return ref.read_text().strip() if ref.exists() else head


def module_hashes() -> dict[str, str]:
    return {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.rglob("*.py")) if "tests" not in p.parts}


def settings_snapshot() -> dict:
    return {name: asdict(value) for name, value in vars(settings).items() if is_dataclass(value) and not isinstance(value, type)}


def provenance(arguments: argparse.Namespace) -> dict:
    return {
        "started_utc": time.strftime(UTC_FORMAT, time.gmtime()),
        "git_commit": git_commit(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "machine": platform.machine(),
        "module_sha256": module_hashes(),
        "settings": settings_snapshot(),
        "arguments": {k: str(v) for k, v in vars(arguments).items() if k != "handler"},
    }


def to_json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialise {type(value)}")


def write(output: Output, payload: dict) -> None:
    payload = {"provenance": provenance(output.arguments), **payload, "seconds": round(time.time() - output.started, SECONDS_DECIMALS)}
    output.path.parent.mkdir(parents=True, exist_ok=True)
    output.path.write_text(json.dumps(payload, indent=JSON_INDENT, default=to_json))
    print(f"wrote {output.path} ({payload['seconds']} s)")


def attempt(test: Callable[..., dict], *args) -> dict:
    """Run one test; a pre-specified exclusion (ValueError from a stated rule) is recorded with its reason, not hidden."""
    try:
        return test(*args)
    except ValueError as error:
        print(f"excluded from {test.__name__}: {error}", file=sys.stderr)
        return {EXCLUDED: str(error)}


def is_excluded(result: dict | None) -> bool:
    return not result or EXCLUDED in result


def included(results: list[dict | None]) -> list[dict]:
    return [r for r in results if not is_excluded(r)]
