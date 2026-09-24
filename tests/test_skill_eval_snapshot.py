from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_eval_snapshot", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class SkillSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "skill"
        self.root.mkdir()
        self.write("SKILL.md", "Use the supplied references.")

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_hidden_files_and_directories_never_enter_snapshot_or_prompt(self):
        for name in (".env", ".git/config", "references/.credentials", "references/.cache/data.txt"):
            self.write(name, "FAKE_PRIVATE_FIXTURE_VALUE")
        snapshot = EVAL.skill_at(str(self.root))
        self.assertEqual(snapshot["files"], {"SKILL.md": "Use the supplied references."})
        prompt = EVAL.prompt_for({"task": "Review.", "inputs": {"source": "fixture"}}, snapshot)
        self.assertNotIn("FAKE_PRIVATE_FIXTURE_VALUE", prompt)

    def test_hidden_directories_are_pruned_before_traversal(self):
        self.write(".git/config", "fake repository metadata")
        self.write("references/.cache/data.txt", "fake cached data")
        original_scandir = os.scandir

        def reject_hidden_directory(path):
            relative = Path(path).relative_to(self.root)
            if any(part.startswith(".") for part in relative.parts):
                raise AssertionError("traversed a hidden directory")
            return original_scandir(path)

        with patch.object(os, "scandir", side_effect=reject_hidden_directory):
            self.assertEqual(set(EVAL.skill_at(str(self.root))["files"]), {"SKILL.md"})

    def test_hidden_files_are_excluded_before_opening(self):
        self.write(".env", "FAKE_PRIVATE_FIXTURE_VALUE")
        self.write("references/.credentials", "FAKE_PRIVATE_FIXTURE_VALUE")
        original_open = Path.open

        def reject_hidden_file(path, *args, **kwargs):
            if any(part.startswith(".") for part in path.relative_to(self.root).parts):
                raise AssertionError("opened a hidden file")
            return original_open(path, *args, **kwargs)

        with patch.object(Path, "open", reject_hidden_file):
            self.assertEqual(set(EVAL.skill_at(str(self.root))["files"]), {"SKILL.md"})

    def test_visible_text_references_include_json_yaml_and_scripts(self):
        references = {
            "references/contract.json": '{"version": 1}',
            "agents/openai.yaml": "display_name: Fixture",
            "scripts/helper.py": "print('fixture')",
            "references/guide.md": "Evidence first.",
        }
        for name, content in references.items():
            self.write(name, content)
        snapshot = EVAL.skill_at(str(self.root))
        self.assertEqual(snapshot["files"], {"SKILL.md": "Use the supplied references.", **references})

    def test_hidden_symlinks_are_ignored_but_visible_symlinks_are_rejected(self):
        outside = self.root.parent / "outside.txt"
        outside.write_text("FAKE_OUTSIDE_VALUE", encoding="utf-8")
        (self.root / ".hidden-link").symlink_to(outside)
        self.assertEqual(set(EVAL.skill_at(str(self.root))["files"]), {"SKILL.md"})
        (self.root / "visible-link").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "must stay inside"):
            EVAL.skill_at(str(self.root))


if __name__ == "__main__":
    unittest.main()
