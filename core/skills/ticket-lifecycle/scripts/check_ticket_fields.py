#!/usr/bin/env python3
"""Check a tracker ticket's fields against the lifecycle contract.

The input is a JSON object keyed by the logical field names listed in
references/field-contract.md. Map the tracker's own field keys to those names
before writing the file; this script never sees a tracker-specific key.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

STATES = ("create", "backlog", "in-progress", "done")
DEFAULT_SCALE = (1, 3, 5)
DEFAULT_CAP = 5
DEFAULT_ESTIMATE_STEP = Decimal("0.5")
DEFAULT_ACTUAL_STEP = Decimal("0.125")


@dataclass
class Finding:
    level: str
    field: str
    message: str


@dataclass
class Contract:
    scale: tuple
    cap: int
    estimate_step: Decimal
    actual_step: Decimal
    require_sprint: bool = False


def is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def to_decimal(value: Any) -> Optional[Decimal]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip())
        except InvalidOperation:
            return None
    return None


def on_step(value: Decimal, step: Decimal) -> bool:
    if step <= 0:
        return False
    quotient = value / step
    return quotient == quotient.to_integral_value()


def parse_date(value: Any) -> Optional[date]:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def check_points(points: Any, state: str, contract: Contract, findings: list) -> None:
    if is_empty(points):
        level = "WARN" if state == "backlog" else "FAIL"
        findings.append(Finding(level, "story_points", "missing"))
        return
    value = to_decimal(points)
    if value is None or value != value.to_integral_value():
        findings.append(Finding("FAIL", "story_points", f"not an integer: {points!r}"))
        return
    number = int(value)
    scale_text = ", ".join(str(item) for item in contract.scale)
    if number > contract.cap:
        findings.append(
            Finding(
                "FAIL",
                "story_points",
                f"{number} exceeds the cap {contract.cap}; split before creating",
            )
        )
    elif number not in contract.scale:
        findings.append(
            Finding("FAIL", "story_points", f"{number} is not on the scale {scale_text}")
        )
    else:
        findings.append(Finding("PASS", "story_points", str(number)))


def check_container(ticket: dict, contract: Contract, findings: list) -> None:
    points = ticket.get("story_points")
    if is_empty(points):
        findings.append(Finding("PASS", "story_points", "empty on a container"))
    else:
        findings.append(
            Finding(
                "FAIL",
                "story_points",
                "a container carries no points; totals live on the leaves",
            )
        )
    leaves = ticket.get("leaves") or []
    if not isinstance(leaves, list):
        findings.append(Finding("FAIL", "leaves", "must be a list"))
        return
    total = Decimal(0)
    for index, leaf in enumerate(leaves):
        label = f"leaf {index + 1}"
        leaf_points = None
        if isinstance(leaf, dict):
            label = str(leaf.get("key") or label)
            leaf_points = to_decimal(leaf.get("story_points"))
        if leaf_points is None:
            findings.append(Finding("FAIL", f"leaves.{label}", "missing story_points"))
        elif leaf_points > contract.cap:
            findings.append(
                Finding(
                    "FAIL",
                    f"leaves.{label}",
                    f"{leaf_points} exceeds the cap {contract.cap}; split again",
                )
            )
        else:
            total += leaf_points
    if leaves:
        findings.append(Finding("PASS", "leaves", f"{len(leaves)} leaves, {total} points"))
    else:
        findings.append(Finding("WARN", "leaves", "no leaf table supplied"))


def check_dates(ticket: dict, state: str, findings: list) -> None:
    required = state != "backlog"
    parsed = {}
    for name in ("start_date", "due_date"):
        raw = ticket.get(name)
        if is_empty(raw):
            if required:
                findings.append(Finding("FAIL", name, "missing"))
            else:
                findings.append(Finding("PASS", name, "empty is allowed in backlog"))
            continue
        value = parse_date(raw)
        if value is None:
            findings.append(Finding("FAIL", name, f"not YYYY-MM-DD: {raw!r}"))
            continue
        parsed[name] = value
        findings.append(Finding("PASS", name, value.isoformat()))
    if "start_date" in parsed and "due_date" in parsed:
        if parsed["due_date"] < parsed["start_date"]:
            findings.append(Finding("FAIL", "due_date", "before start_date"))


def check_effort(
    raw: Any, field: str, step: Decimal, allow_zero: bool, findings: list
) -> None:
    value = to_decimal(raw)
    if value is None:
        findings.append(Finding("FAIL", field, f"not a number: {raw!r}"))
    elif value < 0 or (value == 0 and not allow_zero):
        bound = "zero or more" if allow_zero else "above zero"
        findings.append(Finding("FAIL", field, f"{value} must be {bound}"))
    elif not on_step(value, step):
        findings.append(Finding("FAIL", field, f"{value} is not a multiple of the step {step}"))
    else:
        findings.append(Finding("PASS", field, str(value)))


def check(ticket: dict, state: str, contract: Contract) -> list:
    findings: list = []
    if state not in STATES:
        findings.append(Finding("FAIL", "state", f"unknown state {state!r}; use one of {', '.join(STATES)}"))
        return findings

    if is_empty(ticket.get("parent")):
        findings.append(Finding("FAIL", "parent", "missing; a leaf or container must point at its parent"))
    else:
        findings.append(Finding("PASS", "parent", str(ticket["parent"])))

    if bool(ticket.get("container", False)):
        check_container(ticket, contract, findings)
        return findings

    check_points(ticket.get("story_points"), state, contract, findings)
    check_dates(ticket, state, findings)

    estimate = ticket.get("estimate_effort")
    if is_empty(estimate):
        level = "WARN" if state == "backlog" else "FAIL"
        findings.append(Finding(level, "estimate_effort", "missing"))
    else:
        check_effort(estimate, "estimate_effort", contract.estimate_step, False, findings)

    actual = ticket.get("actual_effort")
    if state == "done":
        if is_empty(actual):
            findings.append(
                Finding("FAIL", "actual_effort", "missing before done; zero counts, empty does not")
            )
        else:
            check_effort(actual, "actual_effort", contract.actual_step, True, findings)
    elif not is_empty(actual):
        findings.append(
            Finding("WARN", "actual_effort", "set before done; confirm it is measured, not estimated")
        )

    if contract.require_sprint and state == "in-progress" and is_empty(ticket.get("sprint")):
        findings.append(Finding("FAIL", "sprint", "missing for in-progress work"))
    return findings


def parse_scale(text: str) -> tuple:
    values = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if not item.isdigit():
            raise argparse.ArgumentTypeError(f"scale values must be integers: {item!r}")
        values.append(int(item))
    if not values:
        raise argparse.ArgumentTypeError("scale must list at least one integer")
    return tuple(sorted(set(values)))


def parse_step(text: str) -> Decimal:
    try:
        value = Decimal(text.strip())
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError(f"step must be a number: {text!r}") from error
    if value <= 0:
        raise argparse.ArgumentTypeError("step must be above zero")
    return value


def load_ticket(path: str) -> dict:
    if path == "-":
        data = json.load(sys.stdin)
    else:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("ticket JSON must be an object keyed by logical field names")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a ticket's fields against the lifecycle contract for a target state"
    )
    parser.add_argument("ticket", help="JSON file of logical fields, or - for stdin")
    parser.add_argument("--state", choices=STATES, help="target state; defaults to the ticket's state field or create")
    parser.add_argument("--scale", type=parse_scale, default=DEFAULT_SCALE, help="allowed point values, comma separated")
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP, help="largest points a single leaf may carry")
    parser.add_argument("--estimate-step", type=parse_step, default=DEFAULT_ESTIMATE_STEP)
    parser.add_argument("--actual-step", type=parse_step, default=DEFAULT_ACTUAL_STEP)
    parser.add_argument("--require-sprint", action="store_true", help="fail in-progress leaves with no sprint")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        ticket = load_ticket(args.ticket)
    except (OSError, ValueError) as error:
        print(f"ERROR: cannot read ticket: {error}", file=sys.stderr)
        return 2

    state = args.state or str(ticket.get("state") or "create")
    contract = Contract(
        scale=args.scale,
        cap=args.cap,
        estimate_step=args.estimate_step,
        actual_step=args.actual_step,
        require_sprint=args.require_sprint,
    )
    findings = check(ticket, state, contract)
    counts = {level: sum(item.level == level for item in findings) for level in ("PASS", "WARN", "FAIL")}

    if args.json:
        print(json.dumps({"state": state, "findings": [asdict(item) for item in findings], "summary": counts}, indent=2))
    else:
        print(f"State: {state}")
        for item in findings:
            print(f"{item.level:4} {item.field}: {item.message}")
        print("Summary: " + " ".join(f"{level.lower()}={counts[level]}" for level in ("PASS", "WARN", "FAIL")))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
