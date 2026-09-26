from __future__ import annotations

import argparse
import contextlib
import io
import json
import shlex
import sys
import unittest
from unittest import mock

import test_skill_eval as fixture


EVAL = fixture.EVAL


class RuntimeIdentityTests(fixture.SkillEvaluationFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.python = sys.executable
        self.supervisor = self.root / "supervisor-python"
        self.supervisor.write_text("Synthetic interpreter bytes; never executed.")
        self.supervisor.chmod(0o700)

    def args(self, name="run"):
        return argparse.Namespace(
            suite=self.suite, skill="none", label=name, model="scripted",
            environment="runtime-fixture", split="all", repeat=1, timeout=1.0,
            synthetic=True, out=self.root / f"{name}.json", runner=[self.python, str(self.runner)])

    @staticmethod
    def answer():
        return dict(status="ok", answer="Synthetic answer.", error="", elapsed_seconds=0.01,
                    exit_code=0, stdout_truncated=False, stderr_truncated=False)

    def capture_runtime(self, args, effect=None):
        with mock.patch.object(EVAL.sys, "executable", str(self.supervisor)), \
                mock.patch.object(EVAL, "execute", side_effect=effect, return_value=self.answer()) as execute, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            EVAL.run(args)
        return EVAL.read_run(args.out), execute.call_args_list

    def test_captured_interpreter_is_the_path_supplied_to_every_attempt(self):
        record, calls = self.capture_runtime(self.args())
        self.assertEqual(record["supervisor_identity"], EVAL.runner_identity([str(self.supervisor)]))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(call.args[3] == record["supervisor_identity"]["command"][0] for call in calls))

    def test_execute_uses_supplied_interpreter_instead_of_current_sys_executable(self):
        marker = self.root / "interpreter-used"
        self.supervisor.write_text(
            "#!/bin/sh\n"
            f"printf used > {shlex.quote(str(marker))}\n"
            f"exec {shlex.quote(self.python)} \"$@\"\n")
        identity = EVAL.runner_identity([str(self.supervisor)])
        with mock.patch.object(EVAL.sys, "executable", "/not-the-recorded-interpreter"):
            result = EVAL.execute([self.python, "-c", "print('answer')"], "", 3,
                                  identity["command"][0])
        self.assertEqual(result["status"], "ok", result["error"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["answer"].strip(), "answer")
        self.assertEqual(marker.read_text(), "used")

    def test_both_identities_reject_malformed_shape_after_valid_record_hash(self):
        original, _ = self.capture_runtime(self.args())
        malformed = [None, "command", [], {}, {"command": [], "files": {}},
                     {"command": ["python", None], "files": {}},
                     {"command": ["python"], "files": []},
                     {"command": ["python"], "files": {"0": "z" * 64}},
                     {"command": ["python"], "files": {"0": "a" * 63}},
                     {"command": ["python"], "files": {"1": "a" * 64}}]
        for field, message in (("runner_identity", "missing or invalid runner identity"),
                               ("supervisor_identity", "missing or invalid supervisor interpreter identity")):
            for value in malformed:
                with self.subTest(field=field, value=value):
                    record = {**original, field: value}
                    record.pop("sha256")
                    record["sha256"] = EVAL.digest(record)
                    path = self.root / "malformed-identity.json"
                    path.write_text(json.dumps(record))
                    with self.assertRaisesRegex(ValueError, message):
                        EVAL.read_run(path)

        # Unresolved runner executables can legitimately produce captured errors,
        # and explicit empty string arguments are valid argv values.
        record = {**original, "runner_identity": {"command": ["missing-runner", ""], "files": {}}}
        record.pop("sha256")
        record["sha256"] = EVAL.digest(record)
        path = self.root / "unresolved-runner.json"
        path.write_text(json.dumps(record))
        self.assertEqual(EVAL.read_run(path)["runner_identity"], record["runner_identity"])

    def test_interpreter_content_change_between_runs_blocks_comparison(self):
        before, _ = self.capture_runtime(self.args("before"))
        self.supervisor.write_text("A different interpreter at the same path.")
        after, _ = self.capture_runtime(self.args("after"))
        self.assertEqual(before["runner_identity"], after["runner_identity"])
        self.assertNotEqual(before["supervisor_identity"], after["supervisor_identity"])
        with self.assertRaisesRegex(ValueError, "supervisor_identity"):
            EVAL.compare(before, after, EVAL.judgments(before, None), EVAL.judgments(after, None),
                         variability=True)

    def test_interpreter_change_during_run_keeps_answers_but_rejects_final_record(self):
        for change_on in (1, 2):
            with self.subTest(change_on=change_on):
                args = self.args(f"drift-{change_on}")
                calls = []

                def change_interpreter(*_):
                    calls.append(True)
                    if len(calls) == change_on:
                        self.supervisor.write_bytes(self.supervisor.read_bytes() + b"changed")
                    return self.answer()

                with self.assertRaisesRegex(ValueError, "supervisor interpreter changed.*journal"):
                    self.capture_runtime(args, change_interpreter)
                self.assertEqual(len(calls), change_on)
                journal = args.out.with_name(args.out.name + ".journal.jsonl")
                events = [json.loads(line) for line in journal.read_text().splitlines()]
                self.assertEqual(sum(event["event"] == "attempt_finished" for event in events), change_on)
                self.assertEqual(args.out.read_bytes(), b"")

    def test_read_requires_current_format_and_recorded_interpreter_identity(self):
        record, _ = self.capture_runtime(self.args())
        original = json.loads(json.dumps(record))
        for version in (1, 2, 999):
            with self.subTest(version=version):
                record = {**original, "version": version}
                record.pop("sha256")
                record["sha256"] = EVAL.digest(record)
                path = self.root / f"version-{version}.json"
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError, f"unsupported run version {version};"):
                    EVAL.read_run(path)
        record = dict(original)
        record.pop("supervisor_identity")
        record.pop("sha256")
        record["sha256"] = EVAL.digest(record)
        path = self.root / "missing-runtime.json"
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "missing or invalid supervisor interpreter identity"):
            EVAL.read_run(path)


if __name__ == "__main__":
    unittest.main()
