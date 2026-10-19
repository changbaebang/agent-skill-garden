#!/usr/bin/env python3
"""Decide whether a review request may be drafted and list who to mention.

Reads one JSON object describing a pull request on standard input (or from
--input). The expected fields follow the common code host "view" shape:

    state            "OPEN" | "MERGED" | "CLOSED"
    isDraft          true | false
    reviewDecision   "APPROVED" | "CHANGES_REQUESTED" | "REVIEW_REQUIRED" | ""
    author           {"login": ...}
    assignees        [{"login": ...}, ...]
    reviewRequests   [{"login": ...} | {"slug": ...} | {"name": ...}, ...]
    reviews          [{"author": {"login": ...}, "state": ..., "submittedAt": ...}, ...]
    number, url      used as the ledger key (url preferred)

Prints a result block and exits 0 for "proceed", 3 for "stop", 2 when the input
cannot be read. Nothing here sends a message; the ledger only remembers that
the user confirmed a send, when --record is passed after that send.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_BOT_MARKERS = ("[bot]", "dependabot", "renovate", "github-actions")

FILTER_NONE = "none"
FILTER_DRAFT = "draft"
FILTER_NOT_OPEN = "not_open"
FILTER_COMPLETE = "review_already_complete"
FILTER_DUPLICATE = "duplicate_request"

EXIT_PROCEED = 0
EXIT_INPUT = 2
EXIT_STOP = 3


def is_bot(login: str, extra_bots: Iterable[str] = ()) -> bool:
    lowered = login.lower()
    if lowered in {bot.lower() for bot in extra_bots}:
        return True
    if lowered.endswith("[bot]") or lowered.endswith("-bot"):
        return True
    return any(marker in lowered for marker in DEFAULT_BOT_MARKERS)


def login_of(entry: Any) -> Optional[str]:
    if isinstance(entry, str) and entry:
        return entry
    if isinstance(entry, dict):
        value = entry.get("login")
        if isinstance(value, str) and value:
            return value
    return None


def team_of(entry: Any) -> Optional[str]:
    if isinstance(entry, dict) and not entry.get("login"):
        for key in ("slug", "name"):
            value = entry.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _ordered_reviews(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    stamps = [review.get("submittedAt") for review in reviews]
    if stamps and all(isinstance(stamp, str) and stamp for stamp in stamps):
        return sorted(reviews, key=lambda review: review["submittedAt"])
    return list(reviews)


def standing_approvals(
    reviews: List[Dict[str, Any]], author: str, extra_bots: Iterable[str] = ()
) -> Dict[str, bool]:
    """Per human reviewer: does an approval still stand after their later reviews?

    An approval stands until the same reviewer requests changes or the approval
    is dismissed. Comments alone neither grant nor revoke it, but a reviewer who
    only commented has not approved.
    """
    standing: Dict[str, bool] = {}
    for review in _ordered_reviews([r for r in reviews if isinstance(r, dict)]):
        login = login_of(review.get("author"))
        if not login or login == author or is_bot(login, extra_bots):
            continue
        state = str(review.get("state") or "").upper()
        if state == "APPROVED":
            standing[login] = True
        elif state in {"CHANGES_REQUESTED", "DISMISSED"}:
            standing[login] = False
        else:
            standing.setdefault(login, False)
    return standing


def parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def ledger_key(pr: Dict[str, Any]) -> str:
    url = pr.get("url")
    if isinstance(url, str) and url:
        return url
    return str(pr.get("number", ""))


def load_ledger(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = data.get("sent", []) if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def recent_send(
    entries: List[Dict[str, Any]], key: str, window_hours: float, now: datetime
) -> Optional[str]:
    for entry in entries:
        if str(entry.get("pr")) != key:
            continue
        sent_at = parse_time(entry.get("at"))
        if sent_at is None:
            continue
        if timedelta(0) <= now - sent_at <= timedelta(hours=window_hours):
            return sent_at.isoformat()
    return None


def record_send(path: Path, key: str, now: datetime) -> None:
    entries = load_ledger(path)
    entries.append({"pr": key, "at": now.isoformat()})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sent": entries}, indent=2) + "\n", encoding="utf-8")


def evaluate(
    pr: Dict[str, Any],
    extra_bots: Iterable[str] = (),
    ledger: Optional[Path] = None,
    window_hours: float = 24.0,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    extra_bots = tuple(extra_bots)
    author = login_of(pr.get("author")) or ""
    state = str(pr.get("state") or "").upper()
    review_decision = str(pr.get("reviewDecision") or "").upper()
    requests = pr.get("reviewRequests") or []
    assignees = pr.get("assignees") or []
    reviews = pr.get("reviews") or []

    pending_users = [login for login in (login_of(e) for e in requests) if login]
    pending_teams = [team for team in (team_of(e) for e in requests) if team]
    assignee_logins = [login for login in (login_of(e) for e in assignees) if login]

    candidates: List[str] = []
    excluded: List[str] = []
    for login in pending_users + assignee_logins:
        if login == author:
            tag = f"author:{login}"
        elif is_bot(login, extra_bots):
            tag = f"bot:{login}"
        else:
            if login not in candidates:
                candidates.append(login)
            continue
        if tag not in excluded:
            excluded.append(tag)

    standing = standing_approvals(reviews, author, extra_bots)
    humans_all_approved = (
        bool(standing) and all(standing.values()) and not pending_users and not pending_teams
    )

    applied = FILTER_NONE
    reason = "Open, not a draft, and review is still outstanding."
    duplicate_at: Optional[str] = None
    if pr.get("isDraft") is True:
        applied, reason = FILTER_DRAFT, "The pull request is a draft; hold the request."
    elif state != "OPEN":
        applied, reason = FILTER_NOT_OPEN, f"The pull request is {state.lower() or 'not open'}."
    elif review_decision == "APPROVED":
        applied, reason = FILTER_COMPLETE, "The review decision is already approved."
    elif humans_all_approved:
        applied = FILTER_COMPLETE
        reason = "No review request is pending and every human reviewer's standing review is an approval."
    elif ledger is not None:
        duplicate_at = recent_send(load_ledger(ledger), ledger_key(pr), window_hours, now)
        if duplicate_at:
            applied = FILTER_DUPLICATE
            reason = f"A request for this pull request was recorded at {duplicate_at}."

    return {
        "action": "stop" if applied != FILTER_NONE else "proceed",
        "applied_filter": applied,
        "review_decision": review_decision,
        "mention_candidates": candidates,
        "team_requests": pending_teams,
        "excluded": excluded,
        "human_reviews_standing": standing,
        "duplicate_recorded_at": duplicate_at,
        "reason": reason,
    }


def render_text(result: Dict[str, Any]) -> str:
    lines = [
        f"action: {result['action']}",
        f"applied_filter: {result['applied_filter']}",
        f"review_decision: {result['review_decision'] or '(empty)'}",
        f"mention_candidates: {', '.join(result['mention_candidates']) or '(none)'}",
        f"team_requests: {', '.join(result['team_requests']) or '(none)'}",
        f"excluded: {', '.join(result['excluded']) or '(none)'}",
        f"reason: {result['reason']}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, help="read the pull request JSON from a file instead of stdin")
    parser.add_argument("--bot", action="append", default=[], help="an automation login to exclude (repeatable)")
    parser.add_argument("--ledger", type=Path, help="JSON file remembering confirmed sends")
    parser.add_argument("--window-hours", type=float, default=24.0, help="duplicate window for --ledger")
    parser.add_argument("--record", action="store_true", help="append this pull request to --ledger after a confirmed send")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)

    try:
        raw = args.input.read_text(encoding="utf-8") if args.input else sys.stdin.read()
        pr = json.loads(raw)
    except (OSError, ValueError) as error:
        print(f"ERROR: cannot read pull request JSON: {error}", file=sys.stderr)
        return EXIT_INPUT
    if not isinstance(pr, dict):
        print("ERROR: pull request JSON must be one object", file=sys.stderr)
        return EXIT_INPUT

    if args.record:
        if args.ledger is None:
            print("ERROR: --record needs --ledger", file=sys.stderr)
            return EXIT_INPUT
        record_send(args.ledger, ledger_key(pr), datetime.now(timezone.utc))
        print(f"recorded: {ledger_key(pr)}")
        return EXIT_PROCEED

    result = evaluate(pr, extra_bots=args.bot, ledger=args.ledger, window_hours=args.window_hours)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_text(result))
    return EXIT_PROCEED if result["action"] == "proceed" else EXIT_STOP


if __name__ == "__main__":
    raise SystemExit(main())
