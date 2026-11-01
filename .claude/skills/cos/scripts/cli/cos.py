#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""`cos` without a virtual environment or a build: `uv run --script <skill>/scripts/cli/cos.py …`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from cos.cli import main  # noqa: E402

sys.exit(main())
