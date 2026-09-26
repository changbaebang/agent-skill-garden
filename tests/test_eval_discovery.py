from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BehavioralSuiteDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suites = self.root / "evals/suites"
        self.suites.mkdir(parents=True)
        self.value = {
            "version": 1, "id": "discovery-fixture", "cases": [{
                "id": "case", "split": "calibration", "task": "Review the change.",
                "inputs": {"diff": "- old\n+ new"},
                "checks": [{"id": "check", "criterion": "Cite supporting evidence."}],
            }],
        }

    def validate(self):
        return subprocess.run(
            [sys.executable, "-c",
             "import sys; from pathlib import Path; "
             "from scripts.validate_skill_evals import validate_suites; "
             "raise SystemExit(validate_suites(Path(sys.argv[1])))", str(self.root)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def test_discovers_nested_suites_and_ignores_other_eval_formats(self):
        nested = self.suites / "nested"
        nested.mkdir()
        (nested / "example.json").write_text(json.dumps(self.value), encoding="utf-8")
        (self.root / "evals/routing.json").write_text("[]", encoding="utf-8")
        schemas = self.root / "evals/schemas"
        schemas.mkdir()
        (schemas / "example.json").write_text('{"type": "object"}', encoding="utf-8")
        self.assertEqual(self.validate().returncode, 0)

    def test_misplaced_top_level_suite_fails_with_migration_guidance(self):
        (self.suites / "good.json").write_text(json.dumps(self.value), encoding="utf-8")
        (self.root / "evals/legacy-suite.json").write_text(
            '{"version": 1, "id": "broken-no-cases"}', encoding="utf-8")
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evals/legacy-suite.json", result.stderr)
        self.assertIn("evals/suites/", result.stderr)
        self.assertIn("evals/<kind>/", result.stderr)
        self.assertIn("Registered top-level routing files: routing.json", result.stderr)
        self.assertIn("For a new routing-format definition only", result.stderr)
        self.assertIn("ROUTING_FILES in scripts/validate_evals.py", result.stderr)

    def test_routing_load_failures_use_error_diagnostics_without_tracebacks(self):
        route = self.root / "evals/routing.json"
        for name, content in (("invalid-json", b"{"), ("invalid-utf8", b"\xff"),
                              ("missing", None),
                              ("too-deep", b"[" * 200000 + b"]" * 200000)):
            with self.subTest(name=name):
                if content is None:
                    route.unlink(missing_ok=True)
                    self.assertFalse(route.exists())
                else:
                    route.write_bytes(content)
                result = subprocess.run(
                    [sys.executable, "-c",
                     "import sys; from pathlib import Path; "
                     "from scripts.validate_evals import validate_routes; "
                     "raise SystemExit(validate_routes(Path(sys.argv[1])))", str(self.root)],
                    cwd=ROOT, text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("ERROR: evals/routing.json: cannot load routing definition:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("Validated", result.stdout)

    def test_routing_owner_registration_is_shared_and_validates_each_file(self):
        (self.suites / "good.json").write_text(json.dumps(self.value), encoding="utf-8")
        skill = self.root / "core/skills/example"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("Example skill", encoding="utf-8")
        for index, filename in enumerate(("routes-a.json", "routes-b.json")):
            (self.root / "evals" / filename).write_text(json.dumps([{
                "id": f"route-{index}", "prompt": "Review this change.",
                "expected_skill": "example", "forbidden_actions": ["publish"],
            }]), encoding="utf-8")

        def validate_registered():
            return subprocess.run(
                [sys.executable, "-c",
                 "import sys; from pathlib import Path; "
                 "from scripts import validate_evals, validate_skill_evals; "
                 "validate_evals.ROUTING_FILES = ('routes-a.json', 'routes-b.json'); "
                 "root = Path(sys.argv[1]); "
                 "raise SystemExit(validate_evals.validate_routes(root) or "
                 "validate_skill_evals.validate_suites(root))", str(self.root)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        registered = validate_registered()
        self.assertEqual(registered.returncode, 0, registered.stderr)
        self.assertIn("Validated 2 synthetic routing case definitions", registered.stdout)
        self.assertIn("behavioral cases", registered.stdout)
        (self.root / "evals/routes-b.json").write_text("{}", encoding="utf-8")
        malformed = validate_registered()
        self.assertNotEqual(malformed.returncode, 0)
        self.assertIn("evals/routes-b.json must contain a non-empty array", malformed.stderr)

        for expected_skill in ([], {}):
            with self.subTest(expected_skill=expected_skill):
                (self.root / "evals/routes-b.json").write_text(json.dumps([{
                    "id": "route-1", "prompt": "Review this change.",
                    "expected_skill": expected_skill, "forbidden_actions": ["publish"],
                }]), encoding="utf-8")
                malformed = validate_registered()
                self.assertEqual(malformed.returncode, 1)
                self.assertIn("evals/routes-b.json: case 1: unknown expected skill", malformed.stderr)
                self.assertNotIn("Traceback", malformed.stderr)

    def test_malformed_definition_in_suite_directory_is_not_skipped(self):
        (self.suites / "good.json").write_text(json.dumps(self.value), encoding="utf-8")
        nested = self.suites / "nested"
        nested.mkdir()
        (nested / "bad.json").write_text('{"version": 1, "id": "invalid"}', encoding="utf-8")
        result = self.validate()
        self.assertEqual(result.returncode, 2)
        self.assertIn("ERROR:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_empty_suite_directory_does_not_claim_success(self):
        self.assertNotEqual(self.validate().returncode, 0)

    def test_module_and_direct_script_entrypoints_work_without_path_patching(self):
        for command, cwd in [
            ([sys.executable, "-m", "scripts.validate_skill_evals"], ROOT),
            ([sys.executable, str(ROOT / "scripts/validate_skill_evals.py")], self.root),
        ]:
            with self.subTest(command=command):
                result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("behavioral cases", result.stdout)


if __name__ == "__main__":
    unittest.main()
