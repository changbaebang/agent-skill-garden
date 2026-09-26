from __future__ import annotations

import importlib.util
import json
import os
import select
import signal
import subprocess
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
        return EVAL.execute([sys.executable, "-c", code], prompt, timeout, sys.executable)

    def execute_with_supervisor_change(self, transform, code="print('answer')", timeout=2):
        real_popen = EVAL.subprocess.Popen

        def spawn(command, *args, **kwargs):
            command = command[:]
            command[3] = transform(command[3])
            return real_popen(command, *args, **kwargs)

        with patch.object(EVAL.subprocess, "Popen", side_effect=spawn):
            return self.execute(code, timeout=timeout)

    def test_completion_pipe_descriptors_do_not_alias_standard_streams(self):
        def transform(source):
            line = "completed, notify = os.pipe()"
            self.assertIn(line, source)
            return source.replace(line, line +
                "\n            assert min(completed, notify) >= 3, (completed, notify)", 1)

        result = self.execute_with_supervisor_change(transform)
        self.assertEqual(result["status"], "ok", result["error"])
        self.assertEqual(result["exit_code"], 0)

    def test_completion_eof_without_outcome_is_reported_without_spinning(self):
        def transform(source):
            start = source.index("            def wait_for_runner():")
            end = source.index("            events.register(completed", start)
            return (source[:start] + "            def wait_for_runner():\n"
                    "                os.close(notify)\n" + source[end:])

        result = self.execute_with_supervisor_change(transform, timeout=.8)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("Runner completion notification without an outcome", result["error"])

    def test_unexpected_completion_bytes_are_consumed_and_reported(self):
        def transform(source):
            start = source.index("            def wait_for_runner():")
            end = source.index("            events.register(completed", start)
            return (source[:start] + "            def wait_for_runner():\n"
                    "                os.write(notify, b'unexpected')\n"
                    "                os.close(notify)\n" + source[end:])

        result = self.execute_with_supervisor_change(transform, timeout=.8)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("Unexpected runner completion notification data", result["error"])

    def test_notification_close_failure_has_a_bounded_diagnostic_fallback(self):
        def transform(source):
            marker = "control = int(sys.argv[1])"
            self.assertIn(marker, source)
            return source.replace(marker,
                "real_close = os.close\n"
                "def failed_notify_close(fd):\n"
                "    if fd == globals().get('notify'):\n"
                "        raise OSError('notify-close-marker')\n"
                "    return real_close(fd)\n"
                "os.close = failed_notify_close\n" + marker, 1)

        result = self.execute_with_supervisor_change(
            transform, "import time; time.sleep(.05); print('answer')", timeout=.8)
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("Runner completion notification failed", result["error"])
        self.assertIn("notify-close-marker", result["error"])

    @unittest.skipUnless(os.name == "posix", "signals require POSIX")
    def test_sigint_after_control_write_never_appends_a_second_json(self):
        real_read = EVAL.os.read
        for mode in ("full", "partial"):
            chunks = []

            def capture_read(fd, size):
                block = real_read(fd, size)
                if block.startswith(b'{"exit_'):
                    chunks.append(block)
                return block

            def transform(source):
                marker = "control = int(sys.argv[1])"
                self.assertIn(marker, source)
                return source.replace(marker,
                    "real_write = os.write\n"
                    "interrupted_write = False\n"
                    "def interrupt_control_write(fd, data):\n"
                    "    global interrupted_write\n"
                    "    if fd == control and not interrupted_write:\n"
                    "        interrupted_write = True\n"
                    f"        payload = data if {mode!r} == 'full' else data[:8]\n"
                    "        count = real_write(fd, payload)\n"
                    "        os.kill(os.getpid(), signal.SIGINT)\n"
                    "        return count\n"
                    "    return real_write(fd, data)\n"
                    "os.write = interrupt_control_write\n" + marker, 1)

            with self.subTest(mode=mode), patch.object(EVAL.os, "read", capture_read):
                result = self.execute_with_supervisor_change(transform)
                captured = b"".join(chunks)
                self.assertEqual(result["answer"].strip(), "answer")
                if mode == "full":
                    self.assertEqual(json.loads(captured), {"exit_code": 0, "error": ""})
                    self.assertEqual(result["exit_code"], 0)
                    self.assertNotIn("No valid runner exit status", result["error"])
                    # macOS can reject killpg against the already-dead leader.
                    # Preserve the runner record without hiding cleanup errors.
                    if result["status"] == "error":
                        self.assertIn("Process-group cleanup failed", result["error"])
                    else:
                        self.assertEqual(result["status"], "ok")
                else:
                    self.assertEqual(captured, b'{"exit_c')
                    self.assertEqual(result["status"], "error")
                    self.assertIsNone(result["exit_code"])
                    self.assertIn("No valid runner exit status", result["error"])

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
        result = EVAL.execute(["/nonexistent-eval-runner"], "", 1, sys.executable)
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
        self.assertIn("No valid runner exit status was received", result["error"])
        self.assertLess(result["elapsed_seconds"], 2)

    def test_failed_group_cleanup_is_reported_instead_of_claiming_success(self):
        with patch.object(EVAL.os, "killpg", side_effect=PermissionError("simulated denial")):
            result = self.execute("print('answer')")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("Process-group cleanup failed", result["error"])

    def test_double_signal_denial_uses_liveness_eof_without_hanging(self):
        real_popen = EVAL.subprocess.Popen
        processes = []

        def spawn(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        try:
            with patch.object(EVAL.subprocess, "Popen", side_effect=spawn), \
                    patch.object(EVAL.os, "killpg", side_effect=PermissionError("group denied")), \
                    patch.object(real_popen, "kill", side_effect=PermissionError("pid denied")):
                result = self.execute("print('answer')")
            self.assertEqual(result["status"], "error")
            self.assertIn("Process-group cleanup failed", result["error"])
            self.assertNotIn("Supervisor cleanup exceeded", result["error"])
            self.assertLess(result["elapsed_seconds"], 2)
            self.assertEqual(len(processes), 1)
            self.assertIsNotNone(processes[0].returncode, "EOF must actually terminate the supervisor")
        finally:
            # A broken liveness implementation must fail without leaving the
            # very orphan this regression test is intended to detect.
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=2)

    def test_completion_is_event_driven_without_runner_polling(self):
        real_popen = EVAL.subprocess.Popen

        def spawn(command, *args, **kwargs):
            command = command[:]
            # A runner completion must wake the supervisor directly. Reject
            # poll() rather than relying on a flaky wall-clock speed threshold.
            code = command[3]
            marker = "control = int(sys.argv[1])"
            self.assertIn(marker, code)
            command[3] = code.replace(marker,
                "def forbidden_poll(*args, **kwargs):\n"
                "    raise RuntimeError('periodic runner polling is forbidden')\n"
                "subprocess.Popen.poll = forbidden_poll\n" + marker, 1)
            return real_popen(command, *args, **kwargs)

        with patch.object(EVAL.subprocess, "Popen", side_effect=spawn):
            result = self.execute("import time; time.sleep(.02); print('answer')")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["answer"].strip(), "answer")

    def test_supervisor_exceptions_preserve_traceback_before_and_after_stdio_close(self):
        real_popen = EVAL.subprocess.Popen
        for phase in ("before", "after"):
            def spawn(command, *args, **kwargs):
                command = command[:]
                lines = command[3].splitlines()
                marker = "try:" if phase == "before" else "outcomes = []"
                index = next(index for index, line in enumerate(lines) if line.strip() == marker)
                indent = len(lines[index]) - len(lines[index].lstrip())
                if phase == "before":
                    index += 1
                    indent += 4
                lines.insert(index, " " * indent + "raise RuntimeError('supervisor-diagnostic-marker')")
                command[3] = "\n".join(lines)
                return real_popen(command, *args, **kwargs)

            with self.subTest(phase=phase), patch.object(EVAL.subprocess, "Popen", side_effect=spawn):
                result = self.execute("print('answer')")
                self.assertEqual(result["status"], "error")
                self.assertIsNone(result["exit_code"])
                self.assertIn("Traceback (most recent call last)", result["error"])
                self.assertIn("RuntimeError: supervisor-diagnostic-marker", result["error"])

    def test_waiter_exception_notifies_supervisor_instead_of_waiting_until_timeout(self):
        real_popen = EVAL.subprocess.Popen

        def spawn(command, *args, **kwargs):
            command = command[:]
            marker = "control = int(sys.argv[1])"
            self.assertIn(marker, command[3])
            command[3] = command[3].replace(marker,
                "def failed_wait(*args, **kwargs):\n"
                "    raise RuntimeError('waiter-diagnostic-marker')\n"
                "subprocess.Popen.wait = failed_wait\n" + marker, 1)
            return real_popen(command, *args, **kwargs)

        with patch.object(EVAL.subprocess, "Popen", side_effect=spawn):
            result = self.execute("import time; time.sleep(.05); print('answer')")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["exit_code"])
        self.assertIn("Supervisor waiter failure", result["error"])
        self.assertIn("RuntimeError: waiter-diagnostic-marker", result["error"])
        self.assertLess(result["elapsed_seconds"], 2)

    @unittest.skipUnless(os.name == "posix", "resource limits require POSIX")
    def test_supervisor_supports_private_descriptors_above_select_fd_setsize(self):
        script = (
            "import importlib.util,json,os,resource,sys\n"
            f"spec=importlib.util.spec_from_file_location('ev',{str(ROOT / 'scripts/skill_eval.py')!r})\n"
            "ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)\n"
            "soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)\n"
            "if hard!=resource.RLIM_INFINITY and hard<2048:\n"
            "    print(json.dumps({'unsupported_limit':hard}));sys.exit(0)\n"
            "resource.setrlimit(resource.RLIMIT_NOFILE,(max(soft,2048),hard))\n"
            "fds=[]\n"
            "try:\n"
            "    fds=[os.open(os.devnull,os.O_RDONLY) for _ in range(1200)]\n"
            "    result=ev.execute([sys.executable,'-c',\"print('answer')\"],'',2,sys.executable)\n"
            "    print(json.dumps({'max_fd':max(fds),**result}))\n"
            "finally:\n"
            "    for fd in fds:os.close(fd)\n")
        process = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=5)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        if "unsupported_limit" in result:
            self.skipTest("host hard descriptor limit is below 2048")
        self.assertGreater(result["max_fd"], 1024)
        self.assertEqual(result["status"], "ok", result["error"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["answer"].strip(), "answer")

    def test_cleanup_diagnostics_do_not_add_blank_lines_when_group_signal_succeeded(self):
        real_popen = EVAL.subprocess.Popen
        real_wait = real_popen.wait
        for stderr in ("", "runner-detail"):
            processes = []

            def spawn(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                processes.append(process)
                return process

            try:
                with self.subTest(stderr=stderr), \
                        patch.object(EVAL.subprocess, "Popen", side_effect=spawn), \
                        patch.object(real_popen, "wait", side_effect=subprocess.TimeoutExpired("test", .5)), \
                        patch.object(real_popen, "kill", side_effect=PermissionError("pid denied")):
                    result = self.execute(f"import sys; sys.stderr.write({stderr!r}); print('answer')")
                self.assertEqual(result["status"], "error")
                self.assertIn("Supervisor termination failed", result["error"])
                self.assertFalse(result["error"].startswith("\n"))
                self.assertNotIn("\n\n", result["error"])
            finally:
                for process in processes:
                    real_wait(process, timeout=2)

    def test_cleanup_waits_are_bounded_even_if_signal_and_wait_both_fail(self):
        real_popen = EVAL.subprocess.Popen
        real_wait = real_popen.wait
        processes = []

        def spawn(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        try:
            with patch.object(EVAL.subprocess, "Popen", side_effect=spawn), \
                    patch.object(real_popen, "wait", side_effect=subprocess.TimeoutExpired("test", .5)) as wait, \
                    patch.object(real_popen, "kill", side_effect=PermissionError("pid denied")), \
                    patch.object(EVAL.os, "killpg", side_effect=PermissionError("group denied")):
                result = self.execute("print('answer')")
            self.assertEqual(result["status"], "error")
            self.assertIn("Supervisor termination failed", result["error"])
            self.assertIn("Supervisor cleanup exceeded 1.0s", result["error"])
            self.assertLess(result["elapsed_seconds"], 2)
            self.assertEqual(len(wait.call_args_list), 2)
            for call in wait.call_args_list:
                self.assertGreater(call.kwargs["timeout"], 0)
                self.assertLessEqual(call.kwargs["timeout"], 1)
        finally:
            # Liveness EOF reaches the real supervisor despite the mocked wait.
            for process in processes:
                real_wait(process, timeout=2)

    def test_timeout_keeps_missing_status_and_cleanup_failure_diagnostics(self):
        with patch.object(EVAL.os, "killpg", side_effect=PermissionError("group denied")):
            result = self.execute("import time; time.sleep(10)", timeout=.2)
        self.assertEqual(result["status"], "timeout")
        self.assertIsNone(result["exit_code"])
        self.assertIn("No valid runner exit status was received", result["error"])
        self.assertIn("Process-group cleanup failed", result["error"])
        self.assertLess(result["elapsed_seconds"], 2)

    def test_closed_standard_descriptors_do_not_alias_private_pipes(self):
        for descriptors in ((0, 1), (0, 1, 2)):
            with self.subTest(descriptors=descriptors), tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / "result.json"
                script = (
                    "import importlib.util,json,os,pathlib,sys\n"
                    f"spec=importlib.util.spec_from_file_location('ev',{str(ROOT / 'scripts/skill_eval.py')!r})\n"
                    "ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)\n"
                    f"for fd in {descriptors!r}: os.close(fd)\n"
                    "result=ev.execute([sys.executable,'-c',\"print('answer')\"],'',2,sys.executable)\n"
                    f"pathlib.Path({str(output)!r}).write_text(json.dumps(result))\n")
                process = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=4)
                self.assertEqual(process.returncode, 0, process.stderr)
                result = json.loads(output.read_text())
                self.assertEqual(result["status"], "ok")
                self.assertEqual(result["exit_code"], 0)
                self.assertEqual(result["answer"].strip(), "answer")

    @unittest.skipUnless(os.name == "posix", "parent liveness uses POSIX pipes/signals")
    def test_harness_death_stops_supervisor_and_group_before_and_after_runner_exit(self):
        for phase in ("running", "exited"):
            for death_signal in (signal.SIGTERM, signal.SIGKILL):
                with self.subTest(phase=phase, signal=death_signal), tempfile.TemporaryDirectory() as folder:
                    ready = Path(folder) / "ready"
                    marker = Path(folder) / "late-write"
                    pid_file = Path(folder) / "supervisor-pid"
                    proof_read, proof_write = os.pipe()
                    late_write = (f"import pathlib,time; time.sleep(.6); pathlib.Path({str(marker)!r}).touch(); "
                                  "time.sleep(10)")
                    if phase == "running":
                        runner = f"import pathlib; pathlib.Path({str(ready)!r}).touch(); " + late_write
                    else:
                        runner = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
                                  + repr(late_write) + "]); print('answer')")
                    harness = (
                        "import importlib.util,os,pathlib,sys\n"
                        f"spec=importlib.util.spec_from_file_location('ev',{str(ROOT / 'scripts/skill_eval.py')!r})\n"
                        "ev=importlib.util.module_from_spec(spec);spec.loader.exec_module(ev)\n"
                        "real_popen=ev.subprocess.Popen\n"
                        "def spawn(*args,**kwargs):\n"
                        f"    kwargs['pass_fds']=(*kwargs.get('pass_fds',()),{proof_write})\n"
                        "    process=real_popen(*args,**kwargs)\n"
                        f"    pathlib.Path({str(pid_file)!r}).write_text(str(process.pid))\n"
                        "    return process\n"
                        "ev.subprocess.Popen=spawn\n"
                        "real_read=ev.os.read\n"
                        "def read(fd,size):\n"
                        "    data=real_read(fd,size)\n"
                        f"    if {phase!r}=='exited' and b'\"exit_code\": 0' in data: "
                        f"pathlib.Path({str(ready)!r}).touch()\n"
                        "    return data\n"
                        "ev.os.read=read\n"
                        f"ev.execute([sys.executable,'-c',{runner!r}],'',10,sys.executable)\n")
                    process = subprocess.Popen([sys.executable, "-c", harness], pass_fds=(proof_write,),
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    os.close(proof_write)
                    supervisor_exited = False
                    try:
                        deadline = time.monotonic() + 3
                        while not ready.exists() and time.monotonic() < deadline:
                            self.assertIsNone(process.poll(), "test harness exited before ready")
                            time.sleep(.01)
                        self.assertTrue(ready.exists(), "requested runner phase must be reached")
                        os.kill(process.pid, death_signal)
                        process.wait(timeout=2)
                        # Only harness and supervisor own this proof write end.
                        # EOF proves supervisor exit without mistaking zombies
                        # for live processes or using a potentially reused PID.
                        self.assertTrue(select.select([proof_read], [], [], 2)[0])
                        supervisor_exited = os.read(proof_read, 1) == b""
                        self.assertTrue(supervisor_exited)
                        time.sleep(.7)
                        self.assertFalse(marker.exists(), "runner/descendant must not survive parent death")
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=2)
                        if not supervisor_exited and pid_file.exists():
                            # The still-open proof pipe identifies our live
                            # supervisor; only clean the group created above.
                            try:
                                os.killpg(int(pid_file.read_text()), signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                        os.close(proof_read)

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
