from __future__ import annotations

import copy
import json
import unittest

import test_skill_eval as fixture


EVAL = fixture.EVAL


class SkillEvaluationComparisonTests(unittest.TestCase):
    def setUp(self):
        # Compose the existing real CLI fixture without inheriting its tests or
        # exposing a second TestCase class for unittest discovery.
        self.fixture = fixture.SkillEvaluationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def grade(self, record, name, verdicts):
        value = EVAL.assessment_template(record)
        self.assertEqual(len(value["assessments"]), len(verdicts))
        value["reviewer"] = "scripted-mechanism-check"
        for row, verdict in zip(value["assessments"], verdicts):
            for check in row["checks"].values():
                check["verdict"] = verdict
                check["note"] = "Synthetic fixture judgment; not evidence of model quality."
        path = self.root / f"{name}-assessment.json"
        EVAL.save(path, value)
        return path

    def compare_unjudged(self, before, after):
        return EVAL.compare(before, after, EVAL.judgments(before, None),
                            EVAL.judgments(after, None))

    def test_same_capture_with_conflicting_grades_is_rejected(self):
        path, record = self.fixture.capture()
        before_grades = self.grade(record, "fail", ["fail", "fail"])
        after_grades = self.grade(record, "pass", ["pass", "pass"])
        with self.assertRaisesRegex(ValueError, "same captured run"):
            EVAL.compare(record, EVAL.read_run(path), EVAL.judgments(record, before_grades),
                         EVAL.judgments(record, after_grades))
        report = self.root / "same-run.md"
        self.assertEqual(self.fixture.cli(
            "compare", path, path, "--before-assessment", before_grades,
            "--after-assessment", after_grades, "--out", report), 2)
        self.assertFalse(report.exists())

    def test_fresh_runs_with_identical_skill_content_are_rejected(self):
        _, before = self.fixture.capture()
        _, after = self.fixture.capture("after", ("--skill", "none"))
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["skill"]["files"], after["skill"]["files"])
        with self.assertRaisesRegex(ValueError, "identical skill content"):
            self.compare_unjudged(before, after)

    def test_renaming_the_skill_directory_cannot_bypass_content_check(self):
        first = self.root / "first-skill-name"
        second = self.root / "second-skill-name"
        for folder in (first, second):
            folder.mkdir()
            (folder / "SKILL.md").write_text("Same guidance and references.\n", encoding="utf-8")
        _, before = self.fixture.capture(extra=("--skill", first))
        _, after = self.fixture.capture("after", ("--skill", second))
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertNotEqual(before["skill_sha256"], after["skill_sha256"])
        self.assertEqual(before["skill"]["files"], after["skill"]["files"])
        self.assertEqual([row["prompt_sha256"] for row in before["results"]],
                         [row["prompt_sha256"] for row in after["results"]])
        with self.assertRaisesRegex(ValueError, "identical skill content"):
            self.compare_unjudged(before, after)

    def test_fresh_runs_with_changed_skill_content_are_comparable(self):
        _, before = self.fixture.capture()
        _, after = self.fixture.capture("after")
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertNotEqual(before["skill"]["files"], after["skill"]["files"])
        report, regressed = self.compare_unjudged(before, after)
        self.assertFalse(regressed)
        self.assertIn("SYNTHETIC", report)
        self.assertIn("inconclusive=1", report)
        self.assertIn("improved=0", report)

    def test_unselected_holdout_changes_preserve_calibration_comparison(self):
        _, before = self.fixture.capture(extra=("--split", "calibration"))
        initial_suite = EVAL.load(self.fixture.suite)
        for operation in ("addition", "edit"):
            with self.subTest(operation=operation):
                suite = copy.deepcopy(initial_suite)
                if operation == "addition":
                    case = copy.deepcopy(suite["cases"][1])
                    case["id"] = "new-holdout"
                    suite["cases"].insert(0, case)
                else:
                    case = suite["cases"][1]
                    case["task"] = "Inspect a new untouched example."
                    case["inputs"]["diff"] = "+ return untrustedInput"
                    case["checks"][0]["criterion"] = "A new holdout-only criterion."
                self.fixture.suite.write_text(json.dumps(suite), encoding="utf-8")
                _, after = self.fixture.capture(operation, ("--split", "calibration"))
                self.assertNotEqual(before["suite_sha256"], after["suite_sha256"])
                self.assertEqual(before["selected_suite_sha256"], after["selected_suite_sha256"])
                report, regressed = self.compare_unjudged(before, after)
                self.assertFalse(regressed)
                self.assertIn(before["suite_sha256"], report)
                self.assertIn(after["suite_sha256"], report)
                self.assertIn("holdout: not selected", report)

    def test_selected_case_changes_reject_comparison(self):
        _, before = self.fixture.capture(extra=("--split", "calibration"))
        initial_suite = EVAL.load(self.fixture.suite)
        for operation in ("task", "input", "criterion", "additional-case"):
            with self.subTest(operation=operation):
                suite = copy.deepcopy(initial_suite)
                case = suite["cases"][0]
                if operation == "task":
                    case["task"] = "Only inspect authorization changes."
                elif operation == "input":
                    case["inputs"]["diff"] = "+ return untrustedInput"
                elif operation == "criterion":
                    case["checks"][0]["criterion"] = "HIDDEN_ORACLE: a different requirement."
                else:
                    case = copy.deepcopy(case)
                    case["id"] = "additional-calibration"
                    suite["cases"].append(case)
                self.fixture.suite.write_text(json.dumps(suite), encoding="utf-8")
                _, after = self.fixture.capture(operation, ("--split", "calibration"))
                self.assertNotEqual(before["selected_suite_sha256"], after["selected_suite_sha256"])
                with self.assertRaisesRegex(ValueError, "selected_suite_sha256"):
                    self.compare_unjudged(before, after)

    def test_holdout_addition_is_incomparable_when_all_cases_were_selected(self):
        _, before = self.fixture.capture()
        suite = EVAL.load(self.fixture.suite)
        additional = copy.deepcopy(suite["cases"][1])
        additional["id"] = "additional-holdout"
        suite["cases"].append(additional)
        self.fixture.suite.write_text(json.dumps(suite), encoding="utf-8")
        _, after = self.fixture.capture("after")
        with self.assertRaisesRegex(ValueError, "selected_suite_sha256"):
            self.compare_unjudged(before, after)

    def test_unchanged_passes_and_failures_have_separate_rows_and_counts(self):
        _, before = self.fixture.capture()
        _, after = self.fixture.capture("after")
        left = self.grade(before, "before", ["pass", "fail"])
        right = self.grade(after, "after", ["pass", "fail"])
        report, regressed = EVAL.compare(before, after, EVAL.judgments(before, left),
                                         EVAL.judgments(after, right))
        self.assertFalse(regressed)
        self.assertIn("| pass | pass | unchanged_pass |", report)
        self.assertIn("| fail | fail | unchanged_fail |", report)
        self.assertIn("calibration: improved=0, regressed=0, unchanged_pass=1, unchanged_fail=0", report)
        self.assertIn("holdout: improved=0, regressed=0, unchanged_pass=0, unchanged_fail=1", report)
        self.assertNotIn("unchanged=", report)

    def test_all_unchanged_failures_exit_zero_without_claiming_quality_pass(self):
        before_path, before = self.fixture.capture()
        after_path, after = self.fixture.capture("after")
        left = self.grade(before, "before", ["fail", "fail"])
        right = self.grade(after, "after", ["fail", "fail"])
        output = self.root / "all-fail.md"
        self.assertEqual(self.fixture.cli(
            "compare", before_path, after_path, "--before-assessment", left,
            "--after-assessment", right, "--out", output, "--fail-on-regression"), 0)
        report = output.read_text(encoding="utf-8")
        self.assertEqual(report.count("| fail | fail | unchanged_fail |"), 2)
        self.assertEqual(report.count("unchanged_pass=0, unchanged_fail=1"), 2)
        self.assertIn("A lack of new regressions is not a quality pass", report)


if __name__ == "__main__":
    unittest.main()
