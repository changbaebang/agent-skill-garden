from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "parent-ticket-guard"
    / "scripts"
    / "guard_check.py"
)
SPEC = importlib.util.spec_from_file_location("guard_check", SCRIPT)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)

ME = "user-a"
OTHER = "user-b"


def facts(target: str, **overrides) -> dict:
    payload = {
        "current_user": ME,
        "working_issue": "CHILD-1",
        "target": target,
        "override": False,
        "issues": {
            "CHILD-1": {"owner": ME, "parent": "MID-1"},
            "MID-1": {"owner": ME, "parent": "TOP-1"},
            "TOP-1": {"owner": OTHER, "parent": None},
            "ELSEWHERE-9": {"owner": OTHER, "parent": None},
        },
    }
    payload.update(overrides)
    return payload


class TestGuardDecision(unittest.TestCase):
    def test_blocks_parent_owned_by_someone_else(self) -> None:
        decision, reason = GUARD.decide(facts("TOP-1"))
        self.assertEqual(decision, GUARD.BLOCK)
        self.assertIn("owned by someone else", reason)

    def test_allows_ancestor_owned_by_current_user(self) -> None:
        decision, _ = GUARD.decide(facts("MID-1"))
        self.assertEqual(decision, GUARD.ALLOW)

    def test_working_issue_itself_is_outside_the_guard(self) -> None:
        decision, _ = GUARD.decide(facts("CHILD-1"))
        self.assertEqual(decision, GUARD.OUTSIDE)

    def test_unrelated_issue_is_outside_the_guard(self) -> None:
        decision, _ = GUARD.decide(facts("ELSEWHERE-9"))
        self.assertEqual(decision, GUARD.OUTSIDE)

    def test_grandparent_is_checked_through_the_chain(self) -> None:
        payload = facts("TOP-1")
        payload["issues"]["MID-1"]["owner"] = OTHER
        decision, _ = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.BLOCK)

    def test_fails_closed_when_owner_is_missing(self) -> None:
        payload = facts("TOP-1")
        payload["issues"]["TOP-1"]["owner"] = None
        decision, reason = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.BLOCK)
        self.assertIn("no visible owner", reason)

    def test_fails_closed_when_current_user_is_unknown(self) -> None:
        decision, reason = GUARD.decide(facts("MID-1", current_user=""))
        self.assertEqual(decision, GUARD.BLOCK)
        self.assertIn("identity is unknown", reason)

    def test_fails_closed_when_ancestor_record_was_not_read(self) -> None:
        payload = facts("TOP-1")
        del payload["issues"]["TOP-1"]
        decision, reason = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.BLOCK)
        self.assertIn("no record", reason)

    def test_explicit_override_allows_with_a_warning(self) -> None:
        decision, reason = GUARD.decide(facts("TOP-1", override=True))
        self.assertEqual(decision, GUARD.ALLOW)
        self.assertIn("override", reason)

    def test_override_does_not_change_an_outside_decision(self) -> None:
        decision, _ = GUARD.decide(facts("ELSEWHERE-9", override=True))
        self.assertEqual(decision, GUARD.OUTSIDE)

    def test_owner_list_is_supported(self) -> None:
        payload = facts("TOP-1")
        payload["issues"]["TOP-1"]["owner"] = [OTHER, ME]
        decision, _ = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.ALLOW)

    def test_parent_cycle_terminates(self) -> None:
        payload = facts("TOP-1")
        payload["issues"]["TOP-1"]["parent"] = "CHILD-1"
        decision, _ = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.BLOCK)

    def test_display_name_is_not_matched_loosely(self) -> None:
        payload = facts("TOP-1")
        payload["issues"]["TOP-1"]["owner"] = "User-A"
        decision, _ = GUARD.decide(payload)
        self.assertEqual(decision, GUARD.BLOCK)


class TestInputValidation(unittest.TestCase):
    def test_rejects_missing_issues(self) -> None:
        with self.assertRaises(ValueError):
            GUARD.decide({"working_issue": "A-1", "target": "A-2"})

    def test_rejects_missing_target(self) -> None:
        with self.assertRaises(ValueError):
            GUARD.decide({"working_issue": "A-1", "issues": {}})

    def test_rejects_non_boolean_override(self) -> None:
        with self.assertRaises(ValueError):
            GUARD.decide(facts("TOP-1", override="yes"))

    def test_exit_codes_follow_decisions(self) -> None:
        self.assertEqual(GUARD.EXIT_CODES[GUARD.BLOCK], 2)
        self.assertEqual(GUARD.EXIT_CODES[GUARD.ALLOW], 0)
        self.assertEqual(GUARD.EXIT_CODES[GUARD.OUTSIDE], 0)


if __name__ == "__main__":
    unittest.main()
