#!/usr/bin/env python3
"""Decide whether a tracker write targets a parent the current user does not own.

The script reads facts that were already collected from the tracker and prints
one line: a decision word followed by a reason. It performs no network access.

Decisions:
  OUTSIDE  the target is not an ancestor of the working issue; the guard does
           not decide this write.
  ALLOW    the target is an ancestor the current user owns, or the user gave an
           explicit override in the current session.
  BLOCK    the target is an ancestor owned by someone else, or ownership or the
           current user's identity could not be established (fails closed).

Exit status: 0 for ALLOW or OUTSIDE, 2 for BLOCK, 1 for malformed input.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple

OUTSIDE = "OUTSIDE"
ALLOW = "ALLOW"
BLOCK = "BLOCK"
EXIT_CODES = {OUTSIDE: 0, ALLOW: 0, BLOCK: 2}


class InputError(ValueError):
    """The facts document does not have the required shape."""


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def owners_of(issue: Dict[str, Any]) -> List[str]:
    """Return the non-empty owner identities recorded on an issue."""
    raw = issue.get("owner")
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, list):
        values = [item for item in raw if isinstance(item, str)]
    else:
        return []
    return [item.strip() for item in values if item.strip()]


def ancestors(issues: Dict[str, Dict[str, Any]], start: str) -> List[str]:
    """Return the parent chain of ``start``, nearest first, stopping on a cycle."""
    chain: List[str] = []
    seen = {start}
    current = _clean(issues.get(start, {}).get("parent"))
    while current and current not in seen:
        chain.append(current)
        seen.add(current)
        current = _clean(issues.get(current, {}).get("parent"))
    return chain


def validate(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("facts must be a JSON object")
    issues = payload.get("issues")
    if not isinstance(issues, dict):
        raise InputError("'issues' must be an object keyed by issue key")
    for key, record in issues.items():
        if not isinstance(record, dict):
            raise InputError(f"issue record for {key!r} must be an object")
    working = _clean(payload.get("working_issue"))
    target = _clean(payload.get("target"))
    if not working:
        raise InputError("'working_issue' is required")
    if not target:
        raise InputError("'target' is required")
    override = payload.get("override", False)
    if not isinstance(override, bool):
        raise InputError("'override' must be true or false")
    return {
        "issues": issues,
        "working_issue": working,
        "target": target,
        "current_user": _clean(payload.get("current_user")),
        "override": override,
    }


def decide(payload: Any) -> Tuple[str, str]:
    """Return ``(decision, reason)`` for the write described by ``payload``."""
    facts = validate(payload)
    issues: Dict[str, Dict[str, Any]] = facts["issues"]
    working: str = facts["working_issue"]
    target: str = facts["target"]
    current_user: str = facts["current_user"]
    override: bool = facts["override"]

    if target == working:
        return OUTSIDE, "target is the working issue itself; this guard decides only ancestors"
    chain = ancestors(issues, working)
    if target not in chain:
        return OUTSIDE, f"{target} is not an ancestor of {working}; other write rules apply"

    record = issues.get(target)
    owners = owners_of(record) if record is not None else []
    if current_user and current_user in owners:
        return ALLOW, f"{target} is owned by the current user"
    if override:
        return ALLOW, (
            f"{target} is owned by someone else; allowed only by the user's explicit "
            "override, keep the change minimal and report it"
        )
    if record is None:
        return BLOCK, f"{target} is an ancestor of {working} but no record was read; failing closed"
    if not current_user:
        return BLOCK, "current user identity is unknown; failing closed"
    if not owners:
        return BLOCK, f"{target} has no visible owner; failing closed"
    return BLOCK, f"{target} is an ancestor of {working} owned by someone else"


def load(source: str) -> Any:
    if source == "-":
        return json.load(sys.stdin)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decide whether a tracker write targets a parent the current user does not own"
    )
    parser.add_argument("facts", help="path to a JSON facts file, or - for standard input")
    parser.add_argument("--json", action="store_true", help="emit a JSON object instead of a line")
    args = parser.parse_args()

    try:
        decision, reason = decide(load(args.facts))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"decision": decision, "reason": reason}))
    else:
        print(f"{decision}: {reason}")
    return EXIT_CODES[decision]


if __name__ == "__main__":
    raise SystemExit(main())
