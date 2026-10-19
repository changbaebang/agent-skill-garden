from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/package-release/scripts/release_prep.py"
SPEC = importlib.util.spec_from_file_location("release_prep", MODULE_PATH)
assert SPEC and SPEC.loader
PREP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREP
SPEC.loader.exec_module(PREP)


CHANGELOG = """# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added
- `--format sarif` output for code scanning uploads

### Fixed
- exit code was 0 when a rule failed

## [0.4.0] - 2026-01-10

### Added
- first public command

[Unreleased]: https://example.invalid/owner/pkg/compare/v0.4.0...HEAD
[0.4.0]: https://example.invalid/owner/pkg/releases/tag/v0.4.0
"""


def run(*argv: str):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = PREP.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class SuggestTest(unittest.TestCase):
    def counts(self, **kwargs) -> dict:
        return dict(kwargs)

    def test_additions_on_0x_are_a_minor(self) -> None:
        level, version, _ = PREP.suggest_bump("0.4.0", self.counts(added=1), breaking=False)
        self.assertEqual((level, version), ("minor", "0.5.0"))

    def test_fixes_only_are_a_patch(self) -> None:
        level, version, _ = PREP.suggest_bump("0.4.0", self.counts(fixed=2), breaking=False)
        self.assertEqual((level, version), ("patch", "0.4.1"))

    def test_breaking_on_0x_is_a_minor_with_the_caveat(self) -> None:
        level, version, reason = PREP.suggest_bump("0.4.2", self.counts(changed=1), breaking=True)
        self.assertEqual((level, version), ("minor", "0.5.0"))
        self.assertIn("0.x", reason)

    def test_breaking_after_1_0_is_a_major(self) -> None:
        level, version, _ = PREP.suggest_bump("1.3.7", self.counts(fixed=1), breaking=True)
        self.assertEqual((level, version), ("major", "2.0.0"))

    def test_a_removal_counts_as_breaking(self) -> None:
        level, version, _ = PREP.suggest_bump("2.0.0", self.counts(removed=1), breaking=False)
        self.assertEqual((level, version), ("major", "3.0.0"))

    def test_prerelease_suffix_is_tolerated(self) -> None:
        self.assertEqual(PREP.parse_semver("v1.2.3-rc.1"), (1, 2, 3))

    def test_non_semver_is_refused(self) -> None:
        with self.assertRaises(PREP.ReleaseError):
            PREP.parse_semver("1.2")

    def test_cli_reads_the_manifest_and_refuses_an_empty_section(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text('{"name": "pkg", "version": "0.4.0"}\n', encoding="utf-8")
            (root / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
            code, out, _ = run("suggest", "--root", str(root), "--changelog", str(root / "CHANGELOG.md"))
            self.assertEqual(code, 0)
            self.assertIn("current : 0.4.0", out)
            self.assertIn("proposed: 0.5.0 (minor)", out)
            self.assertIn("decision: yours", out)

            empty = CHANGELOG.replace(
                "### Added\n- `--format sarif` output for code scanning uploads\n\n### Fixed\n- exit code was 0 when a rule failed\n",
                "",
                1,
            )
            (root / "CHANGELOG.md").write_text(empty, encoding="utf-8")
            code, _, err = run("suggest", "--root", str(root), "--changelog", str(root / "CHANGELOG.md"))
            self.assertEqual(code, 1)
            self.assertIn("empty", err)


class ChangelogTest(unittest.TestCase):
    def test_header_is_replaced_not_duplicated_and_link_retargeted(self) -> None:
        updated, notes = PREP.promote_unreleased(CHANGELOG, "0.5.0", "2026-02-01")
        self.assertNotIn("[Unreleased]", updated)
        self.assertIn("## [0.5.0] - 2026-02-01", updated)
        self.assertEqual(updated.count("## [0.5.0]"), 1)
        self.assertIn("[0.5.0]: https://example.invalid/owner/pkg/compare/v0.4.0...v0.5.0", updated)
        self.assertTrue(any("retargeted" in note for note in notes))
        # The body under the header is untouched.
        self.assertIn("- `--format sarif` output for code scanning uploads", updated)

    def test_existing_version_header_is_refused(self) -> None:
        with self.assertRaises(PREP.ReleaseError) as caught:
            PREP.promote_unreleased(CHANGELOG, "0.4.0", "2026-02-01")
        self.assertIn("already exists", str(caught.exception))

    def test_empty_unreleased_is_refused(self) -> None:
        text = "# Changelog\n\n## [Unreleased]\n\n## [0.4.0] - 2026-01-10\n\n### Added\n- x\n"
        with self.assertRaises(PREP.ReleaseError) as caught:
            PREP.promote_unreleased(text, "0.5.0", "2026-02-01")
        self.assertIn("empty", str(caught.exception))

    def test_missing_unreleased_header_is_refused(self) -> None:
        with self.assertRaises(PREP.ReleaseError):
            PREP.promote_unreleased("# Changelog\n\n## [0.4.0] - 2026-01-10\n- x\n", "0.5.0", "2026-02-01")

    def test_bad_date_or_version_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            PREP.promote_unreleased(CHANGELOG, "0.5.0", "02/01/2026")
        with self.assertRaises(PREP.ReleaseError):
            PREP.promote_unreleased(CHANGELOG, "0.5", "2026-02-01")

    def test_future_tense_preamble_is_flagged(self) -> None:
        text = CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\nThe next release will add SARIF.\n", 1)
        _, notes = PREP.promote_unreleased(text, "0.5.0", "2026-02-01")
        self.assertTrue(any("future tense" in note for note in notes))

    def test_cli_is_a_dry_run_unless_write_is_passed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CHANGELOG.md"
            path.write_text(CHANGELOG, encoding="utf-8")
            code, out, _ = run("changelog", "--changelog", str(path), "--version", "0.5.0", "--date", "2026-02-01")
            self.assertEqual(code, 0)
            self.assertIn("dry run", out)
            self.assertIn("+ 5: ## [0.5.0] - 2026-02-01", out)
            self.assertEqual(path.read_text(encoding="utf-8"), CHANGELOG)

            code, out, _ = run("changelog", "--changelog", str(path), "--version", "0.5.0", "--date", "2026-02-01", "--write")
            self.assertEqual(code, 0)
            self.assertIn("written", out)
            self.assertIn("## [0.5.0] - 2026-02-01", path.read_text(encoding="utf-8"))

            promoted = path.read_text(encoding="utf-8")
            code, _, err = run("changelog", "--changelog", str(path), "--version", "0.5.0", "--date", "2026-02-01", "--write")
            self.assertEqual(code, 1, "a second run must refuse: the Unreleased header is gone")
            self.assertIn("Unreleased", err)
            self.assertEqual(path.read_text(encoding="utf-8"), promoted, "a refusal writes nothing")


class ScanTest(unittest.TestCase):
    def make_tree(self, root: Path) -> None:
        (root / "package.json").write_text('{"name": "pkg", "version": "0.4.0"}\n', encoding="utf-8")
        (root / "README.md").write_text(
            'Run `npx pkg@0.4.0 --check`.\n\n```json\n{"version": "0.4.0"}\n```\n\nNot this: 10.4.0 or 0.4.01 or 0.4.0.1\n',
            encoding="utf-8",
        )
        (root / "CHANGELOG.md").write_text("## [0.4.0] - 2026-01-10\n", encoding="utf-8")
        (root / "pnpm-lock.yaml").write_text("pkg: 0.4.0\n", encoding="utf-8")
        (root / "node_modules" / "dep").mkdir(parents=True)
        (root / "node_modules" / "dep" / "index.js").write_text("// 0.4.0\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "cli.test.ts").write_text("expect(out).toBe('0.4.0');\n", encoding="utf-8")
        (root / "logo.bin").write_bytes(b"\xff\xfe0.4.0\x00\x80")

    def test_whole_token_matching(self) -> None:
        pattern = PREP.literal_pattern("0.4.0")
        self.assertIsNotNone(pattern.search("pkg@0.4.0 --check"))
        self.assertIsNotNone(pattern.search('"version": "0.4.0"'))
        self.assertIsNone(pattern.search("10.4.0"))
        self.assertIsNone(pattern.search("0.4.01"))
        self.assertIsNone(pattern.search("0.4.0.1"))

    def test_scan_skips_locks_changelog_dependencies_and_binaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            hits = PREP.scan_literals(root, "0.4.0")
            files = sorted({str(path) for path, _, _ in hits})
            self.assertEqual(files, ["README.md", "package.json", "src/cli.test.ts"])
            readme_lines = [number for path, number, _ in hits if str(path) == "README.md"]
            self.assertEqual(readme_lines, [1, 4], "the look-alike versions on the last line are not hits")

    def test_cli_reads_old_version_from_the_manifest_and_honours_exclude(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_tree(root)
            code, out, _ = run("scan", "--root", str(root), "--exclude", "cli.test.ts")
            self.assertEqual(code, 0)
            self.assertIn("old version 0.4.0 read from", out)
            self.assertIn("README.md:1:", out)
            self.assertNotIn("cli.test.ts", out)
            self.assertIn("3 line(s) carry 0.4.0", out)

    def test_manifest_detection_for_pyproject_and_cargo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text('[build-system]\nrequires = ["x"]\n\n[project]\nname = "pkg"\nversion = "1.2.3"\n', encoding="utf-8")
            self.assertEqual(PREP.read_manifest_version(root)[1], "1.2.3")
            (root / "pyproject.toml").unlink()
            (root / "Cargo.toml").write_text('[package]\nname = "pkg"\nversion = "0.9.0"\n\n[dependencies]\nserde = "1"\n', encoding="utf-8")
            self.assertEqual(PREP.read_manifest_version(root)[1], "0.9.0")

    def test_missing_manifest_is_a_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, _, err = run("scan", "--root", directory)
            self.assertEqual(code, 1)
            self.assertIn("no manifest found", err)


if __name__ == "__main__":
    unittest.main()
