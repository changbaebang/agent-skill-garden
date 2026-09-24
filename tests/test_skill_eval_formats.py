from __future__ import annotations

import contextlib
import io
import json
import unittest

import test_skill_eval as fixture


EVAL = fixture.EVAL
LEGACY = fixture.ROOT / "tests/fixtures/garden-eval"


class SkillEvaluationFormatTests(fixture.SkillEvaluationFixture, unittest.TestCase):
    def test_legacy_captures_can_be_assessed_without_changing_evidence(self):
        for source in sorted(LEGACY.glob("run-v1-*.json")):
            with self.subTest(source=source.name):
                original_bytes = source.read_bytes()
                original = json.loads(original_bytes)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    record = EVAL.read_run(source)
                self.assertIn("legacy run version 1", stderr.getvalue())
                self.assertEqual(record, original)
                self.assertEqual(source.read_bytes(), original_bytes)
                self.assertEqual([row["case_id"] for row in record["results"]], ["z-last", "a-first"])
                output = self.root / (source.stem + "-assessment.json")
                self.assertEqual(self.cli("assess", source, "--out", output), 0)
                assessment = json.loads(output.read_text())
                self.assertEqual(assessment["run_sha256"], original["sha256"])
                self.assertEqual(assessment["version"], 1)
                self.assertEqual(len(EVAL.judgments(record, output)), 2)

    def test_legacy_evidence_and_recorded_selection_hash_still_reject_edits(self):
        for filename, field in (("run-v1-before-selection.json", "answer"),
                                ("run-v1-with-selection.json", "selected_suite_sha256")):
            with self.subTest(field=field):
                record = json.loads((LEGACY / filename).read_text())
                if field == "answer":
                    record["results"][0]["answer"] = "Changed after capture"
                else:
                    record[field] = "0" * 64
                    record.pop("sha256")
                    record["sha256"] = EVAL.digest(record)
                output = self.root / filename
                output.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, "changed after capture|selected suite hash mismatch"):
                    EVAL.read_run(output)

    def test_new_capture_uses_run_version_two_and_keeps_other_formats_at_one(self):
        _, record = self.capture()
        self.assertEqual(record["version"], 2)
        self.assertEqual(record["suite"]["version"], 1)
        self.assertEqual(EVAL.assessment_template(record)["version"], 1)
        record.pop("selected_suite_sha256")
        record.pop("sha256")
        record["sha256"] = EVAL.digest(record)
        output = self.root / "missing-selection.json"
        output.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "selected suite hash mismatch"):
            EVAL.read_run(output)

    def test_unsupported_format_is_reported_as_version_error(self):
        record = json.loads((LEGACY / "run-v1-before-selection.json").read_text())
        record["version"] = 999
        record.pop("sha256")
        record["sha256"] = EVAL.digest(record)
        output = self.root / "future-format.json"
        output.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "unsupported run version 999"):
            EVAL.read_run(output)

    def test_legacy_capture_cannot_be_compared_with_a_new_harness(self):
        with contextlib.redirect_stderr(io.StringIO()):
            old = EVAL.read_run(LEGACY / "run-v1-before-selection.json")
        _, current = self.capture()
        with self.assertRaisesRegex(ValueError, "version|harness_sha256"):
            EVAL.compare(old, current, EVAL.judgments(old, None), EVAL.judgments(current, None))


if __name__ == "__main__":
    unittest.main()
