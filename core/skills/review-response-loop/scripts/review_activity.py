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
from pathlib import Path
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
    is_finding: bool = False

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


def _comment_location(comment: dict) -> str:
    """Prefer the original line when a review comment is outdated."""
    line = comment.get("line")
    if line is None:
        line = comment.get("original_line", "")
    return f"{comment.get('path', '')}:{line}".strip(":")


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
        state = str(review.get("state") or "").upper()
        body = str(review.get("body") or "").strip()
        found.append(
            Activity(
                "review",
                login,
                state,
                is_finding=state == "CHANGES_REQUESTED"
                or (state == "COMMENTED" and bool(body)),
            )
        )

    for comment in comments:
        login = str(comment.get("user", {}).get("login", ""))
        if login == author or (wanted is not None and login != wanted):
            continue
        if not _later_than(comment.get("created_at"), since):
            continue
        found.append(
            Activity(
                "comment",
                login,
                _comment_location(comment),
                is_finding=comment.get("in_reply_to_id") is None,
            )
        )

    return found


def reviewer_answered(activity: Sequence[Activity], only_from: str | None) -> bool | None:
    """Return fail-closed answer state for a specifically awaited reviewer."""
    if only_from is None:
        return None
    return any(item.author == only_from for item in activity)


def has_new_finding(activity: Sequence[Activity]) -> bool:
    """Distinguish new findings from approvals and replies to existing threads."""
    return any(item.is_finding for item in activity)


def loop_verdict(
    review_decision: str | None,
    unresolved_threads: int,
    awaited_reviewer_answered: bool | None = None,
    has_new_finding: bool = False,
) -> str:
    """Decide whether the loop may stop.

    ``awaited_reviewer_answered`` comes from :func:`reviewer_answered` and is
    ``None`` when no reviewer was re-requested. An approval with no unresolved
    threads is *not* an ending while a re-requested reviewer has still not
    answered: a reviewer who is not on the requested list can hold an open
    comment while the decision already reads as approved.
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


def _round_for(timestamp: str | None, round_marks: Sequence[str]) -> str | None:
    """Return the latest request mark at or before an activity timestamp."""
    if not timestamp:
        return None
    eligible = [mark for mark in round_marks if mark and mark <= timestamp]
    return max(eligible, default=None)


def group_findings(
    comments: Sequence[dict],
    author: str,
    round_marks: Sequence[str] = (),
) -> dict[str, list[dict]]:
    """Group reviewer comments by ``path:line``.

    Frequency alone cannot separate a round-trip from convergence, so each entry
    keeps the author and timestamp needed to compare rounds.
    """
    grouped: dict[str, list[dict]] = {}
    for comment in comments:
        login = str(comment.get("user", {}).get("login", ""))
        if login == author or comment.get("in_reply_to_id") is not None:
            continue
        round_id = comment.get("round_id") or _round_for(
            comment.get("created_at"), round_marks
        )
        grouped.setdefault(_comment_location(comment), []).append(
            {
                "author": login,
                "at": comment.get("created_at", ""),
                "round": round_id,
            }
        )
    return grouped


def classify_repetition(entries: Sequence[dict]) -> str:
    """Label one location without guessing when round evidence is absent."""
    if len(entries) < 2:
        return "single"
    rounds = [entry.get("round") for entry in entries]
    if any(round_id is None for round_id in rounds):
        return "repeated"
    if len(set(rounds)) > 1:
        return "round-trip"
    authors = {entry.get("author", "") for entry in entries}
    if len(authors) > 1:
        return "convergence"
    return "repeated"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="JSON document, or - for stdin")
    parser.add_argument("--author", required=True, help="account whose writes are excluded")
    parser.add_argument("--since", default=None, help="UTC ISO-8601 mark")
    parser.add_argument("--only-from", default=None, help="limit to one reviewer")
    args = parser.parse_args(argv)
    if args.only_from is not None and args.since is None:
        parser.error("--since is required with --only-from")

    raw = (
        sys.stdin.read()
        if args.input == "-"
        else Path(args.input).read_text(encoding="utf-8")
    )
    payload = json.loads(raw)
    if "awaited_reviewer_answered" in payload:
        parser.error(
            "awaited_reviewer_answered is no longer read; pass --only-from "
            "REVIEWER and let the helper derive the answer state"
        )

    reviews = payload.get("reviews", [])
    comments = payload.get("comments", [])

    # Judge the verdict on every reviewer's activity. ``--only-from`` narrows
    # whose answer the loop is waiting for, not the evidence that a finding
    # arrived: narrowing both reports "finished" while another reviewer's fresh
    # finding sits unanswered in the same window.
    activity = new_activity(reviews, comments, args.since, args.author)
    for item in activity:
        print(item.render())

    verdict = loop_verdict(
        payload.get("review_decision"),
        int(payload.get("unresolved_threads", 0)),
        reviewer_answered(activity, args.only_from),
        has_new_finding=has_new_finding(activity),
    )
    print(f"verdict={verdict}")

    round_marks = payload.get("round_marks", [])
    for location, entries in sorted(
        group_findings(comments, args.author, round_marks).items()
    ):
        label = classify_repetition(entries)
        if label != "single":
            print(f"{label} {location} ({len(entries)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
