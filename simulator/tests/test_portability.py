"""The repository must work wherever it is cloned or published (Zenodo, a public website).

Fails if any text file in the repository holds an absolute path to a home or temporary directory or a
file:// address, which would only work on the machine that wrote it.

Run from the simulator directory: ../.venv/bin/python -m unittest discover -s tests -t .
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
SKIPPED_DIRECTORIES = frozenset({".git", ".venv", "__pycache__", "raw", "drafts", "node_modules"})
TEXT_SUFFIXES = frozenset({".py", ".js", ".html", ".css", ".md", ".json", ".cff", ".txt", ".toml", ".yml", ".yaml"})
MACHINE_PATH = re.compile(r"(/Users/[^/\s]+/|/home/[^/\s]+/|/private/tmp/|[A-Za-z]:\\\\Users\\\\|file:///)")


def text_files() -> list[Path]:
    return [
        path for path in REPOSITORY.rglob("*")
        if path.is_file() and path.suffix in TEXT_SUFFIXES and not SKIPPED_DIRECTORIES & set(path.relative_to(REPOSITORY).parts)
    ]


class PortabilityTests(unittest.TestCase):
    def test_no_file_holds_a_path_that_only_exists_on_one_machine(self) -> None:
        offenders = [
            f"{path.relative_to(REPOSITORY)}: {match.group(0)}"
            for path in text_files()
            if path.name != Path(__file__).name
            for match in [MACHINE_PATH.search(path.read_text(errors="ignore"))]
            if match
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
