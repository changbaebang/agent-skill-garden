import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    REPO_ROOT / "core/skills/affected-verification/scripts/classify_test_summary.py"
)
SPEC = importlib.util.spec_from_file_location("classify_test_summary", MODULE_PATH)
assert SPEC and SPEC.loader
CLASSIFY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CLASSIFY
SPEC.loader.exec_module(CLASSIFY)


PASS_LOG = """
PASS packages/one/src/a.test.ts
Test Suites: 18 passed, 18 total
Tests:       245 passed, 245 total
Snapshots:   0 total
"""

ASSERTION_LOG = """
FAIL packages/one/src/a.test.ts
  expect(received).toBe(expected)
Test Suites: 1 failed, 17 passed, 18 total
Tests:       3 failed, 242 passed, 245 total
"""

CRASH_LOG = """
FAIL packages/two/src/b.test.ts
  Test suite failed to run
Test Suites: 1 failed, 17 passed, 18 total
Tests:       245 passed, 245 total
"""

SIGNAL_LOG = """
A worker process has quit unexpectedly! Most likely this is an initialization error.
Test Suites: 18 passed, 18 total
Tests:       245 passed, 245 total
"""

MULTI_BLOCK_LOG = """
app-a:test: Test Suites: 4 passed, 4 total
app-a:test: Tests:       40 passed, 40 total
app-b:test: Test Suites: 1 failed, 2 passed, 3 total
app-b:test: Tests:       30 passed, 30 total
app-c:test: Test Suites: 2 passed, 2 total
app-c:test: Tests:       1 failed, 19 passed, 20 total
"""

PIPE_SEPARATED_LOG = """
 Test Files  1 failed | 17 passed (18)
      Tests  245 passed (245)
"""

NO_SUMMARY_LOG = """
> runner run test --affected
sh: tsc: command not found
ERROR  command finished with error
"""


class ClassifyTests(unittest.TestCase):
    """Failed suites with zero failed tests is a crash, never a code failure."""

    def test_clean_run_is_pass(self) -> None:
        result = CLASSIFY.classify(PASS_LOG)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["tests"]["passed"], 245)
        self.assertEqual(result["suites"]["total"], 18)

    def test_failed_tests_are_assertion_failures(self) -> None:
        result = CLASSIFY.classify(ASSERTION_LOG)
        self.assertEqual(result["verdict"], "assertion-failure")
        self.assertEqual(result["tests"]["failed"], 3)

    def test_failed_suite_with_zero_failed_tests_is_crash(self) -> None:
        result = CLASSIFY.classify(CRASH_LOG)
        self.assertEqual(result["verdict"], "suite-crash")
        self.assertEqual(result["suites"]["failed"], 1)
        self.assertEqual(result["tests"]["failed"], 0)

    def test_crash_signal_without_failed_suite_is_crash(self) -> None:
        result = CLASSIFY.classify(SIGNAL_LOG)
        self.assertEqual(result["verdict"], "suite-crash")
        self.assertIn("worker process has quit unexpectedly", result["crash_signals"])

    def test_monorepo_blocks_are_summed_and_any_failed_test_wins(self) -> None:
        # Prefixed lines from a task runner must still be read; app-b crashed,
        # app-c has a real failure, so the whole run is an assertion failure.
        result = CLASSIFY.classify(MULTI_BLOCK_LOG)
        self.assertEqual(result["summary_blocks"], 3)
        self.assertEqual(result["suites"]["failed"], 1)
        self.assertEqual(result["tests"]["failed"], 1)
        self.assertEqual(result["tests"]["total"], 90)
        self.assertEqual(result["verdict"], "assertion-failure")

    def test_pipe_separated_summary_is_read(self) -> None:
        result = CLASSIFY.classify(PIPE_SEPARATED_LOG)
        self.assertEqual(result["verdict"], "suite-crash")
        self.assertEqual(result["suites"]["total"], 18)
        self.assertEqual(result["tests"]["total"], 245)

    def test_no_summary_is_unknown_not_pass(self) -> None:
        result = CLASSIFY.classify(NO_SUMMARY_LOG)
        self.assertEqual(result["verdict"], "unknown")

    def test_empty_input_is_unknown(self) -> None:
        self.assertEqual(CLASSIFY.classify("")["verdict"], "unknown")


class CommandLineTests(unittest.TestCase):
    def run_script(self, text: str, *extra: str) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as handle:
            handle.write(text)
            path = handle.name
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), path, *extra],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_exit_codes_follow_verdict(self) -> None:
        self.assertEqual(self.run_script(PASS_LOG).returncode, 0)
        self.assertEqual(self.run_script(ASSERTION_LOG).returncode, 1)
        self.assertEqual(self.run_script(CRASH_LOG).returncode, 2)
        self.assertEqual(self.run_script(NO_SUMMARY_LOG).returncode, 3)

    def test_text_output_names_verdict_and_next_action(self) -> None:
        result = self.run_script(CRASH_LOG)
        self.assertIn("verdict: suite-crash", result.stdout)
        self.assertIn("lower concurrency", result.stdout)

    def test_json_output_is_parseable(self) -> None:
        result = self.run_script(ASSERTION_LOG, "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "assertion-failure")

    def test_stdin_is_read_when_no_path_given(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH)],
            input=PASS_LOG,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("verdict: pass", result.stdout)


if __name__ == "__main__":
    unittest.main()
