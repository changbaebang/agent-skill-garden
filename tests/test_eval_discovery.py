from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
    SPEC = importlib.util.spec_from_file_location(
        "validate_skill_evals", ROOT / "scripts/validate_skill_evals.py")
    assert SPEC and SPEC.loader
    DISCOVERY = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(DISCOVERY)


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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return DISCOVERY.validate_suites(self.root)

    def test_discovers_nested_suites_and_ignores_other_eval_formats(self):
        nested = self.suites / "nested"
        nested.mkdir()
        (nested / "example.json").write_text(json.dumps(self.value), encoding="utf-8")
        (self.root / "evals/routing.json").write_text("[]", encoding="utf-8")
        (self.root / "evals/captured-run.json").write_text("{not suite JSON", encoding="utf-8")
        self.assertEqual(self.validate(), 0)

    def test_malformed_definition_in_suite_directory_is_not_skipped(self):
        (self.suites / "good.json").write_text(json.dumps(self.value), encoding="utf-8")
        nested = self.suites / "nested"
        nested.mkdir()
        (nested / "bad.json").write_text('{"version": 1, "id": "invalid"}', encoding="utf-8")
        self.assertNotEqual(self.validate(), 0)

    def test_empty_suite_directory_does_not_claim_success(self):
        self.assertNotEqual(self.validate(), 0)


if __name__ == "__main__":
    unittest.main()
