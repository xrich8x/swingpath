"""Make the `swingvision` package importable when pytest is run from anywhere
(e.g. `python -m pytest tests/` inside backend/, or from the repo root)."""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
