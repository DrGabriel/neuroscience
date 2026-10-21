"""Deviation D7: the exploratory group step reads its inputs from a list, as one folder would be read."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.open_data import exploratory_group

PREFIX = "michigan"
OTHER_PREFIX = "prios"


def a_result(folder: Path, name: str) -> Path:
    path = folder / name
    path.write_text(json.dumps({"name": name}))
    return path


class ListedInputTests(unittest.TestCase):
    def test_files_from_two_folders_are_read_in_name_order_and_only_for_the_dataset_asked(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            later = a_result(Path(first), f"{PREFIX}_sub-09.json")
            earlier = a_result(Path(second), f"{PREFIX}_sub-02.json")
            other = a_result(Path(second), f"{OTHER_PREFIX}_sub-01.json")
            listing = Path(first) / "inputs.txt"
            listing.write_text("\n".join(str(p) for p in (later, other, earlier)))
            names = [r["name"] for r in exploratory_group.load_listed(listing, PREFIX)]
        self.assertEqual(names, [f"{PREFIX}_sub-02.json", f"{PREFIX}_sub-09.json"])

    def test_a_result_listed_twice_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            twice = [a_result(Path(folder), f"{PREFIX}_sub-02.json") for folder in (first, second)]
            listing = Path(first) / "inputs.txt"
            listing.write_text("\n".join(str(p) for p in twice))
            with self.assertRaises(ValueError):
                exploratory_group.load_listed(listing, PREFIX)

    def test_a_folder_is_still_read_as_committed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            a_result(Path(folder), f"{PREFIX}_sub-02.json")
            self.assertEqual(len(exploratory_group.load_listed(Path(folder), PREFIX)), 1)


if __name__ == "__main__":
    unittest.main()
