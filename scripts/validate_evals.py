#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    installed = {
        path.parent.name for path in (root / "core" / "skills").glob("*/SKILL.md")
    }
    cases = json.loads((root / "evals" / "routing.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    seen: set[str] = set()

    if not isinstance(cases, list) or not cases:
        errors.append("evals/routing.json must contain a non-empty array")
        cases = []

    for index, case in enumerate(cases):
        prefix = f"case {index + 1}"
        if not isinstance(case, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}: missing id")
        elif case_id in seen:
            errors.append(f"{prefix}: duplicate id {case_id}")
        else:
            seen.add(case_id)
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            errors.append(f"{prefix}: missing prompt")
        expected = case.get("expected_skill")
        if expected not in installed:
            errors.append(f"{prefix}: unknown expected skill {expected!r}")
        forbidden = case.get("forbidden_actions")
        if not isinstance(forbidden, list) or not forbidden or not all(
            isinstance(item, str) and item for item in forbidden
        ):
            errors.append(f"{prefix}: forbidden_actions must be a non-empty string array")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(cases)} synthetic routing cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
