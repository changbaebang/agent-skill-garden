from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "core" / "skills" / "environment-profile" / "scripts" / "profile_init.py"
DOCTOR = ROOT / "core" / "skills" / "environment-profile" / "scripts" / "profile_doctor.py"


class EnvironmentProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_script(self, script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, script, *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def initialize_project(self) -> Path:
        subprocess.run(["git", "init", "-q", self.root], check=True)
        result = self.run_script(INIT, "--scope", "project", "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.root / ".agent-garden" / "profile.ini"

    def write_valid_profile(self, profile: Path) -> None:
        repository = self.root / "blog"
        drafts = self.root / "drafts"
        (repository / ".git").mkdir(parents=True)
        (repository / "_posts").mkdir()
        drafts.mkdir()
        profile.write_text(
            "[profile]\n"
            "schema_version = 1\n"
            "name = personal\n"
            "visibility = local\n\n"
            "[integration.blog]\n"
            "enabled = true\n"
            "driver = jekyll-git\n"
            f"repository = {repository}\n"
            f"drafts = {drafts}\n"
            "content_root = _posts\n"
            "branch = main\n"
            "base_url = https://example.github.io\n"
            "verify = page,sitemap,home\n\n"
            "[integration.slack]\n"
            "enabled = true\n"
            "driver = slack-host-connector\n"
            "workspace = example-workspace\n",
            encoding="utf-8",
        )

    def test_project_initializer_protects_profile_and_refuses_overwrite(self) -> None:
        profile = self.initialize_project()

        self.assertTrue(profile.is_file())
        self.assertEqual(
            (self.root / ".agent-garden" / ".gitignore").read_text(encoding="utf-8"),
            "profile.ini\n*.local.ini\n",
        )
        ignored = subprocess.run(
            ["git", "-C", self.root, "check-ignore", "--quiet", ".agent-garden/profile.ini"],
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)

        second = self.run_script(INIT, "--scope", "project", "--root", str(self.root))
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("refusing to overwrite", second.stderr)

    def test_doctor_accepts_valid_ignored_jekyll_profile(self) -> None:
        profile = self.initialize_project()
        self.write_valid_profile(profile)

        result = self.run_script(DOCTOR, "--root", str(self.root))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS profile.visibility: local profile is ignored by Git", result.stdout)
        self.assertIn("PASS integration.blog.repository", result.stdout)
        self.assertIn("WARN integration.slack.runtime", result.stdout)

    def test_doctor_rejects_missing_jekyll_paths(self) -> None:
        profile = self.initialize_project()
        profile.write_text(
            "[profile]\n"
            "schema_version = 1\n"
            "name = personal\n"
            "visibility = local\n\n"
            "[integration.blog]\n"
            "driver = jekyll-git\n"
            "repository = ./missing-blog\n"
            "drafts = ./missing-drafts\n"
            "content_root = _posts\n"
            "branch = main\n"
            "base_url = https://example.github.io\n",
            encoding="utf-8",
        )

        result = self.run_script(DOCTOR, "--root", str(self.root))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL integration.blog.repository", result.stdout)
        self.assertIn("FAIL integration.blog.drafts", result.stdout)

    def test_doctor_rejects_secret_bearing_keys(self) -> None:
        profile = self.initialize_project()
        profile.write_text(
            "[profile]\n"
            "schema_version = 1\n"
            "name = personal\n"
            "visibility = local\n"
            "api_token = do-not-store-this\n\n"
            "[integration.slack]\n"
            "driver = slack-host-connector\n"
            "workspace = example-workspace\n",
            encoding="utf-8",
        )

        result = self.run_script(DOCTOR, "--root", str(self.root))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("secret-bearing keys are forbidden", result.stdout)


if __name__ == "__main__":
    unittest.main()
