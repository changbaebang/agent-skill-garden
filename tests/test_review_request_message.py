import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/review-request-message/scripts/review_request_gate.py"
SPEC = importlib.util.spec_from_file_location("review_request_gate", MODULE_PATH)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


def pr(**overrides):
    base = {
        "number": 42,
        "url": "https://example.invalid/repo/pull/42",
        "state": "OPEN",
        "isDraft": False,
        "reviewDecision": "REVIEW_REQUIRED",
        "author": {"login": "author-one"},
        "assignees": [],
        "reviewRequests": [{"login": "reviewer-a"}],
        "reviews": [],
    }
    base.update(overrides)
    return base


class GateTest(unittest.TestCase):
    def test_open_pull_request_awaiting_review_proceeds(self) -> None:
        result = GATE.evaluate(pr(), now=NOW)
        self.assertEqual(result["action"], "proceed")
        self.assertEqual(result["applied_filter"], GATE.FILTER_NONE)

    def test_draft_stops_before_anything_else(self) -> None:
        result = GATE.evaluate(pr(isDraft=True, state="MERGED"), now=NOW)
        self.assertEqual(result["applied_filter"], GATE.FILTER_DRAFT)

    def test_merged_or_closed_stops(self) -> None:
        for state in ("MERGED", "CLOSED"):
            result = GATE.evaluate(pr(state=state), now=NOW)
            self.assertEqual(result["applied_filter"], GATE.FILTER_NOT_OPEN, state)

    def test_approved_decision_stops(self) -> None:
        result = GATE.evaluate(pr(reviewDecision="APPROVED"), now=NOW)
        self.assertEqual(result["applied_filter"], GATE.FILTER_COMPLETE)

    def test_all_humans_approved_with_nothing_pending_stops(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewDecision="",
                reviewRequests=[],
                reviews=[
                    {"author": {"login": "reviewer-a"}, "state": "APPROVED"},
                    {"author": {"login": "reviewer-b"}, "state": "APPROVED"},
                    {"author": {"login": "checks-bot[bot]"}, "state": "COMMENTED"},
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["applied_filter"], GATE.FILTER_COMPLETE)

    def test_approval_followed_by_comment_still_stands(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewDecision="",
                reviewRequests=[],
                reviews=[
                    {"author": {"login": "reviewer-a"}, "state": "APPROVED", "submittedAt": "2026-01-09T10:00:00Z"},
                    {"author": {"login": "reviewer-a"}, "state": "COMMENTED", "submittedAt": "2026-01-09T11:00:00Z"},
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["applied_filter"], GATE.FILTER_COMPLETE)

    def test_changes_requested_after_approval_revokes_it(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewDecision="",
                reviewRequests=[],
                reviews=[
                    {"author": {"login": "reviewer-a"}, "state": "APPROVED", "submittedAt": "2026-01-09T10:00:00Z"},
                    {"author": {"login": "reviewer-a"}, "state": "CHANGES_REQUESTED", "submittedAt": "2026-01-09T11:00:00Z"},
                ],
            ),
            now=NOW,
        )
        self.assertEqual(result["action"], "proceed")

    def test_pending_request_keeps_the_review_open(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewDecision="",
                reviewRequests=[{"login": "reviewer-c"}],
                reviews=[{"author": {"login": "reviewer-a"}, "state": "APPROVED"}],
            ),
            now=NOW,
        )
        self.assertEqual(result["action"], "proceed")

    def test_comment_only_reviewer_is_not_an_approval(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewDecision="",
                reviewRequests=[],
                reviews=[{"author": {"login": "reviewer-a"}, "state": "COMMENTED"}],
            ),
            now=NOW,
        )
        self.assertEqual(result["action"], "proceed")


class MentionCandidateTest(unittest.TestCase):
    def test_excludes_author_and_bots_and_deduplicates(self) -> None:
        result = GATE.evaluate(
            pr(
                reviewRequests=[
                    {"login": "reviewer-a"},
                    {"login": "dependabot[bot]"},
                    {"login": "author-one"},
                    {"slug": "platform-reviewers"},
                ],
                assignees=[{"login": "reviewer-a"}, {"login": "reviewer-b"}, {"login": "deploy-bot"}],
            ),
            extra_bots=["deploy-bot"],
            now=NOW,
        )
        self.assertEqual(result["mention_candidates"], ["reviewer-a", "reviewer-b"])
        self.assertEqual(result["team_requests"], ["platform-reviewers"])
        self.assertEqual(result["excluded"], ["bot:dependabot[bot]", "author:author-one", "bot:deploy-bot"])

    def test_no_reviewer_and_no_assignee_yields_empty_candidates(self) -> None:
        result = GATE.evaluate(pr(reviewRequests=[], assignees=[]), now=NOW)
        self.assertEqual(result["action"], "proceed")
        self.assertEqual(result["mention_candidates"], [])


class LedgerTest(unittest.TestCase):
    def test_recent_send_is_a_duplicate_and_old_send_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.json"
            GATE.record_send(ledger, "https://example.invalid/repo/pull/42", NOW - timedelta(hours=2))
            recent = GATE.evaluate(pr(), ledger=ledger, now=NOW)
            self.assertEqual(recent["applied_filter"], GATE.FILTER_DUPLICATE)
            old = GATE.evaluate(pr(), ledger=ledger, window_hours=1, now=NOW)
            self.assertEqual(old["action"], "proceed")

    def test_missing_ledger_file_means_no_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = GATE.evaluate(pr(), ledger=Path(tmp) / "absent.json", now=NOW)
            self.assertEqual(result["action"], "proceed")

    def test_record_appends_without_losing_earlier_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "nested" / "ledger.json"
            GATE.record_send(ledger, "first", NOW)
            GATE.record_send(ledger, "second", NOW)
            entries = GATE.load_ledger(ledger)
            self.assertEqual([entry["pr"] for entry in entries], ["first", "second"])

    def test_timestamp_with_zulu_suffix_parses_on_python_3_9(self) -> None:
        parsed = GATE.parse_time("2026-01-09T10:00:00Z")
        self.assertEqual(parsed, datetime(2026, 1, 9, 10, 0, tzinfo=timezone.utc))


class CommandLineTest(unittest.TestCase):
    def run_cli(self, payload, *args):
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )

    def test_proceed_exits_zero_with_text_block(self) -> None:
        completed = self.run_cli(pr())
        self.assertEqual(completed.returncode, GATE.EXIT_PROCEED, completed.stderr)
        self.assertIn("action: proceed", completed.stdout)
        self.assertIn("mention_candidates: reviewer-a", completed.stdout)

    def test_stop_exits_three_and_json_flag_emits_object(self) -> None:
        completed = self.run_cli(pr(isDraft=True), "--json")
        self.assertEqual(completed.returncode, GATE.EXIT_STOP)
        self.assertEqual(json.loads(completed.stdout)["applied_filter"], GATE.FILTER_DRAFT)

    def test_invalid_input_exits_two(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH)], input="not json", text=True, capture_output=True
        )
        self.assertEqual(completed.returncode, GATE.EXIT_INPUT)

    def test_record_requires_ledger(self) -> None:
        completed = self.run_cli(pr(), "--record")
        self.assertEqual(completed.returncode, GATE.EXIT_INPUT)


if __name__ == "__main__":
    unittest.main()
