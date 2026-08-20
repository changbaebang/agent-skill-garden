from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap.sh"


class BootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_bootstrap(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("AGENT_GARDEN_PROFILE", None)
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--target",
                "codex",
                "--home",
                str(self.home),
                "--skip-validation",
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_dry_run_does_not_create_configuration(self) -> None:
        result = self.run_bootstrap()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Dry run only", result.stdout)
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / ".agents").exists())
        self.assertFalse((self.home / ".agent-garden").exists())

    def test_apply_creates_codex_guidance_skills_and_local_profile(self) -> None:
        result = self.run_bootstrap("--apply")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.home / ".codex" / "AGENTS.md").is_file())
        self.assertTrue((self.home / ".agents" / "skills" / "intake").is_symlink())
        profile = self.home / ".agent-garden" / "profile.ini"
        self.assertTrue(profile.is_file())
        self.assertIn("enabled = false", profile.read_text(encoding="utf-8"))
        self.assertIn("Bootstrap complete for: codex", result.stdout)

    def test_existing_guidance_is_not_overwritten(self) -> None:
        guidance = self.home / ".codex" / "AGENTS.md"
        guidance.parent.mkdir(parents=True)
        guidance.write_text("personal rules\n", encoding="utf-8")

        result = self.run_bootstrap("--apply")

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(guidance.read_text(encoding="utf-8"), "personal rules\n")
        self.assertFalse((self.home / ".agents").exists())
        self.assertIn("CONFLICT", result.stderr)

    def test_invalid_existing_profile_stops_before_installation(self) -> None:
        profile = self.home / ".agent-garden" / "profile.ini"
        profile.parent.mkdir(parents=True)
        profile.write_text("[profile]\nname = personal\n", encoding="utf-8")

        result = self.run_bootstrap("--apply")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / ".agents").exists())
        self.assertFalse((self.home / ".codex").exists())
        self.assertIn("FAIL profile.schema_version", result.stdout)


if __name__ == "__main__":
    unittest.main()
