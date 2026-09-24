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

    def test_malformed_definition_in_suite_directory_is_not_skipped(self):
        (self.suites / "good.json").write_text(json.dumps(self.value), encoding="utf-8")
        nested = self.suites / "nested"
        nested.mkdir()
        (nested / "bad.json").write_text('{"version": 1, "id": "invalid"}', encoding="utf-8")
        self.assertNotEqual(self.validate().returncode, 0)

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
