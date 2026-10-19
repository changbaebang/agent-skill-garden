import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/deployment-approval-ticket/scripts/check_ticket_body.py"
SPEC = importlib.util.spec_from_file_location("check_ticket_body", MODULE_PATH)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECK
SPEC.loader.exec_module(CHECK)

REQUIRED = ["First approver checklist", "Second approver checklist"]

VALID_BODY = """# Deployment review

### Schedule

- Deployment date: 2026-03-04

### First approver checklist

- **Target and scope**: web storefront, production, one deploy unit
- Rollback: feature flag off / owner: release engineer on duty

### Second approver checklist

- Reason second approval applies: not applicable
- Why now: scheduled release window

### Post-deploy checklist

- [ ] page loads
"""


def failures(findings):
    return [finding for finding in findings if finding.level == "FAIL"]


class HeadingRulesTest(unittest.TestCase):
    def test_valid_body_passes(self) -> None:
        findings = CHECK.check(VALID_BODY, REQUIRED)
        self.assertEqual(failures(findings), [])
        self.assertEqual({f.subject for f in findings if f.level == "PASS"}, set(REQUIRED))

    def test_near_miss_heading_is_reported_with_the_candidate(self) -> None:
        body = VALID_BODY.replace("### Second approver checklist", "### Second approver checklist (example)")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].subject, "Second approver checklist")
        self.assertIn("near miss", findings[0].message)
        self.assertIn("(example)", findings[0].message)

    def test_case_and_spacing_differences_are_not_exact(self) -> None:
        body = VALID_BODY.replace("### First approver checklist", "### First Approver  Checklist")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual([f.subject for f in findings], ["First approver checklist"])
        self.assertIn("near miss", findings[0].message)

    def test_missing_heading_without_near_miss(self) -> None:
        body = VALID_BODY.replace("### Second approver checklist\n", "### Something else\n")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].message, "heading missing")

    def test_sentence_between_heading_and_list_fails(self) -> None:
        body = VALID_BODY.replace(
            "### First approver checklist\n\n- ",
            "### First approver checklist\n\nAnswers follow.\n\n- ",
        )
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual(len(findings), 1)
        self.assertIn("not a list item", findings[0].message)

    def test_heading_with_nothing_after_it_fails(self) -> None:
        body = VALID_BODY.split("### Second approver checklist")[0] + "### Second approver checklist\n"
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual([f.message for f in findings], ["nothing follows the heading"])

    def test_duplicate_heading_fails(self) -> None:
        body = VALID_BODY + "\n### First approver checklist\n\n- again\n"
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual(len(findings), 1)
        self.assertIn("more than once", findings[0].message)

    def test_heading_inside_code_fence_is_ignored(self) -> None:
        body = VALID_BODY + "\n```\n### First approver checklist\n```\n"
        self.assertEqual(failures(CHECK.check(body, REQUIRED)), [])


class ContentRulesTest(unittest.TestCase):
    def test_checked_item_fails_unless_allowed(self) -> None:
        body = VALID_BODY.replace("- [ ] page loads", "- [x] page loads")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual([f.subject for f in findings], ["checklist"])
        self.assertEqual(failures(CHECK.check(body, REQUIRED, allow_checked=True)), [])

    def test_unfilled_template_brace_fails(self) -> None:
        body = VALID_BODY.replace("owner: release engineer on duty", "owner: {owner}")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual([f.subject for f in findings], ["template"])
        self.assertIn("{owner}", findings[0].message)

    def test_empty_list_item_under_required_heading_fails(self) -> None:
        body = VALID_BODY.replace("- Why now: scheduled release window", "- **Why now**:")
        findings = failures(CHECK.check(body, REQUIRED))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].subject, "Second approver checklist")
        self.assertIn("empty list item", findings[0].message)


def run_main(argv):
    """Run the CLI with its output captured so test runs stay quiet."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return CHECK.main(argv)


class CommandLineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.body = self.root / "draft.md"
        self.body.write_text(VALID_BODY, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_refuses_to_run_without_required_headings(self) -> None:
        self.assertEqual(run_main([str(self.body)]), 2)

    def test_headings_file_and_flags_combine(self) -> None:
        headings = self.root / "headings.txt"
        headings.write_text("# copied from the guide\nSecond approver checklist\n\n", encoding="utf-8")
        self.assertEqual(
            run_main([str(self.body), "--heading", "First approver checklist", "--headings-file", str(headings)]),
            0,
        )

    def test_failure_sets_exit_code(self) -> None:
        self.body.write_text(VALID_BODY.replace("- [ ] page loads", "- [x] page loads"), encoding="utf-8")
        self.assertEqual(run_main([str(self.body), "--heading", "First approver checklist"]), 1)


if __name__ == "__main__":
    unittest.main()
