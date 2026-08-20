from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ValidateSkillsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        source = Path(__file__).resolve().parents[1] / "scripts" / "validate_skills.py"
        shutil.copy2(source, scripts / "validate_skills.py")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_skill(self, link_target: str) -> None:
        skill = self.root / "core" / "skills" / "example-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: example-skill\n"
            "description: >-\n"
            "  Verifies a portable example skill.\n"
            "---\n\n"
            f"Use [the reference]({link_target}) before execution.\n",
            encoding="utf-8",
        )

    def validate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.root / "scripts" / "validate_skills.py"],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_existing_relative_link(self) -> None:
        self.write_skill("references/example.md")
        reference = (
            self.root
            / "core"
            / "skills"
            / "example-skill"
            / "references"
            / "example.md"
        )
        reference.parent.mkdir()
        reference.write_text("# Example\n", encoding="utf-8")

        result = self.validate()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_broken_relative_link(self) -> None:
        self.write_skill("references/missing.md")

        result = self.validate()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken relative link references/missing.md", result.stderr)

    def test_rejects_relative_link_outside_repository(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        self.addCleanup(outside.unlink)
        self.write_skill(f"../../../../{outside.name}")

        result = self.validate()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("broken relative link", result.stderr)


if __name__ == "__main__":
    unittest.main()
