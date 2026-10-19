import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/pull-request-checklist/scripts/pr_body_sections.py"
SPEC = importlib.util.spec_from_file_location("pr_body_sections", MODULE_PATH)
assert SPEC and SPEC.loader
SECTIONS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SECTIONS
SPEC.loader.exec_module(SECTIONS)


TEMPLATE = """# Summary

Short summary written by the author.

### References

<!-- Link the ticket and any specification. -->

- Ticket: none yet

### Verification

- [ ] unit tests
- [ ] manual check

### Changes

- first draft bullet

<hr />

### Checklist

- [x] I read the contributing guide
"""


class TicketKeyTest(unittest.TestCase):
    def test_keeps_the_whole_key(self) -> None:
        self.assertEqual(SECTIONS.ticket_keys("ABCDEF-1447 fix the thing"), ["ABCDEF-1447"])

    def test_returns_every_key_once_in_order(self) -> None:
        title = "FOO-1 and BAR-22 then FOO-1 again"
        self.assertEqual(SECTIONS.ticket_keys(title), ["FOO-1", "BAR-22"])

    def test_project_filter_keeps_only_that_project(self) -> None:
        title = "docs: UTF-8 handling for BAR-22"
        self.assertEqual(SECTIONS.ticket_keys(title, project="bar"), ["BAR-22"])

    def test_lowercase_and_bare_numbers_are_not_keys(self) -> None:
        self.assertEqual(SECTIONS.ticket_keys("fix-12 and 1234 and abc-9"), [])


class ClassifyBaseTest(unittest.TestCase):
    def test_default_patterns(self) -> None:
        for branch in ("main", "master", "release/2026.10", "production/eu", "hotfix/login"):
            self.assertEqual(SECTIONS.classify_base(branch), "production-bound", branch)
        for branch in ("develop", "qa", "staging", "feature/epic-x", "release-notes"):
            self.assertEqual(SECTIONS.classify_base(branch), "integration", branch)

    def test_default_branch_is_production_bound_whatever_its_name(self) -> None:
        self.assertEqual(SECTIONS.classify_base("trunk-live", default_branch="trunk-live"), "production-bound")

    def test_explicit_patterns_replace_the_defaults(self) -> None:
        self.assertEqual(SECTIONS.classify_base("qa", production_patterns=[r"^qa$"]), "production-bound")
        self.assertEqual(SECTIONS.classify_base("main", production_patterns=[r"^qa$"]), "integration")


class UpsertTest(unittest.TestCase):
    def upsert(self, body: str, sections: str, order=()) -> str:
        return SECTIONS.upsert_sections(body, sections, order)

    def test_replaces_only_the_named_section(self) -> None:
        result = self.upsert(TEMPLATE, "### Changes\n\n- renamed the helper\n- added a test\n")
        self.assertIn("### Changes\n\n- renamed the helper\n- added a test\n\n<hr />", result)
        self.assertNotIn("first draft bullet", result)
        # Everything outside the section is byte-stable.
        before, _, _ = TEMPLATE.partition("### Changes")
        self.assertTrue(result.startswith(before))
        self.assertTrue(result.endswith("### Checklist\n\n- [x] I read the contributing guide\n"))

    def test_keeps_template_comments_under_the_heading(self) -> None:
        result = self.upsert(TEMPLATE, "### References\n\n- Ticket: ABC-12\n")
        self.assertIn(
            "### References\n\n<!-- Link the ticket and any specification. -->\n\n- Ticket: ABC-12\n\n### Verification",
            result,
        )

    def test_inserts_a_missing_section_in_template_order(self) -> None:
        order = ["References", "Risk tier", "Verification", "Changes"]
        result = self.upsert(TEMPLATE, "### Risk tier\n\nHigh\nRationale: touches payment.\n", order)
        self.assertIn("- Ticket: none yet\n\n### Risk tier\n\nHigh\nRationale: touches payment.\n\n### Verification", result)

    def test_appends_when_no_ordered_neighbour_exists(self) -> None:
        result = self.upsert("# Only a title\n", "### Notes\n\n- one\n")
        self.assertEqual(result, "# Only a title\n\n### Notes\n\n- one\n")

    def test_is_idempotent(self) -> None:
        order = ["References", "Risk tier", "Verification", "Changes"]
        sections = (
            "### References\n\n- Ticket: ABC-12\n\n"
            "### Risk tier\n\nHigh\nRationale: touches payment.\n\n"
            "### Changes\n\n- renamed the helper\n"
        )
        once = self.upsert(TEMPLATE, sections, order)
        twice = self.upsert(once, sections, order)
        self.assertEqual(once, twice)

    def test_drops_exact_duplicate_bullets(self) -> None:
        result = self.upsert(TEMPLATE, "### Changes\n\n- same\n- other\n-   same\n")
        self.assertIn("### Changes\n\n- same\n- other\n\n<hr />", result)

    def test_headings_inside_code_fences_are_content(self) -> None:
        body = "### Changes\n\n```md\n### not a heading\n```\n\n### Checklist\n\n- [x] done\n"
        result = self.upsert(body, "### Changes\n\n- real change\n")
        self.assertEqual(result, "### Changes\n\n- real change\n\n### Checklist\n\n- [x] done\n")

    def test_replacing_a_section_removes_its_nested_subsections(self) -> None:
        body = "## Impact\n\nold\n\n### Scope\n\nold scope\n\n## Verification\n\n- run\n"
        result = self.upsert(body, "## Impact\n\n- new impact\n")
        self.assertEqual(result, "## Impact\n\n- new impact\n\n## Verification\n\n- run\n")

    def test_preserves_crlf_line_endings(self) -> None:
        body = TEMPLATE.replace("\n", "\r\n")
        result = self.upsert(body, "### Changes\n\n- renamed\n")
        self.assertNotIn("\n\n", result.replace("\r\n", ""))
        self.assertIn("### Changes\r\n\r\n- renamed\r\n\r\n<hr />", result)

    def test_keeps_the_tail_after_a_horizontal_rule_and_stays_idempotent(self) -> None:
        body = "### Changes\n\n- old\n\n---\n\nFixed footer text\n\n### Checklist\n\n- [x] done\n"
        once = self.upsert(body, "### Changes\n\n- new\n")
        self.assertEqual(once, "### Changes\n\n- new\n\n---\n\nFixed footer text\n\n### Checklist\n\n- [x] done\n")
        self.assertEqual(self.upsert(once, "### Changes\n\n- new\n"), once)

    def test_a_dash_line_under_text_is_not_a_rule(self) -> None:
        body = "### Changes\n\nSetext title\n---\nmore old text\n"
        result = self.upsert(body, "### Changes\n\n- new\n")
        self.assertEqual(result, "### Changes\n\n- new\n")

    def test_heading_match_ignores_extra_whitespace(self) -> None:
        body = "###   Changes  \n\n- old\n"
        result = self.upsert(body, "### Changes\n\n- new\n")
        self.assertEqual(result, "###   Changes  \n\n- new\n")


class CommandLineTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_ticket_key_exit_code_signals_absence(self) -> None:
        found = self.run_script("ticket-key", "ABC-12", "fix", "login")
        self.assertEqual(found.returncode, 0)
        self.assertEqual(found.stdout, "ABC-12\n")
        missing = self.run_script("ticket-key", "fix login")
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(missing.stdout, "")

    def test_classify_and_sections_and_upsert(self) -> None:
        self.assertEqual(self.run_script("classify-base", "release/1.2").stdout, "production-bound\n")
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "body.md"
            sections = Path(directory) / "sections.md"
            body.write_text(TEMPLATE, encoding="utf-8")
            sections.write_text("### Changes\n\n- renamed\n", encoding="utf-8")
            listed = self.run_script("sections", "--body", str(body))
            self.assertEqual(listed.stdout, "1\tSummary\n3\tReferences\n3\tVerification\n3\tChanges\n3\tChecklist\n")
            result = self.run_script("upsert", "--body", str(body), "--sections", str(sections), "--order", "References", "Changes")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("### Changes\n\n- renamed\n\n<hr />", result.stdout)


if __name__ == "__main__":
    unittest.main()
