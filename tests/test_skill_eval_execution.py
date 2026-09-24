from __future__ import annotations

import importlib.util
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_eval", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class SkillEvaluationExecutionTests(unittest.TestCase):
    def execute(self, code, timeout=3, prompt=""):
        return EVAL.execute([sys.executable, "-c", code], prompt, timeout)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_large_stdout_does_not_hide_timeout(self):
        result = self.execute(
            "import sys,time; sys.stdout.write('x' * 1000001); "
            "sys.stdout.flush(); time.sleep(10)", timeout=0.5)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["exit_code"], -signal.SIGKILL)
        self.assertEqual(len(result["answer"]), EVAL.MAX_OUTPUT)
        self.assertTrue(result["stdout_truncated"])
        self.assertFalse(result["stderr_truncated"])

    def test_large_stdout_does_not_hide_nonzero_exit(self):
        result = self.execute(
            "import sys; sys.stdout.write('x' * 1000001); sys.exit(7)")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], 7)
        self.assertTrue(result["stdout_truncated"])

    def test_successful_oversized_answer_still_hits_output_limit(self):
        result = self.execute("import sys; sys.stdout.write('x' * 1000001)")
        self.assertEqual(result["status"], "output_limit")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["stdout_truncated"])
        self.assertEqual(len(result["answer"]), EVAL.MAX_OUTPUT)

    def test_answer_exactly_at_limit_is_complete(self):
        result = self.execute("import sys; sys.stdout.write('x' * 1000000)")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["stdout_truncated"])
        self.assertEqual(len(result["answer"]), EVAL.MAX_OUTPUT)

    def test_long_stderr_keeps_final_failure_reason(self):
        result = self.execute(
            "import sys; sys.stderr.write('INITIAL_HEADER\\n' + 'noise' * 4000 + "
            "'\\nAuthentication failed: expired token\\n'); sys.exit(3)")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], 3)
        self.assertTrue(result["stderr_truncated"])
        self.assertEqual(len(result["error"].encode()), EVAL.MAX_STDERR)
        self.assertNotIn("INITIAL_HEADER", result["error"])
        self.assertTrue(result["error"].endswith("Authentication failed: expired token\n"))

    def test_stderr_exactly_at_limit_is_not_truncated(self):
        result = self.execute("import sys; sys.stderr.write('x' * 8192); print('answer')")
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["stderr_truncated"])
        self.assertEqual(result["error"], "x" * EVAL.MAX_STDERR)

    def test_missing_executable_has_no_truncated_streams(self):
        result = EVAL.execute(["/nonexistent-eval-runner"], "", 1)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertFalse(result["stdout_truncated"])
        self.assertFalse(result["stderr_truncated"])

    @unittest.skipUnless(os.name == "posix", "file-size resource limits require POSIX")
    def test_large_streams_do_not_use_unbounded_disk_capture(self):
        # A file-backed capture would hit this limit before either stream was
        # complete. Pipes still permit the final stderr diagnostic to arrive.
        result = self.execute(
            "import resource,sys; "
            "resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536)); "
            "sys.stdout.write('x' * 4000000); "
            "sys.stderr.write('noise' * 800000 + '\\nFINAL_DIAGNOSTIC\\n')")
        self.assertEqual(result["status"], "output_limit")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(len(result["answer"]), EVAL.MAX_OUTPUT)
        self.assertEqual(len(result["error"].encode()), EVAL.MAX_STDERR)
        self.assertTrue(result["error"].endswith("FINAL_DIAGNOSTIC\n"))
        self.assertTrue(result["stdout_truncated"])
        self.assertTrue(result["stderr_truncated"])

    def test_output_is_drained_while_large_prompt_waits_to_be_read(self):
        prompt = "request-data\n" * 100000
        result = self.execute(
            "import sys; sys.stdout.write('x' * 2000000); sys.stdout.flush(); "
            "sys.stderr.write('noise' * 400000); sys.stderr.flush(); "
            f"assert len(sys.stdin.read()) == {len(prompt)}; "
            "sys.stderr.write('\\nPROMPT_RECEIVED\\n')", prompt=prompt)
        self.assertEqual(result["status"], "output_limit")
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["error"].endswith("PROMPT_RECEIVED\n"))
        self.assertEqual(len(result["answer"]), EVAL.MAX_OUTPUT)
        self.assertEqual(len(result["error"].encode()), EVAL.MAX_STDERR)

    def test_runner_that_never_reads_stdin_still_times_out(self):
        result = self.execute(
            "import sys,time; print('started', flush=True); time.sleep(10)",
            timeout=0.3, prompt="x" * 2000000)
        self.assertEqual(result["status"], "timeout")
        self.assertIn("started", result["answer"])
        self.assertLess(result["elapsed_seconds"], 2)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_inherited_output_pipes_cannot_outlive_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / "orphan-write"
            child = ("import time,pathlib; time.sleep(.7); pathlib.Path("
                     + repr(str(marker)) + ").touch()")
            parent = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
                      + repr(child) + "]); print('parent exited')")
            result = self.execute(parent, timeout=0.3)
            self.assertEqual(result["status"], "timeout")
            self.assertEqual(result["exit_code"], 0)
            self.assertLess(result["elapsed_seconds"], 2)
            time.sleep(0.6)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
