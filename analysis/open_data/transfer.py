"""Network transfer for the downloader: sizes, retried fetches with a size check, and archive extraction that refuses
any member whose path would leave the destination. Downloads are data, never code; nothing here executes them."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

TIMEOUT_SECONDS = 120
CHUNK_BYTES = 1 << 20
ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 5
PARTIAL_SUFFIX = ".part"
JSON_HEADERS = {"Content-Type": "application/json"}

Result = TypeVar("Result")


@dataclass(frozen=True)
class Item:
    """One file to fetch; ``size`` is known in advance for some sources, ``extract`` marks a zip archive."""

    url: str
    target: Path
    size: int | None = None
    extract: bool = False


def with_retries(action: Callable[[], Result]) -> Result:
    """Retry transient network failures; an HTTP error status (404, 403) is final and raised at once."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return action()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == ATTEMPTS:
                raise
            time.sleep(RETRY_PAUSE_SECONDS)
    raise AssertionError("unreachable")


def http_size(url: str) -> int:
    def head() -> int:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=TIMEOUT_SECONDS) as response:
            return int(response.headers["Content-Length"])

    return with_retries(head)


def post_json(url: str, body: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=JSON_HEADERS)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def fetch(item: Item, size: int) -> None:
    item.target.parent.mkdir(parents=True, exist_ok=True)
    partial = item.target.with_name(item.target.name + PARTIAL_SUFFIX)
    with urllib.request.urlopen(item.url, timeout=TIMEOUT_SECONDS) as response, partial.open("wb") as handle:
        while chunk := response.read(CHUNK_BYTES):
            handle.write(chunk)
    if partial.stat().st_size != size:
        raise IOError(f"received {partial.stat().st_size} bytes, expected {size}")
    partial.rename(item.target)


def _member_target(archive: zipfile.ZipFile, member: zipfile.ZipInfo, destination: Path) -> Path:
    target = (destination / member.filename).resolve()
    if not target.is_relative_to(destination):
        raise ValueError(f"{archive.filename}: member {member.filename} would leave {destination}")
    return target


def _extract_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, target: Path) -> None:
    if member.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        return
    if target.exists() and target.stat().st_size == member.file_size:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member) as source, target.open("wb") as sink:
        while chunk := source.read(CHUNK_BYTES):
            sink.write(chunk)


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            _extract_member(archive, member, _member_target(archive, member, destination))
