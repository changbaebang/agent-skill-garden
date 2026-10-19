#!/usr/bin/env python3
"""Judge whether the changes behind a deployment request may ship.

Reads the code host's JSON for one or more pull requests (a single object or
an array) and applies the release gate. A merged change passes the review
axis. An open change must be a non-draft, approved, mergeable request with no
failing and no pending check. The check axis is judged for both.

Two traps are handled here so they are never handled by eye:

* The same check name can appear twice in a rollup after a re-run, and the
  older failure survives in the data. Only the latest run per name is judged,
  ordered by completion time, or by start time for a run still in progress.
* A check the team has declared non-blocking may fail routinely. It is
  exempted only when named with ``--exempt-check``, and every applied
  exemption is reported so it can be written into the approval record.

No network access and no organization values. Fetch the JSON first with the
host's CLI or API (field names are listed in references/gates-and-reasons.md).
An entry of the form ``{"ref": "...", "error": "..."}`` marks a change that
could not be fetched; it is reported as UNVERIFIED, which is a different
finding from no change being linked at all.

Exit status: 0 approvable, 2 hold, 1 unusable input.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

APPROVABLE = "approvable"
HOLD = "hold"

NO_PR = "NO_PR"
UNVERIFIED = "UNVERIFIED"
PR_DRAFT = "PR_DRAFT"
PR_NOT_APPROVED = "PR_NOT_APPROVED"
PR_NOT_MERGEABLE = "PR_NOT_MERGEABLE"
CI_FAILED = "CI_FAILED"
CI_PENDING = "CI_PENDING"

FAILED = {
    "FAILURE",
    "FAILED",
    "ERROR",
    "TIMED_OUT",
    "CANCELLED",
    "STARTUP_FAILURE",
    "ACTION_REQUIRED",
}
PENDING = {"PENDING", "IN_PROGRESS", "QUEUED", "WAITING", "REQUESTED", "EXPECTED", "STALE"}
PASSED = {"SUCCESS", "NEUTRAL", "SKIPPED"}


def _timestamp(value: Any) -> float:
    """ISO-8601 to epoch seconds; a trailing Z is accepted; unparsable is 0."""
    if not isinstance(value, str) or not value.strip():
        return 0.0
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def check_name(check: Dict[str, Any]) -> str:
    """Check runs carry ``name``; commit statuses carry ``context``."""
    return str(check.get("name") or check.get("context") or "unnamed")


def check_outcome(check: Dict[str, Any]) -> str:
    """Return ``passed``, ``failed`` or ``pending`` for one run or status.

    An unknown completed conclusion is not a pass; it is reported as failed
    with its raw value so a human can decide whether to exempt it.
    """
    conclusion = str(check.get("conclusion") or "").upper()
    state = str(check.get("state") or "").upper()
    status = str(check.get("status") or "").upper()
    value = conclusion or state
    if value in FAILED:
        return "failed"
    if value in PASSED:
        return "passed"
    if value in PENDING:
        return "pending"
    if status and status != "COMPLETED":
        return "pending"
    if not value:
        return "pending"
    return "failed"


def latest_checks(checks: Iterable[Any]) -> List[Dict[str, Any]]:
    """Keep one run per check name: the one that completed, or started, last.

    A run still in progress has no completion time, so its start time is used.
    That lets a fresh re-run supersede the failure it was started to replace.
    When two runs carry no time at all, the later one in the list wins.
    """
    by_name: Dict[str, Any] = {}
    for check in checks or []:
        if not isinstance(check, dict):
            continue
        name = check_name(check)
        when = _timestamp(check.get("completedAt")) or _timestamp(check.get("startedAt"))
        previous = by_name.get(name)
        if previous is None or when >= previous[0]:
            by_name[name] = (when, check)
    return [check for _, check in by_name.values()]


def evaluate_checks(checks: Sequence[Any], exempt: Iterable[str] = ()) -> Dict[str, Any]:
    """Split the latest run per name into failed, pending, and exempted."""
    exempt_names = {name.strip() for name in exempt if isinstance(name, str) and name.strip()}
    latest = latest_checks(checks)
    failed: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []
    exempted: List[Dict[str, Any]] = []
    for check in latest:
        outcome = check_outcome(check)
        if outcome == "failed":
            if check_name(check) in exempt_names:
                exempted.append(check)
            else:
                failed.append(check)
        elif outcome == "pending":
            pending.append(check)
    counted = sum(1 for check in checks if isinstance(check, dict))
    return {
        "latest": latest,
        "failed": failed,
        "pending": pending,
        "exempted": exempted,
        "superseded": counted - len(latest),
    }


def _describe(check: Dict[str, Any]) -> str:
    value = check.get("conclusion") or check.get("state") or check.get("status") or "unknown"
    return f"{check_name(check)}: {value}"


def _reference(change: Dict[str, Any]) -> str:
    if change.get("url"):
        return str(change["url"])
    if change.get("ref"):
        return str(change["ref"])
    if change.get("number"):
        return f"#{change['number']}"
    return "change"


def evaluate_change(change: Dict[str, Any], exempt: Iterable[str] = ()) -> Dict[str, Any]:
    """Apply the gate to one change and return verdict, reasons, notes, exemptions."""
    result: Dict[str, Any] = {
        "ref": _reference(change),
        "title": change.get("title"),
        "author": (change.get("author") or {}).get("login") if isinstance(change.get("author"), dict) else change.get("author"),
        "state": None,
        "reviewDecision": None,
        "mergeable": None,
        "verdict": HOLD,
        "reasons": [],
        "notes": [],
        "exemptions": [],
        "checks": {"failed": [], "pending": [], "passed": 0},
    }
    if change.get("error"):
        result["reasons"].append({"code": UNVERIFIED, "detail": str(change["error"])})
        return result

    state = str(change.get("state") or "").upper()
    merged = state == "MERGED" or bool(change.get("mergedAt"))
    decision = str(change.get("reviewDecision") or "").upper()
    approved = decision == "APPROVED"
    draft = bool(change.get("isDraft"))
    mergeable = str(change.get("mergeable") or "").upper()
    merge_state = str(change.get("mergeStateStatus") or "").upper()

    result["state"] = "MERGED" if merged else (state or None)
    result["reviewDecision"] = decision or None
    result["mergeable"] = mergeable or None

    reasons: List[Dict[str, str]] = result["reasons"]
    notes: List[str] = result["notes"]
    checks = evaluate_checks(change.get("statusCheckRollup") or [], exempt)

    if merged:
        notes.append("merged; review axis passes")
    else:
        if state == "CLOSED":
            reasons.append({"code": PR_NOT_MERGEABLE, "detail": "closed without merge"})
        if draft:
            reasons.append({"code": PR_DRAFT, "detail": "draft"})
        if not approved:
            reasons.append({"code": PR_NOT_APPROVED, "detail": f"review decision {decision or 'none'}"})
        if mergeable == "CONFLICTING" or merge_state == "DIRTY":
            reasons.append({"code": PR_NOT_MERGEABLE, "detail": "conflicts with the base branch"})
        elif merge_state == "BEHIND":
            notes.append("behind the base branch; the host may require an update before merge")
        elif mergeable == "UNKNOWN" or merge_state == "UNKNOWN":
            notes.append("mergeability not yet computed by the host; fetch again")
        if checks["pending"]:
            reasons.append(
                {"code": CI_PENDING, "detail": "; ".join(_describe(check) for check in checks["pending"])}
            )

    if checks["failed"]:
        reasons.append({"code": CI_FAILED, "detail": "; ".join(_describe(check) for check in checks["failed"])})
    if merged and checks["pending"]:
        names = ", ".join(check_name(check) for check in checks["pending"])
        notes.append(f"pending checks ignored on a merged change: {names}")
    if checks["superseded"]:
        notes.append(
            f"{checks['superseded']} superseded check run(s) ignored; only the latest run per name was judged"
        )
    result["exemptions"] = [f"{_describe(check)} exempted as a declared non-blocking check" for check in checks["exempted"]]
    result["checks"] = {
        "failed": [_describe(check) for check in checks["failed"]],
        "pending": [_describe(check) for check in checks["pending"]],
        "passed": sum(1 for check in checks["latest"] if check_outcome(check) == "passed"),
    }
    result["verdict"] = APPROVABLE if not reasons else HOLD
    return result


def evaluate(changes: Any, exempt: Iterable[str] = ()) -> Dict[str, Any]:
    """Apply the gate to every change; one hold holds the whole request."""
    items = changes if isinstance(changes, list) else [changes]
    results = [evaluate_change(item, exempt) for item in items if isinstance(item, dict)]
    if not results:
        return {
            "verdict": HOLD,
            "reasons": [{"code": NO_PR, "detail": "no change supplied"}],
            "changes": [],
            "exemptions": [],
        }
    verdict = APPROVABLE if all(item["verdict"] == APPROVABLE for item in results) else HOLD
    exemptions = [line for item in results for line in item["exemptions"]]
    return {"verdict": verdict, "reasons": [], "changes": results, "exemptions": exemptions}


def render_table(result: Dict[str, Any]) -> str:
    """Markdown summary for the approval record; never paste it into chat."""
    lines = [
        "| Change | State | Review | Checks | Mergeable | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    for item in result.get("changes") or []:
        checks = item["checks"]
        if item["reasons"] and item["reasons"][0]["code"] == UNVERIFIED:
            check_text = "not fetched"
        elif checks["failed"]:
            check_text = "failed: " + ", ".join(checks["failed"])
        elif checks["pending"]:
            check_text = "pending: " + ", ".join(checks["pending"])
        else:
            check_text = f"{checks['passed']} passed"
        lines.append(
            f"| {item['ref']} | {item['state'] or '-'} | {item['reviewDecision'] or '-'} | {check_text} | "
            f"{item['mergeable'] or '-'} | {item['verdict']} |"
        )
    lines.append("")
    lines.append(f"Verdict: {result['verdict']}")
    reasons = [(item["ref"], reason) for item in result.get("changes") or [] for reason in item["reasons"]]
    reasons.extend(("request", reason) for reason in result.get("reasons") or [])
    for ref, reason in reasons:
        lines.append(f"- {reason['code']} ({ref}): {reason['detail']}")
    for line in result.get("exemptions") or []:
        lines.append(f"- exemption: {line}")
    return "\n".join(lines)


def _load(source: Optional[str]) -> Any:
    if not source or source == "-":
        return json.load(sys.stdin)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", nargs="?", help="JSON file with one change or an array; - or omitted reads stdin")
    parser.add_argument(
        "--exempt-check",
        action="append",
        default=[],
        metavar="NAME",
        help="check name the team has declared non-blocking; repeatable; every use is reported",
    )
    parser.add_argument("--markdown", action="store_true", help="print a markdown table instead of JSON")
    args = parser.parse_args(argv)
    try:
        data = _load(args.source)
    except (OSError, ValueError) as error:
        print(f"cannot read change JSON: {error}", file=sys.stderr)
        return 1
    result = evaluate(data, args.exempt_check)
    if args.markdown:
        print(render_table(result))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verdict"] == APPROVABLE else 2


if __name__ == "__main__":
    raise SystemExit(main())
