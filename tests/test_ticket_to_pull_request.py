from __future__ import annotations

import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "ticket-to-pull-request"
    / "scripts"
    / "work_item_key.py"
)
SPEC = importlib.util.spec_from_file_location("work_item_key", SCRIPT)
assert SPEC and SPEC.loader
WORK_ITEM_KEY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = WORK_ITEM_KEY
SPEC.loader.exec_module(WORK_ITEM_KEY)


class ExtractKeysTest(unittest.TestCase):
    def test_digit_in_prefix_is_not_truncated(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.extract_keys("fix AB1CD-42 crash"), ["AB1CD-42"])

    def test_keys_keep_first_appearance_order_without_duplicates(self) -> None:
        text = "ZZ-9 then AB1CD-42, again ZZ-9 and QA-7"
        self.assertEqual(WORK_ITEM_KEY.extract_keys(text), ["ZZ-9", "AB1CD-42", "QA-7"])

    def test_lowercase_and_embedded_tokens_are_ignored(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.extract_keys("ab-12 xAB-12 AB-12x AB-"), [])

    def test_branch_names_yield_their_key(self) -> None:
        self.assertEqual(
            WORK_ITEM_KEY.extract_keys("feature/AB1CD-42-remove-legacy-parser"),
            ["AB1CD-42"],
        )


class PrimaryKeyTest(unittest.TestCase):
    def test_longest_key_wins_by_default(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.primary_key("QA-7 blocks AB1CD-42"), "AB1CD-42")

    def test_preferred_prefix_beats_length(self) -> None:
        self.assertEqual(
            WORK_ITEM_KEY.primary_key("AB1CD-42 blocks QA-7", prefer=["QA"]), "QA-7"
        )

    def test_preferred_prefix_requires_exact_match(self) -> None:
        self.assertEqual(
            WORK_ITEM_KEY.primary_key("ABC-1 and AB-22", prefer=["AB"]), "AB-22"
        )

    def test_first_wins_among_equal_length(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.primary_key("AA-11 and BB-22"), "AA-11")

    def test_no_key_returns_none(self) -> None:
        self.assertIsNone(WORK_ITEM_KEY.primary_key("nothing here"))


class BranchNameTest(unittest.TestCase):
    def test_title_becomes_ascii_slug(self) -> None:
        self.assertEqual(
            WORK_ITEM_KEY.branch_name("AB1CD-42", "Remove legacy parser!"),
            "feature/AB1CD-42-remove-legacy-parser",
        )

    def test_non_ascii_title_falls_back_to_key_only(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.branch_name("AB1CD-42", "제목만 있음"), "feature/AB1CD-42")

    def test_slug_is_trimmed_to_budget_without_dangling_hyphen(self) -> None:
        name = WORK_ITEM_KEY.branch_name(
            "AB1CD-42", "a very long title that keeps going on and on", max_length=36
        )
        self.assertLessEqual(len(name), 36)
        self.assertFalse(name.endswith("-"))
        self.assertTrue(name.startswith("feature/AB1CD-42-"))

    def test_custom_prefix_and_empty_prefix(self) -> None:
        self.assertEqual(WORK_ITEM_KEY.branch_name("QA-7", "x", prefix="fix/"), "fix/QA-7-x")
        self.assertEqual(WORK_ITEM_KEY.branch_name("QA-7", "x", prefix=""), "QA-7-x")

    def test_invalid_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            WORK_ITEM_KEY.branch_name("not-a-key", "title")


class CommandLineTest(unittest.TestCase):
    def run_cli(self, *argv: str, stdin: str = "") -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        original = sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = WORK_ITEM_KEY.main(list(argv))
        finally:
            sys.stdin = original
        return code, out.getvalue(), err.getvalue()

    def test_extract_prints_one_key_per_line(self) -> None:
        code, out, _ = self.run_cli("extract", "QA-7", "and", "AB1CD-42")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["QA-7", "AB1CD-42"])

    def test_primary_reads_stdin_and_honours_prefer(self) -> None:
        code, out, _ = self.run_cli("primary", "-", "--prefer", "QA", stdin="AB1CD-42 QA-7\n")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "QA-7")

    def test_primary_without_key_fails(self) -> None:
        code, out, err = self.run_cli("primary", "plain text")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("no tracker key", err)

    def test_branch_command(self) -> None:
        code, out, _ = self.run_cli("branch", "AB1CD-42", "--title", "Remove legacy parser")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "feature/AB1CD-42-remove-legacy-parser")


if __name__ == "__main__":
    unittest.main()
