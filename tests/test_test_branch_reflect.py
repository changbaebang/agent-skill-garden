from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "core/skills/test-branch-reflect/scripts/reflect_branch.sh"

BASE = "main"
TARGET = "staging"
WORK = "feature/cart-badge"


class ReflectBranchTests(unittest.TestCase):
    """Exercise the script against a bare remote and a clone, both on disk."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.env = {
            **{k: v for k, v in os.environ.items() if k in ("PATH", "TMPDIR", "LANG", "LC_ALL")},
            "HOME": str(root / "home"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
        (root / "home").mkdir()
        self.origin = root / "origin.git"
        self.seed = root / "seed"
        self.clone = root / "clone"

        self.git(None, "init", "--quiet", "--bare", str(self.origin))
        self.git(self.origin, "symbolic-ref", "HEAD", f"refs/heads/{BASE}")

        self.seed.mkdir()
        self.git(self.seed, "init", "--quiet")
        self.git(self.seed, "symbolic-ref", "HEAD", f"refs/heads/{BASE}")
        self.commit(self.seed, "base.txt", "base\n", "base: first")
        self.git(self.seed, "branch", TARGET)
        self.git(self.seed, "checkout", "--quiet", "-b", WORK)
        self.work_first = self.commit(self.seed, "feature.txt", "feature\n", "work: first")
        self.git(self.seed, "checkout", "--quiet", BASE)
        self.git(self.seed, "remote", "add", "origin", str(self.origin))
        self.git(self.seed, "push", "--quiet", "origin", BASE, TARGET, WORK)

        self.git(None, "clone", "--quiet", str(self.origin), str(self.clone))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    # helpers -------------------------------------------------------------

    def git(self, cwd, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        command = ["git"]
        if cwd is not None:
            command += ["-C", str(cwd)]
        return subprocess.run(
            command + list(args), check=check, capture_output=True, text=True, env=self.env
        )

    def commit(self, repo: Path, name: str, content: str, message: str) -> str:
        (repo / name).write_text(content, encoding="utf-8")
        self.git(repo, "add", name)
        self.git(repo, "commit", "--quiet", "-m", message)
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def rev(self, repo: Path, ref: str) -> str:
        return self.git(repo, "rev-parse", ref).stdout.strip()

    def contains(self, repo: Path, ancestor: str, ref: str) -> bool:
        return self.git(repo, "merge-base", "--is-ancestor", ancestor, ref, check=False).returncode == 0

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=str(self.clone),
            check=False,
            capture_output=True,
            text=True,
            env=self.env,
        )

    # tests ---------------------------------------------------------------

    def test_script_parses(self) -> None:
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_merge_without_push_changes_only_the_local_copy(self) -> None:
        remote_before = self.rev(self.origin, TARGET)

        result = self.run_script("--target", TARGET, "--work", WORK)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.contains(self.clone, self.work_first, TARGET))
        self.assertEqual(self.rev(self.origin, TARGET), remote_before)
        self.assertIn("not pushed", result.stdout)
        self.assertIn("mode    : merge", result.stdout)
        # The base was detected from the remote HEAD, not passed by hand.
        self.assertIn(f"base    : {BASE} @", result.stdout)

    def test_push_updates_the_remote_with_a_merge_commit(self) -> None:
        result = self.run_script("--target", TARGET, "--work", WORK, "--base", BASE, "--push")

        self.assertEqual(result.returncode, 0, result.stderr)
        tip = self.rev(self.origin, TARGET)
        self.assertTrue(self.contains(self.origin, self.work_first, tip))
        parents = self.git(self.origin, "rev-list", "--parents", "-n", "1", tip).stdout.split()
        self.assertEqual(len(parents), 3, "a no-fast-forward merge has two parents")
        self.assertIn("(pushed)", result.stdout)

    def test_refuses_a_dirty_working_tree(self) -> None:
        (self.clone / "scratch.txt").write_text("wip\n", encoding="utf-8")
        remote_before = self.rev(self.origin, TARGET)

        result = self.run_script("--target", TARGET, "--work", WORK, "--push")

        self.assertEqual(result.returncode, 1)
        self.assertIn("not clean", result.stderr)
        self.assertEqual(self.rev(self.origin, TARGET), remote_before)

    def test_refuses_when_the_local_test_branch_holds_unpushed_commits(self) -> None:
        self.git(self.clone, "checkout", "--quiet", TARGET)
        local_only = self.commit(self.clone, "local.txt", "only here\n", "staging: local only")
        self.git(self.clone, "checkout", "--quiet", BASE)
        remote_before = self.rev(self.origin, TARGET)

        result = self.run_script("--target", TARGET, "--work", WORK, "--push")

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"missing from origin/{TARGET}", result.stderr)
        self.assertIn("staging: local only", result.stderr)
        self.assertEqual(self.rev(self.clone, TARGET), local_only, "the local commit is kept")
        self.assertEqual(self.rev(self.origin, TARGET), remote_before)

    def test_refuses_when_the_local_base_has_diverged(self) -> None:
        self.commit(self.clone, "diverge.txt", "local base\n", "main: local only")

        result = self.run_script("--target", TARGET, "--work", WORK)

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"local {BASE} holds commits missing", result.stderr)

    def test_refreshes_a_stale_base_that_is_not_checked_out(self) -> None:
        self.git(self.clone, "checkout", "--quiet", "-b", "scratch")
        scratch = self.rev(self.clone, "scratch")
        new_base = self.commit(self.seed, "later.txt", "later\n", "base: second")
        self.git(self.seed, "push", "--quiet", "origin", BASE)

        result = self.run_script("--target", TARGET, "--work", WORK)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rev(self.clone, BASE), new_base, "the base ref moved to the remote tip")
        self.assertEqual(self.rev(self.clone, "scratch"), scratch, "unrelated branches are untouched")
        self.assertEqual(self.git(self.clone, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), TARGET)
        self.assertIn(f"base    : {BASE} @ {new_base[:7]}", result.stdout)

    def test_conflict_aborts_cleanly_and_pushes_nothing(self) -> None:
        self.git(self.seed, "checkout", "--quiet", WORK)
        self.commit(self.seed, "base.txt", "changed by work\n", "work: edit base")
        self.git(self.seed, "checkout", "--quiet", TARGET)
        self.commit(self.seed, "base.txt", "changed by staging\n", "staging: edit base")
        self.git(self.seed, "checkout", "--quiet", BASE)
        self.git(self.seed, "push", "--quiet", "origin", TARGET, WORK)
        remote_before = self.rev(self.origin, TARGET)

        result = self.run_script("--target", TARGET, "--work", WORK, "--push")

        self.assertEqual(result.returncode, 1)
        self.assertIn("base.txt", result.stderr)
        self.assertIn("merge conflicts", result.stderr)
        self.assertIn("--pick", result.stderr)
        self.assertEqual(self.git(self.clone, "status", "--porcelain").stdout, "")
        self.assertEqual(self.rev(self.origin, TARGET), remote_before)

    def test_cherry_pick_moves_only_the_approved_commits(self) -> None:
        self.git(self.seed, "checkout", "--quiet", WORK)
        second = self.commit(self.seed, "second.txt", "second\n", "work: second")
        self.git(self.seed, "checkout", "--quiet", BASE)
        self.git(self.seed, "push", "--quiet", "origin", WORK)

        result = self.run_script("--target", TARGET, "--work", WORK, "--pick", second[:10], "--push")

        self.assertEqual(result.returncode, 0, result.stderr)
        tip = self.rev(self.origin, TARGET)
        files = self.git(self.origin, "ls-tree", "--name-only", tip).stdout.split()
        self.assertIn("second.txt", files)
        self.assertNotIn("feature.txt", files, "the unapproved first commit stays behind")
        message = self.git(self.origin, "log", "-1", "--format=%B", tip).stdout
        self.assertIn(f"cherry picked from commit {second}", message)
        self.assertIn(f"mode    : cherry-pick {second[:7]}", result.stdout)

    def test_cherry_pick_refuses_a_commit_that_is_not_on_the_work_branch(self) -> None:
        self.git(self.seed, "checkout", "--quiet", TARGET)
        staging_only = self.commit(self.seed, "staging.txt", "staging\n", "staging: own commit")
        self.git(self.seed, "checkout", "--quiet", BASE)
        self.git(self.seed, "push", "--quiet", "origin", TARGET)

        result = self.run_script("--target", TARGET, "--work", WORK, "--pick", staging_only)

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"is not on origin/{WORK}", result.stderr)

    def test_cherry_pick_refuses_a_commit_already_on_the_target(self) -> None:
        # The base tip is an ancestor of the work branch and of the test branch,
        # so picking it would only produce an empty commit.
        base_tip = self.rev(self.origin, BASE)

        result = self.run_script("--target", TARGET, "--work", WORK, "--pick", base_tip)

        self.assertEqual(result.returncode, 1)
        self.assertIn(f"is already on {TARGET}", result.stderr)

    def test_missing_remote_branch_is_reported(self) -> None:
        result = self.run_script("--target", "nonexistent", "--work", WORK)

        self.assertEqual(result.returncode, 1)
        self.assertIn("origin/nonexistent does not exist", result.stderr)

    def test_usage_error_without_required_arguments(self) -> None:
        result = self.run_script("--target", TARGET)

        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
