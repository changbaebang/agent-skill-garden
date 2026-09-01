from __future__ import annotations

import io
import importlib.util
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


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


def review(login: str, state: str, at: str, body: str = "") -> dict:
    return {
        "user": {"login": login},
        "state": state,
        "submitted_at": at,
        "body": body,
    }


def comment(
    login: str,
    path: str,
    line: int | None,
    at: str,
    *,
    reply_to: int | None = None,
    round_id: str | None = None,
    original_line: int | None = None,
) -> dict:
    record = {
        "user": {"login": login},
        "path": path,
        "line": line,
        "created_at": at,
    }
    if reply_to is not None:
        record["in_reply_to_id"] = reply_to
    if round_id is not None:
        record["round_id"] = round_id
    if original_line is not None:
        record["original_line"] = original_line
    return record


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

    def test_uses_original_line_for_an_outdated_comment(self) -> None:
        found = REVIEW_ACTIVITY.new_activity(
            [],
            [
                comment(
                    "other",
                    "a/b.ts",
                    None,
                    "2026-01-01T00:01:00Z",
                    original_line=27,
                )
            ],
            "2026-01-01T00:00:00Z",
            "author",
        )
        self.assertEqual([item.render() for item in found], ["comment other a/b.ts:27"])


class ActivityMeaningTests(unittest.TestCase):
    def test_silent_awaited_reviewer_is_fail_closed(self) -> None:
        self.assertFalse(REVIEW_ACTIVITY.reviewer_answered([], "awaited"))

    def test_no_awaited_reviewer_has_no_answer_requirement(self) -> None:
        self.assertIsNone(REVIEW_ACTIVITY.reviewer_answered([], None))

    def test_approval_and_thread_reply_are_not_a_new_finding(self) -> None:
        activity = REVIEW_ACTIVITY.new_activity(
            [review("awaited", "APPROVED", "2026-01-01T00:02:00Z")],
            [
                comment(
                    "awaited",
                    "a/b.ts",
                    12,
                    "2026-01-01T00:01:00Z",
                    reply_to=42,
                )
            ],
            "2026-01-01T00:00:00Z",
            "author",
            only_from="awaited",
        )
        self.assertTrue(REVIEW_ACTIVITY.reviewer_answered(activity, "awaited"))
        self.assertFalse(REVIEW_ACTIVITY.has_new_finding(activity))
        self.assertEqual(
            REVIEW_ACTIVITY.loop_verdict("APPROVED", 0, True, False),
            REVIEW_ACTIVITY.FINISHED,
        )

    def test_root_comment_is_a_new_finding(self) -> None:
        activity = REVIEW_ACTIVITY.new_activity(
            [],
            [comment("reviewer", "a/b.ts", 12, "2026-01-01T00:01:00Z")],
            "2026-01-01T00:00:00Z",
            "author",
        )
        self.assertTrue(REVIEW_ACTIVITY.has_new_finding(activity))

    def test_changes_requested_review_is_a_new_finding(self) -> None:
        activity = REVIEW_ACTIVITY.new_activity(
            [review("reviewer", "CHANGES_REQUESTED", "2026-01-01T00:01:00Z")],
            [],
            "2026-01-01T00:00:00Z",
            "author",
        )
        self.assertTrue(REVIEW_ACTIVITY.has_new_finding(activity))

    def test_commented_review_body_is_a_new_finding(self) -> None:
        activity = REVIEW_ACTIVITY.new_activity(
            [
                review(
                    "reviewer",
                    "COMMENTED",
                    "2026-01-01T00:01:00Z",
                    body="Please revisit the fallback.",
                )
            ],
            [],
            "2026-01-01T00:00:00Z",
            "author",
        )
        self.assertTrue(REVIEW_ACTIVITY.has_new_finding(activity))


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
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": "r1"},
            {"author": "one", "at": "2026-01-02T00:00:00Z", "round": "r2"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "round-trip")

    def test_several_reviewers_are_convergence(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": "r1"},
            {"author": "two", "at": "2026-01-01T00:01:00Z", "round": "r1"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "convergence")

    def test_a_single_finding_is_neither(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": "r1"}
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "single")

    def test_different_reviewers_across_rounds_are_a_round_trip(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": "r1"},
            {"author": "two", "at": "2026-01-02T00:00:00Z", "round": "r2"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "round-trip")

    def test_same_reviewer_in_one_round_is_only_repeated(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": "r1"},
            {"author": "one", "at": "2026-01-01T00:01:00Z", "round": "r1"},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "repeated")

    def test_missing_round_evidence_is_only_repeated(self) -> None:
        entries = [
            {"author": "one", "at": "2026-01-01T00:00:00Z", "round": None},
            {"author": "two", "at": "2026-01-01T00:01:00Z", "round": None},
        ]
        self.assertEqual(REVIEW_ACTIVITY.classify_repetition(entries), "repeated")

    def test_grouping_drops_the_author_own_comments(self) -> None:
        grouped = REVIEW_ACTIVITY.group_findings(
            [
                comment("author", "a/b.ts", 1, "2026-01-01T00:00:00Z"),
                comment("other", "a/b.ts", 1, "2026-01-01T00:01:00Z"),
            ],
            "author",
            ["2026-01-01T00:00:30Z"],
        )
        self.assertEqual(
            grouped,
            {
                "a/b.ts:1": [
                    {
                        "author": "other",
                        "at": "2026-01-01T00:01:00Z",
                        "round": "2026-01-01T00:00:30Z",
                    }
                ]
            },
        )

    def test_grouping_drops_replies_from_repetition_counts(self) -> None:
        grouped = REVIEW_ACTIVITY.group_findings(
            [
                comment("reviewer", "a/b.ts", 1, "2026-01-01T00:01:00Z"),
                comment(
                    "reviewer",
                    "a/b.ts",
                    1,
                    "2026-01-01T00:02:00Z",
                    reply_to=42,
                ),
            ],
            "author",
            ["2026-01-01T00:00:30Z"],
        )
        self.assertEqual(len(grouped["a/b.ts:1"]), 1)


class CliTests(unittest.TestCase):
    def run_cli(self, payload: dict, *args: str) -> list[str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))):
                result = REVIEW_ACTIVITY.main(["--input", "-", "--author", "author", *args])
        self.assertEqual(result, 0)
        return stdout.getvalue().splitlines()

    def test_silent_awaited_reviewer_does_not_finish(self) -> None:
        lines = self.run_cli(
            {
                "reviews": [],
                "comments": [],
                "review_decision": "APPROVED",
                "unresolved_threads": 0,
            },
            "--since",
            "2026-01-01T00:00:00Z",
            "--only-from",
            "awaited",
        )
        self.assertIn("verdict=awaiting-reviewer", lines)

    def test_reply_and_approval_finish_the_wait(self) -> None:
        lines = self.run_cli(
            {
                "reviews": [
                    review("awaited", "APPROVED", "2026-01-01T00:02:00Z")
                ],
                "comments": [
                    comment(
                        "awaited",
                        "a/b.ts",
                        12,
                        "2026-01-01T00:01:00Z",
                        reply_to=42,
                    )
                ],
                "review_decision": "APPROVED",
                "unresolved_threads": 0,
            },
            "--since",
            "2026-01-01T00:00:00Z",
            "--only-from",
            "awaited",
        )
        self.assertIn("verdict=finished", lines)
        self.assertNotIn("verdict=new-finding", lines)

    def test_only_from_still_reports_another_reviewer_finding(self) -> None:
        # --only-from names whose answer is awaited. Narrowing the evidence too
        # would finish the loop while a fresh finding sat unanswered: a
        # top-level commented review opens no thread, so unresolved_threads and
        # an already-approved decision cannot catch it either.
        lines = self.run_cli(
            {
                "reviews": [
                    review("awaited", "APPROVED", "2026-01-01T00:01:00Z"),
                    review(
                        "bystander",
                        "COMMENTED",
                        "2026-01-01T00:02:00Z",
                        body="this leaks a handle",
                    ),
                ],
                "comments": [],
                "review_decision": "APPROVED",
                "unresolved_threads": 0,
            },
            "--since",
            "2026-01-01T00:00:00Z",
            "--only-from",
            "awaited",
        )
        self.assertIn("verdict=new-finding", lines)
        self.assertIn("review bystander COMMENTED", lines)

    def test_retired_answered_flag_is_rejected(self) -> None:
        # The key used to decide the verdict. Ignoring it silently would flip
        # awaiting-reviewer into finished on an unchanged document.
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                self.run_cli(
                    {
                        "reviews": [],
                        "comments": [],
                        "review_decision": "APPROVED",
                        "unresolved_threads": 0,
                        "awaited_reviewer_answered": False,
                    }
                )
        self.assertIn("awaited_reviewer_answered is no longer read", stderr.getvalue())

    def test_only_from_requires_a_since_mark(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit):
                REVIEW_ACTIVITY.main(
                    ["--input", "-", "--author", "author", "--only-from", "awaited"]
                )
        self.assertIn("--since is required with --only-from", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
