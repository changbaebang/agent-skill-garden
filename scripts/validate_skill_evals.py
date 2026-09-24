#!/usr/bin/env python3
"""Validate every behavioral definition in the designated suite directory."""
from __future__ import annotations

import sys
from pathlib import Path

from skill_eval import main as validate_command


def validate_suites(root: Path) -> int:
    # Other eval formats, captured runs, and reports are not suite definitions.
    suites = sorted((root / "evals" / "suites").rglob("*.json"))
    if not suites:
        print("ERROR: evals/suites must contain at least one behavioral suite", file=sys.stderr)
        return 1
    for suite in suites:
        status = validate_command(["validate", str(suite)])
        if status:
            return status
    return 0


if __name__ == "__main__":
    raise SystemExit(validate_suites(Path(__file__).resolve().parents[1]))
