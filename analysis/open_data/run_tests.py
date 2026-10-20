"""Run the open-data unit tests with an isolated interpreter: .venv/bin/python -I analysis/open_data/run_tests.py"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(REPO / "analysis" / "open_data" / "tests"), top_level_dir=str(REPO))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
