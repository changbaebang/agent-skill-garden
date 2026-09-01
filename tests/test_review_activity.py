from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "review-response-loop"
    / "scripts"
    / "review_activity.py"
)
SPEC = importlib.util.spec_from_file_location("review_activity", SCRIPT)
assert SPEC and SPEC.loader
REVIEW_ACTIVITY = importlib.util.module_from_spec(SPEC)
# Register before executing: the module defines a dataclass, and dataclasses
# resolve postponed annotations through sys.modules.
sys.modules[SPEC.name] = REVIEW_ACTIVITY
SPEC.loader.exec_module(REVIEW_ACTIVITY)


def review(login: str, state: str, at: str) -> dict:
    return {"user": {"login": login}, "state": state, "submitted_at": at}


def comment(login: str, path: str, line: int, at: str) -> dict:
    return {"user": {"login": login}, "path": path, "line": line, "created_at": at}


class NewActivityTests(unittest.TestCase):
    def test_excludes_the_author_own_writes(self) -> None:
        reviews = [review("author", "COMMENTED", "2026-01-01T00:01:00Z")]
        found = REVIEW_ACTIVITY.new_activity(reviews, [], "2026-01-01T00:00:00Z", "author")
        self.assertEqual(found, [])

    def test_excludes_activity_at_or_before_the_mark(self) -> None:
        reviews = [review("other", "APPROVED", "2026-01-01T00:00:00Z")]
        found = REVIEW_ACTIVITY.new_activity(reviews, [], "2026-01-01T00:00:00Z", "author")
        self.assertEqual(found, [])

    def test_reports_reviews_and_comments_after_the_mark(self) -> None:
        found = REVIEW_ACTIVITY.new_activity(
            [review("other", "APPROVED", "2026-01-01T00:02:00Z")],
            [comment("other", "a/b.ts", 12, "2026-01-01T00:03:00Z")],
            "2026-01-01T00:00:00Z",
            "author",
        )
        self.assertEqual(
            [item.render() for item in found],
            ["review other APPROVED", "comment other a/b.ts:12"],
        )

    def test_only_from_ignores_an_unrelated_approval(self) -> None:
        # A watch that stops on any activity is consumed by someone else's
        # approval before the awaited reviewer answers.
        found = REVIEW_ACTIVITY.new_activity(
            [
                review("bystander", "APPROVED", "2026-01-01T00:02:00Z"),
                review("awaited", "COMMENTED", "2026-01-01T00:04:00Z"),
            ],
            [],
            "2026-01-01T00:00:00Z",
            "author",
            only_from="awaited",
        )
        self.assertEqual([item.author for item in found], ["awaited"])

    def test_missing_timestamp_is_treated_as_older(self) -> None:
        reviews = [{"user": {"login": "other"}, "state": "APPROVED"}]
        found = REVIEW_ACTIVITY.new_activity(reviews, [], "2026-01-01T00:00:00Z", "author")
        self.assertEqual(found, [])


class LoopVerdictTests(unittest.TestCase):
    def test_approved_and_settled_finishes(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 0, None), REVIEW_ACTIVITY.FINISHED
        )

    def test_approved_does_not_finish_while_a_reviewer_is_awaited(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 0, False),
            REVIEW_ACTIVITY.AWAITING_REVIEWER,
        )

    def test_awaited_reviewer_answered_allows_the_finish(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 0, True), REVIEW_ACTIVITY.FINISHED
        )

    def test_open_threads_outrank_an_approval(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 2, None), REVIEW_ACTIVITY.THREADS_OPEN
        )

    def test_a_new_finding_outranks_everything(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 0, True, has_new_finding=True),
            REVIEW_ACTIVITY.NEW_FINDING,
        )

    def test_without_an_approval_the_loop_is_undecided(self) -> None:
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("REVIEW_REQUIRED", 0, None),
            REVIEW_ACTIVITY.UNDECIDED,
        )


class RepetitionTests(unittest.TestCase):
    def test_one_reviewer_across_rounds_is_a_round_trip(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z"},
            {"author": "one", "at": "2026-01-02T00:00:00Z"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "round-trip")

    def test_several_reviewers_are_convergence(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z"},
            {"author": "two", "at": "2026-01-01T00:01:00Z"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "convergence")

    def test_a_single_finding_is_neither(self) -> None:
        entries = [{"author": "one", "at": "2026-01-01T00:00:00Z"}]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "single")

    def test_grouping_drops_the_author_own_comments(self) -> None:
        grouped = REVIEW_ACTIVITY.group_findings(
            [
                comment("author", "a/b.ts", 1, "2026-01-01T00:00:00Z"),
                comment("other", "a/b.ts", 1, "2026-01-01T00:01:00Z"),
            ],
            "author",
        )
        self.assertEqual(grouped, {"a/b.ts:1": [{"author": "other", "at": "2026-01-01T00:01:00Z"}]})


if __name__ == "__main__":
    unittest.main()
