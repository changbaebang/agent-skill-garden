from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_eval", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)
SUITE = ROOT / "evals/suites/critical-review.json"


class SkillEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / "suite.json"
        self.suite.write_text(json.dumps({
            "version": 1, "id": "fixture", "cases": [
                {"id": "one", "split": "calibration", "task": "Review this diff.",
                 "inputs": {"diff": "- return a\n+ return b"},
                 "checks": [{"id": "detect", "criterion": "HIDDEN_ORACLE: find the defect."}]},
                {"id": "two", "split": "holdout", "task": "Re-review this diff.",
                 "inputs": {"diff": "- return b\n+ return a"},
                 "checks": [{"id": "fixed", "criterion": "HIDDEN_ORACLE: no finding."}]},
            ]}), encoding="utf-8")
        self.runner = self.root / "runner.py"
        self.runner.write_text(
            "import os,sys\nprompt=sys.stdin.read()\n"
            "assert 'HIDDEN_ORACLE' not in prompt\n"
            "assert 'calibration' not in prompt and 'holdout' not in prompt\n"
            "assert not os.path.exists('suite.json')\n"
            "print('A scripted review, not a model result.')\n", encoding="utf-8")

    def cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return EVAL.main(list(map(str, args)))

    def capture(self, name="before", extra=()):
        path = self.root / f"{name}.json"
        skill = "none"
        if name != "before":
            folder = self.root / "comparison-skill"
            folder.mkdir(exist_ok=True)
            (folder / "SKILL.md").write_text("Use evidence for each finding.")
            skill = str(folder)
        code = self.cli("run", "--suite", self.suite, "--skill", skill, "--label", name,
                        "--model", "scripted", "--environment", "test-fixture-v1", "--synthetic",
                        "--split", "all", "--repeat", "1", "--out", path, *extra,
                        "--", sys.executable, self.runner)
        self.assertEqual(code, 0)
        return path, EVAL.read_run(path)

    def grade(self, record, verdicts):
        value = EVAL.assessment_template(record)
        value["reviewer"] = "fixture-author"
        for row, verdict in zip(value["assessments"], verdicts):
            for check in row["checks"].values():
                check["verdict"] = verdict
                check["note"] = "Scripted evidence for testing the comparison mechanism."
        path = self.root / f"{record['label']}-assessment.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_bundled_suite_matches_documented_six_four_split(self):
        suite = EVAL.suite_at(SUITE)
        counts = {split: sum(c["split"] == split for c in suite["cases"])
                  for split in EVAL.SPLITS}
        self.assertEqual(counts, {"calibration": 6, "holdout": 4})

    def test_run_excludes_oracle_and_records_skill_reference_snapshot(self):
        skill = self.root / "skill"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text("Use references/guide.md", encoding="utf-8")
        (skill / "references/guide.md").write_text("Evidence first.", encoding="utf-8")
        _, record = self.capture(extra=("--skill", skill))
        self.assertEqual([r["status"] for r in record["results"]], ["ok", "ok"])
        self.assertIn("references/guide.md", record["skill"]["files"])
        self.assertNotIn("HIDDEN_ORACLE", EVAL.prompt_for(record["suite"]["cases"][0], record["skill"]))

    def test_missing_judgments_are_inconclusive_never_improved(self):
        _, before = self.capture()
        _, after = self.capture("after")
        report, regression = EVAL.compare(before, after, EVAL.judgments(before, None),
                                           EVAL.judgments(after, None))
        self.assertIn("SYNTHETIC", report)
        self.assertIn("inconclusive=1", report)
        self.assertIn("improved=0", report)
        self.assertFalse(regression)

    def test_comparison_keeps_regression_even_when_another_case_improves(self):
        before_path, before = self.capture()
        after_path, after = self.capture("after")
        a = self.grade(before, ["fail", "pass"])
        b = self.grade(after, ["pass", "fail"])
        out = self.root / "report.md"
        code = self.cli("compare", before_path, after_path, "--before-assessment", a,
                        "--after-assessment", b, "--out", out, "--fail-on-regression")
        self.assertEqual(code, 1)
        self.assertIn("| fail | pass | improved |", out.read_text())
        self.assertIn("| pass | fail | regressed |", out.read_text())
        self.assertIn("holdout: improved=0, regressed=1", out.read_text())

    def test_compatibility_rejects_environment_suite_runner_and_model_drift(self):
        _, before = self.capture()
        _, after = self.capture("after")
        for field in ("harness_sha256", "selected_suite_sha256", "model", "environment", "runner_identity", "repeat", "kind", "split"):
            candidate = dict(after, **{field: "changed"})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                EVAL.compare(before, candidate, EVAL.judgments(before, None),
                             EVAL.judgments(after, None))

    def test_run_edit_or_removed_attempt_is_rejected(self):
        path, record = self.capture()
        record["results"].pop()
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "changed"):
            EVAL.read_run(path)
        record.pop("sha256")
        record["sha256"] = EVAL.digest(record)
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "missing attempts"):
            EVAL.read_run(path)

    def test_stale_judgment_and_changed_criteria_are_rejected(self):
        _, before = self.capture()
        _, after = self.capture("after")
        grades = self.grade(before, ["pass", "pass"])
        with self.assertRaisesRegex(ValueError, "another run"):
            EVAL.judgments(after, grades)
        value = EVAL.load(grades)
        value["assessments"][0]["checks"]["detect"]["criterion"] = "Easier check"
        grades.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "criterion"):
            EVAL.judgments(before, grades)

    def test_a_pass_requires_a_reviewer_and_evidence(self):
        _, run = self.capture()
        path = self.grade(run, ["pass", "pass"])
        value = EVAL.load(path)
        value["reviewer"] = ""
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "reviewer"):
            EVAL.judgments(run, path)
        value["reviewer"] = "person"
        value["assessments"][0]["checks"]["detect"]["note"] = ""
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "evidence"):
            EVAL.judgments(run, path)

    def test_failures_are_retained_and_cannot_be_graded_as_pass(self):
        self.runner.write_text("import sys\nsys.stdin.read()\nsys.exit(3)\n")
        _, run = self.capture()
        self.assertEqual([r["status"] for r in run["results"]], ["error", "error"])
        grades = self.grade(run, ["pass", "pass"])
        with self.assertRaisesRegex(ValueError, "failed runs"):
            EVAL.judgments(run, grades)

    def test_failure_to_success_is_not_automatically_quality_improvement(self):
        self.runner.write_text(
            "import sys,json\nprompt=sys.stdin.read()\n"
            "data=json.loads(prompt.split('\\n\\n',1)[1])\n"
            "if not data['skill']: sys.exit(3)\nprint('answer')\n")
        _, before = self.capture()
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Guidance")
        _, after = self.capture("after", ("--skill", skill))
        grades = self.grade(after, ["pass", "pass"])
        report, _ = EVAL.compare(before, after, EVAL.judgments(before, None),
                                 EVAL.judgments(after, grades))
        self.assertIn("| error | pass | inconclusive |", report)
        self.assertIn("0/2 attempts completed", report)

    def test_runner_script_changes_at_the_same_path_are_incomparable(self):
        _, before = self.capture()
        self.runner.write_text("import sys\nsys.stdin.read()\nprint('different answer')\n")
        _, after = self.capture("after")
        with self.assertRaisesRegex(ValueError, "runner_identity"):
            EVAL.compare(before, after, EVAL.judgments(before, None), EVAL.judgments(after, None))

    def test_runner_keeps_the_selected_python_virtual_environment(self):
        folder = self.root / "venv"
        venv.EnvBuilder(with_pip=False, symlinks=True).create(folder)
        command = [str(folder / "bin/python"), "-c", "import sys; print(sys.prefix)"]
        identity = EVAL.runner_identity(command)
        result = EVAL.execute(identity["command"], "", 5)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(Path(result["answer"].strip()).resolve(), folder.resolve())

    def test_missing_executable_timeout_and_empty_output_are_not_success(self):
        self.assertEqual(EVAL.execute(["/nonexistent-eval-runner"], "prompt", 1)["status"], "error")
        self.assertEqual(EVAL.execute([sys.executable, "-c", "pass"], "prompt", 1)["status"], "error")
        result = EVAL.execute([sys.executable, "-c", "import time; time.sleep(10)"], "prompt", 0.03)
        self.assertEqual(result["status"], "timeout")

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_timeout_stops_descendant_writes(self):
        marker = self.root / "late-write"
        child = "import time,pathlib; time.sleep(.3); pathlib.Path(" + repr(str(marker)) + ").touch()"
        parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(10)"
        result = EVAL.execute([sys.executable, "-c", parent], "prompt", 0.08)
        self.assertEqual(result["status"], "timeout")
        import time
        time.sleep(0.35)
        self.assertFalse(marker.exists())

    def test_excessive_output_cannot_be_scored_as_a_complete_answer(self):
        result = EVAL.execute([sys.executable, "-c", "print('x' * 1000001)"], "", 2)
        self.assertEqual(result["status"], "output_limit")

    def test_symlinked_skill_content_is_rejected(self):
        skill = self.root / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Read reference.md")
        (skill / "reference.md").symlink_to(self.suite)
        with self.assertRaisesRegex(ValueError, "inside"):
            EVAL.skill_at(str(skill))

    def test_duplicate_suite_cases_are_rejected(self):
        suite = EVAL.load(self.suite)
        suite["cases"].append(suite["cases"][0])
        self.suite.write_text(json.dumps(suite))
        self.assertEqual(self.cli("validate", self.suite), 2)

    def test_outputs_do_not_overwrite_existing_results(self):
        path, _ = self.capture()
        original = path.read_bytes()
        self.assertEqual(self.cli("assess", path, "--out", path), 2)
        self.assertEqual(path.read_bytes(), original)

    def test_negative_or_nan_review_time_is_rejected(self):
        _, record = self.capture()
        grades = self.grade(record, ["pass", "pass"])
        value = EVAL.load(grades)
        for invalid in (-1, float("nan"), True):
            value["assessments"][0]["review_minutes"] = invalid
            grades.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                EVAL.judgments(record, grades)


if __name__ == "__main__":
    unittest.main()
