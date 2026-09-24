from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "repository"
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/check-public-safety.sh", self.root / "scripts")
        (self.root / "config").mkdir()
        (self.root / "config/forbidden-patterns.txt").write_text(
            "DO_NOT_PUBLISH_[A-Z]+\n", encoding="utf-8")
        (self.root / ".gitignore").write_text("work/\n", encoding="utf-8")
        self.git("init", "-q")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True)

    def write(self, path, text="DO_NOT_PUBLISH_SECRET\n"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def scan(self, scanner, root=None):
        # An isolated PATH really exercises the grep fallback even on hosts
        # where ripgrep is installed. Never replace the production scan logic.
        tools = self.home / f"bin-{scanner}"
        tools.mkdir(exist_ok=True)
        for name in ("bash", "git", "dirname", "mktemp", "rm", scanner):
            executable = shutil.which(name)
            if executable is None:
                self.skipTest(f"{name} is unavailable")
            link = tools / name
            if not link.exists():
                link.symlink_to(executable)
        env = dict(os.environ, PATH=str(tools))
        return subprocess.run([str((root or self.root) / "scripts/check-public-safety.sh")],
                              env=env, capture_output=True, text=True)

    def assert_scanners(self, succeeds, message=None, root=None):
        for scanner in ("rg", "grep"):
            with self.subTest(scanner=scanner):
                result = self.scan(scanner, root)
                if succeeds:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                if message:
                    self.assertIn(message, result.stdout + result.stderr)

    def test_ignored_runs_are_not_scanned(self):
        self.write("work/run.json")
        self.write("public.md", "Public documentation.\n")
        self.assert_scanners(True)

    def test_tracked_ignored_files_are_still_scanned(self):
        self.write("work/tracked.json")
        self.git("add", "-f", "work/tracked.json")
        self.assert_scanners(False, "DO_NOT_PUBLISH_SECRET")

    def test_untracked_public_files_and_hidden_files_are_scanned(self):
        self.write(".public/note with spaces.txt")
        self.assert_scanners(False, "DO_NOT_PUBLISH_SECRET")

    def test_only_the_root_pattern_configuration_is_exempt(self):
        self.write("docs/forbidden-patterns.txt")
        self.assert_scanners(False, "DO_NOT_PUBLISH_SECRET")

    def test_binary_files_are_scanned_consistently(self):
        (self.root / "fixture.bin").write_bytes(b"\x00DO_NOT_PUBLISH_SECRET\n")
        self.assert_scanners(False, "DO_NOT_PUBLISH_SECRET")

    def test_invalid_pattern_fails_closed(self):
        self.write("config/forbidden-patterns.txt", "(\n")
        self.assert_scanners(False, "scanner failed")

    def test_git_enumeration_failure_does_not_pass(self):
        shutil.rmtree(self.root / ".git")
        self.assert_scanners(False, "Cannot enumerate repository files")

    def test_zero_eligible_files_does_not_pass(self):
        self.write("private.txt")
        self.write(".gitignore", "*\n")
        self.assert_scanners(False, "No eligible repository files")

    def test_only_exempt_configuration_does_not_pass(self):
        self.write(".gitignore", "*\n")
        self.git("add", "-f", "config/forbidden-patterns.txt")
        self.assert_scanners(False, "No eligible repository files")

    def test_worktree_git_pointer_is_not_scanned(self):
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "Fixture")
        # Put the common Git directory below a forbidden path. A recursive grep
        # of the worktree's .git pointer would incorrectly report that path.
        common = self.home / "DO_NOT_PUBLISH_METADATA"
        self.root.rename(common)
        self.root = common
        worktree = self.home / "worktree"
        self.git("worktree", "add", "--detach", "-q", str(worktree))
        self.assertIn("DO_NOT_PUBLISH_METADATA", (worktree / ".git").read_text())
        self.assert_scanners(True, root=worktree)


if __name__ == "__main__":
    unittest.main()
