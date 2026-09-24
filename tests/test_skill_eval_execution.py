from __future__ import annotations

import importlib.util
import os
import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


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
        self.assertIsNone(result["exit_code"])
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

    def test_successful_and_failed_runners_clean_group_before_supervisor_reap(self):
        real_wait = EVAL.subprocess.Popen.wait
        real_killpg = EVAL.os.killpg
        for exit_code in (0, 7):
            events = []

            def wait(process, *args, **kwargs):
                events.append(("reap-start", process.returncode))
                return real_wait(process, *args, **kwargs)

            def killpg(pid, sig):
                events.append(("signal", sig))
                return real_killpg(pid, sig)

            with self.subTest(exit_code=exit_code), \
                    patch.object(EVAL.subprocess.Popen, "wait", wait), \
                    patch.object(EVAL.os, "killpg", killpg):
                result = self.execute(f"import sys; print('answer'); sys.exit({exit_code})")
                self.assertEqual(result["exit_code"], exit_code)
                self.assertEqual(events, [("signal", signal.SIGKILL), ("reap-start", None)])

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_timeout_signals_group_before_reaping_runner(self):
        events = []
        real_wait = EVAL.subprocess.Popen.wait
        real_killpg = EVAL.os.killpg

        def wait(process, *args, **kwargs):
            code = real_wait(process, *args, **kwargs)
            events.append(("reaped", code))
            return code

        def killpg(pid, sig):
            events.append(("signal", sig))
            return real_killpg(pid, sig)

        with patch.object(EVAL.subprocess.Popen, "wait", wait), \
                patch.object(EVAL.os, "killpg", killpg):
            result = self.execute("import time; time.sleep(10)", timeout=0.2)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(events[0], ("signal", signal.SIGKILL))
        self.assertEqual(events[1], ("reaped", -signal.SIGKILL))
        self.assertEqual(sum(event[0] == "signal" for event in events), 1)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_interruption_signals_group_before_reaping_runner(self):
        events = []
        real_wait = EVAL.subprocess.Popen.wait
        real_killpg = EVAL.os.killpg

        def wait(process, *args, **kwargs):
            code = real_wait(process, *args, **kwargs)
            events.append(("reaped", code))
            return code

        def killpg(pid, sig):
            events.append(("signal", sig))
            return real_killpg(pid, sig)

        with patch.object(EVAL.subprocess.Popen, "wait", wait), \
                patch.object(EVAL.os, "killpg", killpg), \
                patch.object(EVAL.selectors.DefaultSelector, "select", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.execute("import time; time.sleep(10)")
        self.assertEqual(events[0], ("signal", signal.SIGKILL))
        self.assertEqual(events[1], ("reaped", -signal.SIGKILL))
        self.assertEqual(sum(event[0] == "signal" for event in events), 1)

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
    def test_closed_output_pipes_do_not_remove_runner_deadline(self):
        result = self.execute(
            "import os,time; os.close(1); os.close(2); time.sleep(10)", timeout=0.2)
        self.assertEqual(result["status"], "timeout")
        self.assertIsNone(result["exit_code"])
        self.assertLess(result["elapsed_seconds"], 2)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_normal_exit_stops_grandchildren_that_closed_standard_streams(self):
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as folder:
                ready = Path(folder) / "grandchild-ready"
                marker = Path(folder) / "late-write"
                grandchild = (
                    "import os,pathlib,time\n"
                    "for fd in (0,1,2): os.close(fd)\n"
                    f"pathlib.Path({str(ready)!r}).touch()\n"
                    f"time.sleep(1.2); pathlib.Path({str(marker)!r}).touch()\n")
                child = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
                         + repr(grandchild) + "])\n")
                parent = (
                    "import pathlib,subprocess,sys,time\n"
                    f"subprocess.Popen([sys.executable,'-c',{child!r}], "
                    "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                    f"while not pathlib.Path({str(ready)!r}).exists(): time.sleep(.01)\n"
                    f"print('answer'); sys.exit({exit_code})\n")
                result = self.execute(parent)
                self.assertEqual(result["status"], "ok" if exit_code == 0 else "error")
                self.assertEqual(result["exit_code"], exit_code)
                self.assertTrue(ready.exists(), "grandchild must have started before runner exit")
                time.sleep(1.35)
                self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "posix", "file descriptor inheritance requires POSIX")
    def test_runner_does_not_inherit_private_supervisor_status_pipe(self):
        result = self.execute(
            "import os\n"
            "opened=[]\n"
            "for fd in range(3,128):\n"
            "    try: os.fstat(fd)\n"
            "    except OSError: continue\n"
            "    opened.append(fd)\n"
            "print(opened)\n")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["answer"].strip(), "[]")

    @unittest.skipUnless(os.name == "posix", "signals require POSIX")
    def test_runner_signal_exit_is_preserved_separately_from_supervisor_cleanup(self):
        result = self.execute(
            "import os,signal; print('answer',flush=True); os.kill(os.getpid(),signal.SIGTERM)")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], -signal.SIGTERM)

    @unittest.skipUnless(os.name == "posix", "signals require POSIX")
    def test_supervisor_death_without_status_cannot_be_a_successful_answer(self):
        result = self.execute(
            "import os,signal,time; print('answer',flush=True); "
            "os.kill(os.getppid(),signal.SIGTERM); time.sleep(.05)")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("answer", result["answer"])
        self.assertIn("Supervisor exited without a valid runner status", result["error"])
        self.assertLess(result["elapsed_seconds"], 2)

    def test_failed_group_cleanup_is_reported_instead_of_claiming_success(self):
        with patch.object(EVAL.os, "killpg", side_effect=PermissionError("simulated denial")):
            result = self.execute("print('answer')")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("Process-group cleanup failed", result["error"])

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
