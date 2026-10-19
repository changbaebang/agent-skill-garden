from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/ticket-lifecycle/scripts/check_ticket_fields.py"
SPEC = importlib.util.spec_from_file_location("check_ticket_fields", MODULE_PATH)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)


def default_contract(**overrides) -> "CHECKER.Contract":
    values = {
        "scale": CHECKER.DEFAULT_SCALE,
        "cap": CHECKER.DEFAULT_CAP,
        "estimate_step": CHECKER.DEFAULT_ESTIMATE_STEP,
        "actual_step": CHECKER.DEFAULT_ACTUAL_STEP,
    }
    values.update(overrides)
    return CHECKER.Contract(**values)


def complete_leaf(**overrides) -> dict:
    ticket = {
        "parent": "parent-key",
        "story_points": 3,
        "start_date": "2026-03-02",
        "due_date": "2026-03-06",
        "estimate_effort": 0.5,
        "actual_effort": 0.625,
    }
    ticket.update(overrides)
    return ticket


def failures(findings) -> dict:
    return {item.field: item.message for item in findings if item.level == "FAIL"}


def warnings(findings) -> dict:
    return {item.field: item.message for item in findings if item.level == "WARN"}


class RequiredFieldsByStateTest(unittest.TestCase):
    """Each state has its own required set; the checker must not over- or under-ask."""

    def test_complete_done_leaf_has_no_failures(self) -> None:
        findings = CHECKER.check(complete_leaf(), "done", default_contract())
        self.assertEqual(failures(findings), {})

    def test_done_requires_actual_effort(self) -> None:
        ticket = complete_leaf()
        del ticket["actual_effort"]
        findings = CHECKER.check(ticket, "done", default_contract())
        self.assertIn("actual_effort", failures(findings))

    def test_actual_effort_zero_is_a_value(self) -> None:
        findings = CHECKER.check(complete_leaf(actual_effort=0), "done", default_contract())
        self.assertEqual(failures(findings), {})

    def test_create_does_not_require_actual_effort(self) -> None:
        ticket = complete_leaf()
        del ticket["actual_effort"]
        findings = CHECKER.check(ticket, "create", default_contract())
        self.assertEqual(failures(findings), {})

    def test_backlog_may_leave_dates_empty(self) -> None:
        ticket = {"parent": "parent-key"}
        findings = CHECKER.check(ticket, "backlog", default_contract())
        self.assertEqual(failures(findings), {})
        self.assertIn("story_points", warnings(findings))
        self.assertIn("estimate_effort", warnings(findings))

    def test_in_progress_requires_dates(self) -> None:
        ticket = complete_leaf(start_date=None, due_date="")
        del ticket["actual_effort"]
        findings = CHECKER.check(ticket, "in-progress", default_contract())
        self.assertIn("start_date", failures(findings))
        self.assertIn("due_date", failures(findings))

    def test_in_progress_sprint_only_when_required(self) -> None:
        ticket = complete_leaf()
        del ticket["actual_effort"]
        relaxed = CHECKER.check(ticket, "in-progress", default_contract())
        strict = CHECKER.check(ticket, "in-progress", default_contract(require_sprint=True))
        self.assertNotIn("sprint", failures(relaxed))
        self.assertIn("sprint", failures(strict))

    def test_parent_is_always_required(self) -> None:
        for state in CHECKER.STATES:
            ticket = complete_leaf(parent=" ")
            findings = CHECKER.check(ticket, state, default_contract())
            self.assertIn("parent", failures(findings), state)

    def test_unknown_state_is_a_failure(self) -> None:
        findings = CHECKER.check(complete_leaf(), "shipped", default_contract())
        self.assertIn("state", failures(findings))


class PointsTest(unittest.TestCase):
    def test_points_over_cap_demand_a_split(self) -> None:
        findings = CHECKER.check(complete_leaf(story_points=8), "create", default_contract())
        self.assertIn("split", failures(findings)["story_points"])

    def test_points_off_scale_are_rejected(self) -> None:
        findings = CHECKER.check(complete_leaf(story_points=2), "create", default_contract())
        self.assertIn("not on the scale", failures(findings)["story_points"])

    def test_points_must_be_integers(self) -> None:
        findings = CHECKER.check(complete_leaf(story_points=2.5), "create", default_contract())
        self.assertIn("story_points", failures(findings))

    def test_custom_scale_and_cap_are_honored(self) -> None:
        contract = default_contract(scale=(1, 2, 3, 5, 8), cap=8)
        findings = CHECKER.check(complete_leaf(story_points=8), "create", contract)
        self.assertEqual(failures(findings), {})


class EffortStepsTest(unittest.TestCase):
    """Estimate and actual follow different granularity rules."""

    def test_estimate_off_its_step_fails_while_same_actual_passes(self) -> None:
        contract = default_contract()
        estimate = CHECKER.check(complete_leaf(estimate_effort=0.375), "done", contract)
        actual = CHECKER.check(complete_leaf(actual_effort=0.375), "done", contract)
        self.assertIn("estimate_effort", failures(estimate))
        self.assertEqual(failures(actual), {})

    def test_estimate_must_be_above_zero(self) -> None:
        findings = CHECKER.check(complete_leaf(estimate_effort=0), "create", default_contract())
        self.assertIn("above zero", failures(findings)["estimate_effort"])

    def test_effort_accepts_numeric_strings(self) -> None:
        findings = CHECKER.check(
            complete_leaf(estimate_effort="1.5", actual_effort="1.125"), "done", default_contract()
        )
        self.assertEqual(failures(findings), {})

    def test_actual_before_done_is_only_a_warning(self) -> None:
        findings = CHECKER.check(complete_leaf(), "in-progress", default_contract())
        self.assertNotIn("actual_effort", failures(findings))
        self.assertIn("actual_effort", warnings(findings))

    def test_on_step_uses_exact_decimal_arithmetic(self) -> None:
        self.assertTrue(CHECKER.on_step(Decimal("0.625"), Decimal("0.125")))
        self.assertFalse(CHECKER.on_step(Decimal("0.6"), Decimal("0.125")))
        self.assertFalse(CHECKER.on_step(Decimal("1"), Decimal("0")))


class DatesTest(unittest.TestCase):
    def test_due_before_start_fails(self) -> None:
        findings = CHECKER.check(
            complete_leaf(start_date="2026-03-06", due_date="2026-03-02"), "create", default_contract()
        )
        self.assertEqual(failures(findings)["due_date"], "before start_date")

    def test_malformed_date_fails(self) -> None:
        findings = CHECKER.check(complete_leaf(start_date="03/02/2026"), "create", default_contract())
        self.assertIn("start_date", failures(findings))


class ContainerTest(unittest.TestCase):
    def test_container_with_points_is_double_counting(self) -> None:
        ticket = {"parent": "parent-key", "container": True, "story_points": 8}
        findings = CHECKER.check(ticket, "create", default_contract())
        self.assertIn("story_points", failures(findings))

    def test_container_without_points_and_leaves_within_cap_passes(self) -> None:
        ticket = {
            "parent": "parent-key",
            "container": True,
            "leaves": [{"key": "first", "story_points": 5}, {"key": "second", "story_points": 3}],
        }
        findings = CHECKER.check(ticket, "create", default_contract())
        self.assertEqual(failures(findings), {})
        self.assertIn("8 points", {item.field: item.message for item in findings}["leaves"])

    def test_container_leaf_over_cap_fails(self) -> None:
        ticket = {"parent": "parent-key", "container": True, "leaves": [{"key": "big", "story_points": 8}]}
        findings = CHECKER.check(ticket, "create", default_contract())
        self.assertIn("leaves.big", failures(findings))

    def test_container_skips_leaf_only_fields(self) -> None:
        ticket = {"parent": "parent-key", "container": True, "leaves": [{"key": "a", "story_points": 1}]}
        findings = CHECKER.check(ticket, "done", default_contract())
        self.assertEqual(failures(findings), {})


class CommandLineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_checker(self, ticket: dict, *arguments: str) -> subprocess.CompletedProcess:
        path = self.root / "ticket.json"
        path.write_text(json.dumps(ticket), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *arguments, str(path)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_exit_code_follows_failures(self) -> None:
        complete = self.run_checker(complete_leaf(), "--state", "done")
        self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
        ticket = complete_leaf()
        del ticket["actual_effort"]
        missing = self.run_checker(ticket, "--state", "done")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("actual_effort", missing.stdout)

    def test_state_defaults_to_ticket_field(self) -> None:
        ticket = complete_leaf(state="done")
        del ticket["actual_effort"]
        result = self.run_checker(ticket)
        self.assertEqual(result.returncode, 1)
        self.assertIn("State: done", result.stdout)

    def test_json_output_is_parseable(self) -> None:
        result = self.run_checker(complete_leaf(), "--state", "done", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["state"], "done")
        self.assertEqual(payload["summary"]["FAIL"], 0)

    def test_scale_flag_overrides_default(self) -> None:
        result = self.run_checker(complete_leaf(story_points=8), "--scale", "1,2,3,5,8", "--cap", "8")
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_unreadable_ticket_is_a_usage_error(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), str(self.root / "missing.json")],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
