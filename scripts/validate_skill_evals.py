#!/usr/bin/env python3
"""Validate every behavioral definition in the designated suite directory."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from .skill_eval import main as validate_command
else:
    from skill_eval import main as validate_command


def validate_suites(root: Path) -> int:
    evals = root / "evals"
    misplaced = sorted(path for path in evals.glob("*.json") if path.name != "routing.json")
    if misplaced:
        for path in misplaced:
            print(
                f"ERROR: unexpected top-level evaluation file: evals/{path.name}. "
                "Move behavioral suites to evals/suites/; put other definition formats "
                "in a named evals/<kind>/ directory. Only routing.json is allowed here.",
                file=sys.stderr,
            )
        return 1
    # Other definition formats have their own named directories and validators.
    suites = sorted((evals / "suites").rglob("*.json"))
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
