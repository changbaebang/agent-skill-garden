import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core" / "skills" / "vendored-skill-lifecycle" / "scripts" / "vendor_lock.py"
)
spec = importlib.util.spec_from_file_location("vendor_lock", SCRIPT)
vendor_lock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vendor_lock)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = vendor_lock.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class VendorLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "root"
        plugin = self.root / "vendor" / "toolkit" / "plugins" / "demo"
        (plugin / "skills").mkdir(parents=True)
        (plugin / "skills" / "scan.md").write_text("# scan\n", encoding="utf-8")
        self.install_args = [
            "install", "--root", str(self.root), "--plugin", "demo",
            "--source", "https://example.invalid/team/toolkit.git",
            "--ticket", "T-1", "--plugin-path", "plugins/demo",
        ]

    def test_install_status_teardown_roundtrip(self):
        code, out, _ = run(*self.install_args)
        self.assertEqual(code, 0, out)
        wrapper = self.root / "skills" / "demo-vendor" / "SKILL.md"
        text = wrapper.read_text(encoding="utf-8")
        self.assertIn(vendor_lock.MARKER, text)
        self.assertIn("skills/scan.md", text)
        lock = json.loads((self.root / "vendor-lock.json").read_text())
        self.assertEqual(lock["installs"][0]["ticket"], "T-1")

        code, out, _ = run("status", "--root", str(self.root), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["installs"][0]["problems"], [])

        code, out, _ = run("teardown", "--root", str(self.root), "--ticket", "T-1")
        self.assertEqual(code, 0)
        self.assertFalse(wrapper.parent.exists())
        self.assertTrue((self.root / "vendor" / "toolkit" / "plugins" / "demo").is_dir())
        lock = json.loads((self.root / "vendor-lock.json").read_text())
        self.assertEqual(lock["installs"], [])

    def test_dry_run_writes_nothing(self):
        code, _, _ = run(*self.install_args, "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse((self.root / "vendor-lock.json").exists())
        self.assertFalse((self.root / "skills").exists())

    def test_duplicate_plugin_refused(self):
        run(*self.install_args)
        code, _, err = run(*self.install_args[:-4], "--ticket", "T-2", "--plugin-path", "plugins/demo")
        self.assertEqual(code, 1)
        self.assertIn("already installed", err)

    def test_missing_clone_refused(self):
        code, _, err = run("install", "--root", str(self.root), "--plugin", "other",
                           "--source", "x/y", "--ticket", "T-3")
        self.assertEqual(code, 1)
        self.assertIn("clone", err)

    def test_teardown_refuses_unmanaged_wrapper(self):
        run(*self.install_args)
        wrapper = self.root / "skills" / "demo-vendor" / "SKILL.md"
        wrapper.write_text("hand written\n", encoding="utf-8")
        code, _, err = run("teardown", "--root", str(self.root), "--ticket", "T-1")
        self.assertEqual(code, 1)
        self.assertIn("not written by this script", err)
        self.assertTrue(wrapper.exists())

    def test_install_refuses_existing_foreign_directory(self):
        foreign = self.root / "skills" / "demo-vendor"
        foreign.mkdir(parents=True)
        (foreign / "SKILL.md").write_text("mine\n", encoding="utf-8")
        code, _, err = run(*self.install_args)
        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)

    def test_invalid_names_refused(self):
        code, _, err = run("install", "--root", str(self.root), "--plugin", "Bad Name",
                           "--source", "x/y", "--ticket", "T-1")
        self.assertEqual(code, 1)

    def test_repository_name(self):
        self.assertEqual(vendor_lock.repository_name("git@host:team/tool.git"), "tool")
        self.assertEqual(vendor_lock.repository_name("https://h/a/b/"), "b")


if __name__ == "__main__":
    unittest.main()
