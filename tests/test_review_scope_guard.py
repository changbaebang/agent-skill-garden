import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "core/skills/review-scope-guard/scripts/blast_radius.mjs"

GIT_IDENTITY = [
    "-c", "user.name=fixture",
    "-c", "user.email=fixture@example.invalid",
    "-c", "commit.gpgsign=false",
]


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_fixture(root: Path) -> None:
    """A two-app, one-shared-package workspace committed on `main`."""
    write(root, "package.json", json.dumps({
        "name": "fixture-root",
        "private": True,
        "workspaces": ["apps/*", "packages/*"],
    }))
    write(root, "packages/ui/package.json", json.dumps({"name": "@fixture/ui", "version": "0.0.0"}))
    write(root, "packages/ui/src/button.tsx", (
        "import { tv } from 'tailwind-variants';\n"
        "export const buttonStyles = tv({\n"
        "  base: 'inline-flex px-4',\n"
        "  variants: { tone: { primary: 'bg-black', quiet: 'bg-white' } },\n"
        "});\n"
        "export const enum ButtonTone { Primary, Quiet }\n"
    ))
    write(root, "packages/ui/src/tokens.ts", "export const spacingScale = [0, 4, 8, 16];\n")
    for app in ("web", "admin"):
        write(root, f"apps/{app}/package.json", json.dumps({
            "name": app,
            "dependencies": {"@fixture/ui": "workspace:*"},
        }))
    write(root, "apps/web/src/home.tsx", (
        "import { buttonStyles } from '@fixture/ui';\n"
        "import { spacingScale } from '@fixture/ui/tokens';\n"
        "export const Home = () => <button className={buttonStyles()} style={{ gap: spacingScale[1] }} />;\n"
    ))
    write(root, "apps/web/src/about.tsx", (
        "import { buttonStyles } from '@fixture/ui';\n"
        "export const About = () => <button className={buttonStyles({ tone: 'quiet' })} />;\n"
    ))
    write(root, "apps/web/src/local.tsx", "export const localOnly = 1;\n")
    write(root, "apps/web/src/button.test.tsx", (
        "import { buttonStyles } from '@fixture/ui';\n"
        "it('renders', () => buttonStyles());\n"
    ))
    write(root, "apps/admin/src/panel.tsx", (
        "import { buttonStyles } from '@fixture/ui';\n"
        "export const Panel = () => <button className={buttonStyles()} />;\n"
    ))
    git(root, "init", "-q")
    git(root, "symbolic-ref", "HEAD", "refs/heads/main")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "fixture")


def commit_change(root: Path, branch: str, edits: dict) -> None:
    git(root, "checkout", "-q", "-b", branch, "main")
    for relative, text in edits.items():
        write(root, relative, text)
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", branch)


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["node", str(SCRIPT), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


@unittest.skipUnless(shutil.which("node") and shutil.which("git"), "node and git are required")
class BlastRadiusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        build_fixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def result_for(self, payload: dict, file: str) -> dict:
        matches = [entry for entry in payload["results"] if entry["file"] == file]
        self.assertEqual(len(matches), 1, payload)
        return matches[0]

    def test_shared_base_style_is_flagged_with_consumers_and_dependents(self) -> None:
        commit_change(self.root, "feature/base", {
            "packages/ui/src/button.tsx": (
                "import { tv } from 'tailwind-variants';\n"
                "export const buttonStyles = tv({\n"
                "  base: 'inline-flex px-4 pt-[env(safe-area-inset-top)]',\n"
                "  variants: { tone: { primary: 'bg-black', quiet: 'bg-white' } },\n"
                "});\n"
                "export const enum ButtonTone { Primary, Quiet }\n"
            ),
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["base"], "main")
        self.assertEqual(payload["flagged_count"], 1)
        entry = self.result_for(payload, "packages/ui/src/button.tsx")
        self.assertTrue(entry["flagged"])
        self.assertEqual(entry["package"], "@fixture/ui")
        self.assertEqual(entry["dependents"], ["admin", "web"])
        self.assertTrue(any("base:" in why for why in entry["always_on"]), entry)
        self.assertEqual(entry["overrides"], [])
        # Only the touched line is inspected, so the style constant has no
        # `export` in the diff and the whole file's exports are used instead.
        consumers = {consumer["name"]: consumer for consumer in entry["consumers"]}
        self.assertIn("buttonStyles", consumers)
        # home, about, panel reference it; the test file and the source itself do not count.
        self.assertEqual(consumers["buttonStyles"]["count"], 3)
        self.assertNotIn("enum", consumers)

    def test_override_is_flagged_without_always_on(self) -> None:
        commit_change(self.root, "feature/override", {
            "apps/web/src/home.tsx": (
                "import { buttonStyles } from '@fixture/ui';\n"
                "import { spacingScale } from '@fixture/ui/tokens';\n"
                "document.documentElement.style.setProperty('--safe-area-inset-top', '0px');\n"
                "export const Home = () => <button className={buttonStyles()} style={{ gap: spacingScale[1] }} />;\n"
            ),
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        entry = self.result_for(json.loads(result.stdout), "apps/web/src/home.tsx")
        self.assertEqual(entry["always_on"], [])
        self.assertTrue(any("setProperty" in why for why in entry["overrides"]), entry)
        self.assertTrue(any("documentElement" in why for why in entry["overrides"]), entry)
        # An application's own package name is still reported, with no dependents.
        self.assertEqual(entry["package"], "web")
        self.assertEqual(entry["dependents"], [])

    def test_local_change_without_reach_exits_zero(self) -> None:
        commit_change(self.root, "feature/local", {
            "apps/web/src/local.tsx": "export const localOnly = 1;\nconst unused = 2;\n",
        })
        result = run_script(self.root, "--diff", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No reach-widening change", result.stdout)

    def test_default_output_shows_flagged_only_and_all_shows_everything(self) -> None:
        commit_change(self.root, "feature/mixed", {
            "packages/ui/src/button.tsx": (
                "import { tv } from 'tailwind-variants';\n"
                "export const buttonStyles = tv({\n"
                "  base: 'inline-flex px-6',\n"
                "  variants: { tone: { primary: 'bg-black', quiet: 'bg-white' } },\n"
                "});\n"
                "export const enum ButtonTone { Primary, Quiet }\n"
            ),
            "packages/ui/src/tokens.ts": "export const spacingScale = [0, 4, 8, 16, 32];\n",
        })
        default = run_script(self.root, "--diff", "main")
        self.assertEqual(default.returncode, 1, default.stderr)
        self.assertIn("### packages/ui/src/button.tsx", default.stdout)
        self.assertNotIn("### packages/ui/src/tokens.ts", default.stdout)
        self.assertIn("flagged 1 - consumers only 1", default.stdout)
        self.assertIn("FLAG cannot opt out", default.stdout)
        self.assertIn("dependent packages 2: admin, web", default.stdout)

        everything = run_script(self.root, "--diff", "main", "--all")
        self.assertIn("### packages/ui/src/button.tsx", everything.stdout)
        self.assertIn("### packages/ui/src/tokens.ts", everything.stdout)

    def test_base_is_detected_when_omitted(self) -> None:
        commit_change(self.root, "feature/detect", {
            "packages/ui/src/tokens.ts": "export const spacingScale = [0, 2, 4, 8, 16];\n",
        })
        result = run_script(self.root, "--diff", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["base"], "main")
        self.assertEqual(payload["flagged_count"], 0)
        entry = self.result_for(payload, "packages/ui/src/tokens.ts")
        self.assertEqual(entry["consumers"][0]["name"], "spacingScale")
        self.assertEqual(entry["consumers"][0]["count"], 1)
        self.assertEqual(entry["consumers"][0]["sample"], ["apps/web/src/home.tsx"])

    def test_explicit_files_scan_whole_file_and_skip_keywords(self) -> None:
        result = run_script(self.root, "packages/ui/src/button.tsx", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsNone(payload["base"])
        entry = self.result_for(payload, "packages/ui/src/button.tsx")
        names = [consumer["name"] for consumer in entry["consumers"]]
        self.assertIn("buttonStyles", names)
        # `const enum` is matched before `const`, so the keyword is never a symbol.
        self.assertNotIn("enum", names)
        self.assertNotIn("const", names)

    def test_pnpm_workspace_file_is_read_for_dependents(self) -> None:
        # The same fixture, declared through pnpm-workspace.yaml instead of the
        # root manifest's "workspaces" field. Discovery reads the working tree.
        write(self.root, "package.json", json.dumps({"name": "fixture-root", "private": True}))
        write(self.root, "pnpm-workspace.yaml", (
            "# workspace layout\n"
            "packages:\n"
            "  - 'apps/*'\n"
            "  - \"packages/**\"\n"
            "  - '!packages/ui/node_modules'\n"
        ))
        result = run_script(self.root, "packages/ui/src/button.tsx", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        entry = self.result_for(json.loads(result.stdout), "packages/ui/src/button.tsx")
        self.assertEqual(entry["package"], "@fixture/ui")
        self.assertEqual(entry["dependents"], ["admin", "web"])

    def test_plain_object_fields_and_variables_are_not_flagged(self) -> None:
        # `base:` with a non-class value and a `body` variable are ordinary
        # code, not a shared default or a global selector.
        commit_change(self.root, "feature/plain", {
            "apps/web/src/client.ts": (
                "const baseUrl = 'https://example.invalid';\n"
                "export const client = { base: baseUrl, retries: 2 };\n"
                "export const send = (body: string) => fetch(baseUrl, { body });\n"
            ),
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["flagged_count"], 0)

    def test_stylesheet_global_selector_is_flagged(self) -> None:
        commit_change(self.root, "feature/global-css", {
            "packages/ui/src/reset.css": "html, body {\n  margin: 0;\n}\n",
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        entry = self.result_for(json.loads(result.stdout), "packages/ui/src/reset.css")
        self.assertTrue(any("global selector" in why for why in entry["always_on"]), entry)

    def test_test_files_are_neither_scanned_nor_counted(self) -> None:
        commit_change(self.root, "feature/spec", {
            "apps/web/src/layout.spec.ts": (
                "export const config = { base: 'px-4' };\n"
                "document.documentElement.style.setProperty('--x', '0');\n"
            ),
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["files_scanned"], 0)
        self.assertEqual(payload["results"], [])

    def test_consumers_inside_one_application_are_not_searched(self) -> None:
        # local.tsx is referenced by nothing, but home.tsx exports Home which
        # could be imported elsewhere in the same app; without a flag and
        # without dependents the search is skipped and the file is silent.
        commit_change(self.root, "feature/app-local", {
            "apps/web/src/home.tsx": (
                "import { buttonStyles } from '@fixture/ui';\n"
                "import { spacingScale } from '@fixture/ui/tokens';\n"
                "export const Home = () => <button className={buttonStyles({ tone: 'quiet' })} style={{ gap: spacingScale[2] }} />;\n"
            ),
            "apps/web/src/about.tsx": (
                "import { buttonStyles } from '@fixture/ui';\n"
                "import { Home } from './home';\n"
                "export const About = () => <><Home /><button className={buttonStyles({ tone: 'quiet' })} /></>;\n"
            ),
        })
        result = run_script(self.root, "--diff", "main", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["results"], [])

    def test_runs_from_a_subdirectory(self) -> None:
        result = run_script(self.root / "apps" / "web", "src/local.tsx", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["files_scanned"], 1)
        self.assertEqual(payload["results"], [])

    def test_usage_errors_exit_two(self) -> None:
        self.assertEqual(run_script(self.root).returncode, 2)
        self.assertEqual(run_script(self.root, "--diff", "main", "src/x.tsx").returncode, 2)
        self.assertEqual(run_script(self.root, "--diff", "no-such-base").returncode, 2)
        self.assertEqual(run_script(self.root, "--bogus").returncode, 2)

    def test_outside_a_git_repository_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            result = run_script(Path(plain), "--diff")
            self.assertEqual(result.returncode, 2)
            self.assertIn("git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
