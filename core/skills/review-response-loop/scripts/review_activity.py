#!/usr/bin/env python3
"""Turn pull-request review records into new-activity and loop-verdict lines.

The decision logic is kept free of network access so it can be tested directly.
Fetching belongs to the caller: pass the review and comment collections in, or
use ``--input`` with a JSON document holding them.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Iterable, Sequence

FINISHED = "finished"
NEW_FINDING = "new-finding"
AWAITING_REVIEWER = "awaiting-reviewer"
THREADS_OPEN = "threads-open"
UNDECIDED = "undecided"


@dataclass(frozen=True)
class Activity:
    kind: str
    author: str
    detail: str

    def render(self) -> str:
        return f"{self.kind} {self.author} {self.detail}".rstrip()


def _later_than(timestamp: str | None, mark: str | None) -> bool:
    # Timestamps arrive as UTC ISO-8601 strings, which compare correctly as
    # text. An absent timestamp is treated as older so a malformed record can
    # never manufacture a round.
    if not timestamp:
        return False
    if not mark:
        return True
    return timestamp > mark


def new_activity(
    reviews: Iterable[dict],
    comments: Iterable[dict],
    since: str | None,
    author: str,
    only_from: str | None = None,
) -> list[Activity]:
    """Collect review activity newer than ``since``, excluding the author.

    ``only_from`` narrows the result to one reviewer. While waiting on a
    specific reviewer this keeps an unrelated approval from ending the wait.
    """
    wanted = None if only_from is None else only_from
    found: list[Activity] = []

    for review in reviews:
        login = str(review.get("user", {}).get("login", ""))
        if login == author or (wanted is not None and login != wanted):
            continue
        if not _later_than(review.get("submitted_at"), since):
            continue
        found.append(Activity("review", login, str(review.get("state", ""))))

    for comment in comments:
        login = str(comment.get("user", {}).get("login", ""))
        if login == author or (wanted is not None and login != wanted):
            continue
        if not _later_than(comment.get("created_at"), since):
            continue
        location = f"{comment.get('path', '')}:{comment.get('line', '')}".strip(":")
        found.append(Activity("comment", login, location))

    return found


def loop_verdict(
    review_decision: str | None,
    unresolved_threads: int,
    awaited_reviewer_answered: bool | None = None,
    has_new_finding: bool = False,
) -> str:
    """Decide whether the loop may stop.

    ``awaited_reviewer_answered`` is ``None`` when no reviewer was re-requested.
    An approval with no unresolved threads is *not* an ending while a
    re-requested reviewer has still not answered: a reviewer who is not on the
    requested list can hold an open comment while the decision already reads as
    approved.
    """
    if has_new_finding:
        return NEW_FINDING
    if unresolved_threads > 0:
        return THREADS_OPEN
    if awaited_reviewer_answered is False:
        return AWAITING_REVIEWER
    if review_decision == "APPROVED":
        return FINISHED
    return UNDECIDED


def group_findings(comments: Sequence[dict], author: str) -> dict[str, list[dict]]:
    """Group reviewer comments by ``path:line``.

    Frequency alone cannot separate a round-trip from convergence, so each entry
    keeps the author and timestamp needed to compare rounds.
    """
    grouped: dict[str, list[dict]] = {}
    for comment in comments:
        login = str(comment.get("user", {}).get("login", ""))
        if login == author:
            continue
        location = f"{comment.get('path', '')}:{comment.get('line', '')}".strip(":")
        grouped.setdefault(location, []).append(
            {"author": login, "at": comment.get("created_at", "")}
        )
    return grouped


def classify_repetition(entries: Sequence[dict]) -> str:
    """Label one location as a round-trip, convergence, or a single finding."""
    if len(entries) < 2:
        return "single"
    authors = {entry.get("author", "") for entry in entries}
    if len(authors) > 1:
        return "convergence"
    return "round-trip"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON document, or - for stdin")
    parser.add_argument("--author", required=True, help="account whose writes are excluded")
    parser.add_argument("--since", default=None, help="UTC ISO-8601 mark")
    parser.add_argument("--only-from", default=None, help="limit to one reviewer")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
    payload = json.loads(raw)

    reviews = payload.get("reviews", [])
    comments = payload.get("comments", [])

    activity = new_activity(reviews, comments, args.since, args.author, args.only_from)
    for item in activity:
        print(item.render())

    verdict = loop_verdict(
        payload.get("review_decision"),
        int(payload.get("unresolved_threads", 0)),
        payload.get("awaited_reviewer_answered"),
        has_new_finding=any(item.kind == "comment" for item in activity),
    )
    print(f"verdict={verdict}")

    for location, entries in sorted(group_findings(comments, args.author).items()):
        label = classify_repetition(entries)
        if label != "single":
            print(f"{label} {location} ({len(entries)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
