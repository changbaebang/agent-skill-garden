from __future__ import annotations

import html
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_eval", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class SkillEvaluationRenderingTests(unittest.TestCase):
    def test_pipes_after_any_number_of_backslashes_cannot_add_table_cells(self):
        for slashes in range(5):
            original = "before " + "\\" * slashes + "| after"
            with self.subTest(slashes=slashes):
                rendered = EVAL.md(original)
                # GFM splits table cells before decoding character entities.
                # No raw pipe or backslash can escape the generated cell.
                self.assertNotIn("|", rendered)
                self.assertNotIn("\\", rendered)
                self.assertEqual(("| " + rendered + " | stable |").count("|"), 3)
                self.assertEqual(html.unescape(rendered), original)

    def test_unicode_line_separators_cannot_add_rows_or_blocks(self):
        original = "first\nsecond\rthird\r\nfourth\u2028| forged |\u2029# forged\tend"
        rendered = EVAL.md(original)
        self.assertEqual(len(rendered.splitlines()), 1)
        self.assertFalse(any(char.isspace() and char != " " for char in rendered))
        self.assertEqual(html.unescape(rendered), "".join(
            " " if char.isspace() else char for char in original))

    def test_notes_preserve_literal_text_without_active_html_or_markdown(self):
        original = '<img src=x onerror="boom"> &lt;script&gt; **bold** _text_ `code` [link](bad) ~~gone~~'
        rendered = EVAL.md(original)
        for syntax in ("<", ">", "*", "_", "`", "[", "]", "~"):
            self.assertNotIn(syntax, rendered)
        # Decode exactly once, as the renderer does: pre-existing entity text
        # must remain literal rather than becoming a second-stage HTML tag.
        self.assertEqual(html.unescape(rendered), original)
        self.assertIn("&amp;lt;script&amp;gt;", rendered)

    def test_ordinary_korean_notes_remain_readable(self):
        original = "입력과 실제 결과를 확인했습니다. 2회 중 1회 실패했습니다."
        self.assertEqual(EVAL.md(original), original)


if __name__ == "__main__":
    unittest.main()
