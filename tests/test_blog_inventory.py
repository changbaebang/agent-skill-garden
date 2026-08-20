from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "blog-writing-workflow"
    / "scripts"
    / "blog_inventory.py"
)
SPEC = importlib.util.spec_from_file_location("blog_inventory", SCRIPT)
assert SPEC and SPEC.loader
BLOG_INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BLOG_INVENTORY)


class BlogInventoryTests(unittest.TestCase):
    def test_inventory_reports_structure_without_body_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "posts").mkdir()
            (root / "posts" / "2026-01-01-example.md").write_text(
                "---\n"
                "title: Example\n"
                "date: 2026-01-01\n"
                "tags: [testing]\n"
                "---\n\n"
                "## A heading\n\n"
                "Private sentence that must not appear in the inventory.\n\n"
                "- one\n- two\n",
                encoding="utf-8",
            )

            result = BLOG_INVENTORY.build_inventory(root, sample_size=5)
            rendered = str(result)

            self.assertEqual(result["post_count"], 1)
            self.assertEqual(result["frontmatter_key_counts"]["title"], 1)
            self.assertEqual(result["average_body_metrics"]["h2_headings"], 1.0)
            self.assertEqual(
                result["sample_paths"], ["posts/2026-01-01-example.md"]
            )
            self.assertNotIn("Private sentence", rendered)
            self.assertNotIn("Example", rendered)
            self.assertNotIn("testing", rendered)

    def test_excludes_generated_and_build_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "kept.md").write_text("# Kept\n", encoding="utf-8")
            for name in (".agent-blog", "_site", "node_modules"):
                excluded = root / name
                excluded.mkdir()
                (excluded / "ignored.md").write_text("# Ignored\n", encoding="utf-8")

            result = BLOG_INVENTORY.build_inventory(root, sample_size=5)

            self.assertEqual(result["post_count"], 1)
            self.assertEqual(result["sample_paths"], ["kept.md"])

    def test_does_not_exclude_a_source_named_like_an_ignored_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "build"
            root.mkdir()
            (root / "kept.md").write_text("# Kept\n", encoding="utf-8")

            result = BLOG_INVENTORY.build_inventory(root, sample_size=5)

            self.assertEqual(result["post_count"], 1)
            self.assertEqual(result["sample_paths"], ["kept.md"])


if __name__ == "__main__":
    unittest.main()
