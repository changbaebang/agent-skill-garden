import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/quality-gate-triage/scripts/gate_log_triage.py"
SPEC = importlib.util.spec_from_file_location("gate_log_triage", MODULE_PATH)
assert SPEC and SPEC.loader
TRIAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TRIAGE
SPEC.loader.exec_module(TRIAGE)


FAILED_LOG = """\
gate\tRun gate check\t2026-01-01T00:00:00Z Fetching analysis for commit abc123
gate\tRun gate check\t2026-01-01T00:00:05Z QUALITY GATE STATUS: FAILED
gate\tRun gate check\t2026-01-01T00:00:05Z - Coverage on New Code: 41.2% is less than 80%
gate\tRun gate check\t2026-01-01T00:00:05Z - Duplicated Lines on New Code: 7.1% is greater than 3%
"""

TIMEOUT_LOG = """\
gate\tRun gate check\t2026-01-01T00:00:00Z Report uploaded, waiting for analysis
gate\tRun gate check\t2026-01-01T00:05:00Z Polling timeout reached for waiting for finishing of the analysis!
gate\tRun gate check\t2026-01-01T00:05:00Z ##[error]Quality Gate check failed
"""

PASSED_LOG = """\
gate\tRun gate check\t2026-01-01T00:00:00Z \x1b[32mQuality Gate passed\x1b[0m
"""

UNKNOWN_LOG = """\
scan\tRun scanner\t2026-01-01T00:00:00Z ANALYSIS SUCCESSFUL
scan\tRun scanner\t2026-01-01T00:00:01Z pollingTimeoutSec: 300
"""


class ClassifyTest(unittest.TestCase):
    def classify(self, text: str):
        return TRIAGE.classify_lines(text.splitlines())

    def test_failed_verdict_keeps_its_conditions(self) -> None:
        verdict, evidence = self.classify(FAILED_LOG)
        self.assertEqual(verdict, "failed")
        kinds = [kind for kind, _number, _text in evidence]
        self.assertEqual(kinds, ["failed", "condition", "condition"])
        self.assertEqual(evidence[0][1], 2)

    def test_timeout_wins_over_the_error_it_causes(self) -> None:
        verdict, evidence = self.classify(TIMEOUT_LOG)
        self.assertEqual(verdict, "no-verdict")
        self.assertEqual([kind for kind, _n, _t in evidence], ["incomplete", "failed"])
        self.assertEqual(evidence[0][1], 2)

    def test_passed_strips_ansi_colour(self) -> None:
        verdict, evidence = self.classify(PASSED_LOG)
        self.assertEqual(verdict, "passed")
        self.assertNotIn("\x1b", evidence[0][2])

    def test_scan_success_and_config_echo_are_not_a_verdict(self) -> None:
        verdict, evidence = self.classify(UNKNOWN_LOG)
        self.assertEqual(verdict, "unknown")
        self.assertEqual(evidence, [])

    def test_passed_next_to_failed_is_conflicting(self) -> None:
        verdict, _evidence = self.classify("Quality Gate passed\nQuality gate status: FAILED\n")
        self.assertEqual(verdict, "conflicting")

    def test_condition_lines_do_not_leak_into_other_verdicts(self) -> None:
        verdict, evidence = self.classify("coverage threshold is 80%\nQuality Gate passed\n")
        self.assertEqual(verdict, "passed")
        self.assertEqual([kind for kind, _n, _t in evidence], ["passed"])

    def test_pattern_override_replaces_one_group_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            patterns = Path(directory) / "patterns.json"
            patterns.write_text('{"passed": ["gate verdict: GREEN"]}', encoding="utf-8")
            compiled = TRIAGE.load_patterns(str(patterns))
            verdict, _evidence = TRIAGE.classify_lines(["gate verdict: GREEN"], compiled)
            self.assertEqual(verdict, "passed")
            verdict, _evidence = TRIAGE.classify_lines(["Quality Gate passed"], compiled)
            self.assertEqual(verdict, "unknown")
            verdict, _evidence = TRIAGE.classify_lines(["Polling timeout reached"], compiled)
            self.assertEqual(verdict, "no-verdict")

    def test_unknown_pattern_group_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            patterns = Path(directory) / "patterns.json"
            patterns.write_text('{"mystery": ["x"]}', encoding="utf-8")
            with self.assertRaises(ValueError):
                TRIAGE.load_patterns(str(patterns))


class TallyTest(unittest.TestCase):
    def tally(self, text: str, branch=None):
        return TRIAGE.tally_runs(TRIAGE.parse_runs(text.splitlines()), branch)

    def test_repo_wide_when_two_or_more_branches_miss_a_verdict(self) -> None:
        rows = (
            "1\tfeature/a\taaa\tno-verdict\n"
            "2\tfeature/b\tbbb\tno-verdict\n"
            "3\tfeature/c\tccc\tpassed\n"
        )
        result = self.tally(rows, "feature/a")
        self.assertEqual(result["reading"], "repo-wide")
        self.assertEqual(result["runs_no_verdict"], 2)
        self.assertEqual(result["branches_no_verdict"], 2)
        self.assertEqual(result["per_branch"]["feature/c"], (0, 1))

    def test_branch_local_when_only_the_triaged_branch_misses(self) -> None:
        rows = "1\tfeature/a\taaa\tno-verdict\n2\tfeature/b\tbbb\tpassed\n"
        self.assertEqual(self.tally(rows, "feature/a")["reading"], "branch-local")
        self.assertEqual(self.tally(rows, "feature/b")["reading"], "single-branch")
        self.assertEqual(self.tally(rows)["reading"], "single-branch")

    def test_none_when_every_run_has_a_verdict(self) -> None:
        rows = "1\tfeature/a\taaa\tpassed\n2\tfeature/b\tbbb\tfailed\n"
        self.assertEqual(self.tally(rows)["reading"], "none")

    def test_duplicate_commits_are_counted_once_per_commit(self) -> None:
        rows = (
            "1\tfeature/a\taaa\tno-verdict\n"
            "2\tfeature/a\taaa\tno-verdict\n"
            "3\tfeature/a\taaa\tpassed\n"
            "4\tfeature/b\tbbb\tpassed\n"
        )
        self.assertEqual(self.tally(rows)["duplicate_commits"], 1)

    def test_three_column_rows_and_comments_are_accepted(self) -> None:
        rows = "# run\tbranch\tverdict\n1\tfeature/a\tno-verdict\n\n2\tfeature/a\tpassed\n"
        result = self.tally(rows)
        self.assertEqual(result["runs_total"], 2)
        self.assertEqual(result["duplicate_commits"], 0)

    def test_malformed_row_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            TRIAGE.parse_runs(["only-one-column"])


class CommandLineTest(unittest.TestCase):
    def run_script(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *args],
            input=stdin,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_classify_reads_stdin_and_prints_verdict_first(self) -> None:
        result = self.run_script("classify", stdin=TIMEOUT_LOG)
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], "verdict\tno-verdict")
        self.assertTrue(lines[1].startswith("incomplete\t2\t"))

    def test_tally_reads_a_file_and_renders_per_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runs = Path(directory) / "runs.tsv"
            runs.write_text("1\tfeature/a\taaa\tno-verdict\n2\tfeature/b\tbbb\tno-verdict\n", encoding="utf-8")
            result = self.run_script("tally", "--runs", str(runs), "--branch", "feature/a")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("reading\trepo-wide\n", result.stdout)
            self.assertIn("branch\tfeature/a\t1/1\n", result.stdout)

    def test_missing_file_exits_two(self) -> None:
        result = self.run_script("classify", "--log", "/nonexistent/gate.log")
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
