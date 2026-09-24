from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_eval_capture", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class SkillCaptureRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / "suite.json"
        self.suite_value = {
            "version": EVAL.SUITE_VERSION,
            "id": "capture-fixture",
            "cases": [{
                "id": "one", "split": "calibration", "task": "Review the change.",
                "inputs": {"base.py": "return a", "head.py": "return b"},
                "checks": [{"id": "detect", "criterion": "Explain the changed return value."}],
            }],
        }
        self.suite.write_text(json.dumps(self.suite_value), encoding="utf-8")
        self.runner = self.root / "runner.py"
        self.runner.write_text("print('Synthetic fixture only.')\n", encoding="utf-8")

    def args(self, name="run", **changes):
        values = dict(
            suite=self.suite, skill="none", label=name, model="scripted",
            environment="capture-regression-fixture", split="calibration",
            repeat=2, timeout=1.0, synthetic=True, out=self.root / f"{name}.json",
            runner=[sys.executable, str(self.runner)],
        )
        values.update(changes)
        return argparse.Namespace(**values)

    def answer(self, text="Synthetic captured answer."):
        return dict(status="ok", elapsed_seconds=0.01, answer=text, error="", exit_code=0,
                    stdout_truncated=False, stderr_truncated=False)

    def journal_path(self, args):
        return Path(str(args.out) + ".journal.jsonl")

    def events(self, args):
        return [json.loads(line) for line in self.journal_path(args).read_text(
            encoding="utf-8").splitlines()]

    def run_capture(self, args, result=None):
        with mock.patch.object(EVAL, "execute", return_value=result or self.answer()), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            EVAL.run(args)
        return EVAL.read_run(args.out)

    def test_prompt_is_canonical_when_input_and_skill_key_order_changes(self):
        first = self.suite_value["cases"][0]
        second = dict(first, inputs=dict(reversed(list(first["inputs"].items()))))
        skill = {"name": "fixture", "files": {"SKILL.md": "Read both files.", "references/a.md": "Use evidence."}}
        reordered = dict(skill, files=dict(reversed(list(skill["files"].items()))))
        self.assertEqual(EVAL.digest(first), EVAL.digest(second))
        self.assertEqual(EVAL.prompt_for(first, skill), EVAL.prompt_for(second, reordered))

    def test_runner_identity_does_not_rewrite_bare_subcommands_or_mutate_input(self):
        (self.root / "exec").write_text("A coincidental file, not a command argument.", encoding="utf-8")
        command = [sys.executable, "exec", "./runner.py"]
        original = command[:]
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            identity = EVAL.runner_identity(command)
        finally:
            os.chdir(previous)
        self.assertEqual(command, original)
        self.assertEqual(identity["command"][1], "exec")
        self.assertTrue(Path(identity["command"][2]).is_absolute())
        self.assertEqual(Path(identity["command"][2]).resolve(), self.runner.resolve())
        self.assertNotIn("1", identity["files"])
        self.assertIn("2", identity["files"])

    def test_json_skill_reference_changes_snapshot_hash_and_supplied_prompt(self):
        skill = self.root / "skill"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text("Use references/checklist.json.", encoding="utf-8")
        reference = skill / "references/checklist.json"
        reference.write_text('{"check":"authorization"}', encoding="utf-8")
        before = EVAL.skill_at(str(skill))
        reference.write_text('{"check":"data-loss"}', encoding="utf-8")
        after = EVAL.skill_at(str(skill))
        self.assertEqual(before["files"]["references/checklist.json"], '{"check":"authorization"}')
        self.assertEqual(after["files"]["references/checklist.json"], '{"check":"data-loss"}')
        self.assertNotEqual(before, after)
        self.assertNotEqual(EVAL.digest(before), EVAL.digest(after))
        case = self.suite_value["cases"][0]
        self.assertNotEqual(EVAL.prompt_for(case, before), EVAL.prompt_for(case, after))

    def test_builtin_review_skill_captures_agent_metadata_and_markdown_references(self):
        skill = ROOT / "core/skills/critical-review"
        record = self.run_capture(self.args(skill=str(skill)))
        for relative in ("SKILL.md", "agents/openai.yaml", "references/severity.md"):
            with self.subTest(file=relative):
                self.assertEqual(record["skill"]["files"][relative], (skill / relative).read_text(encoding="utf-8"))

    def test_skill_scripts_are_supplied_as_text_without_execution(self):
        skill = self.root / "skill-script"
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text("Read scripts/helper.py as source.", encoding="utf-8")
        marker = self.root / "must-not-be-created"
        code = f"from pathlib import Path\nPath({str(marker)!r}).write_text('unexpected execution')\n"
        (skill / "scripts/helper.py").write_text(code, encoding="utf-8")
        snapshot = EVAL.skill_at(str(skill))
        self.assertEqual(snapshot["files"]["scripts/helper.py"], code)
        self.assertFalse(marker.exists())

    def test_binary_or_nonregular_skill_file_is_rejected_before_runner_calls(self):
        for name, content in (("nul", b"text\x00suffix"), ("invalid-utf8", b"\xff\xfe"), ("fifo", None)):
            with self.subTest(kind=name):
                skill = self.root / f"skill-{name}"
                skill.mkdir()
                (skill / "SKILL.md").write_text("Read local references.", encoding="utf-8")
                reference = skill / "reference.bin"
                if content is None:
                    os.mkfifo(reference)
                else:
                    reference.write_bytes(content)
                with mock.patch.object(EVAL, "execute") as execute, self.assertRaises(ValueError):
                    EVAL.run(self.args(name=name, skill=str(skill)))
                execute.assert_not_called()

    def test_individual_or_total_skill_size_limit_fails_before_runner_calls(self):
        for name, sizes in (("file-limit", [1_000_001]), ("total-limit", [1_000_000] * 4)):
            with self.subTest(limit=name):
                skill = self.root / f"skill-{name}"
                skill.mkdir()
                (skill / "SKILL.md").write_text("Read local references.", encoding="utf-8")
                for index, size in enumerate(sizes):
                    (skill / f"reference-{index}.txt").write_bytes(b"x" * size)
                with mock.patch.object(EVAL, "execute") as execute, self.assertRaises(ValueError):
                    EVAL.run(self.args(name=name, skill=str(skill)))
                execute.assert_not_called()

    def test_skill_rejects_file_and_directory_symlinks(self):
        target = self.root / "external"
        target.mkdir()
        (target / "rules.md").write_text("External instructions.", encoding="utf-8")
        for name, source in (("file", target / "rules.md"), ("directory", target)):
            with self.subTest(kind=name):
                skill = self.root / f"skill-{name}"
                skill.mkdir()
                (skill / "SKILL.md").write_text("Use the linked reference.", encoding="utf-8")
                (skill / "linked").symlink_to(source, target_is_directory=source.is_dir())
                with self.assertRaises(ValueError):
                    EVAL.skill_at(str(skill))

    def test_nonfinite_json_is_rejected_before_any_runner_call(self):
        for index, literal in enumerate(("NaN", "Infinity", "-Infinity", "1e999")):
            with self.subTest(value=literal):
                source = json.dumps(self.suite_value)[:-1] + ', "ignored": ' + literal + '}'
                self.suite.write_text(source, encoding="utf-8")
                with mock.patch.object(EVAL, "execute") as execute, self.assertRaises(ValueError):
                    EVAL.run(self.args(name=f"nonfinite-{index}"))
                execute.assert_not_called()

    def test_existing_output_or_journal_is_preserved_without_runner_calls(self):
        for name in ("output", "journal"):
            with self.subTest(conflict=name):
                args = self.args(name=name)
                target = args.out if name == "output" else self.journal_path(args)
                target.write_text("Earlier experiment: keep this exact content.", encoding="utf-8")
                with mock.patch.object(EVAL, "execute") as execute, self.assertRaises((ValueError, OSError)):
                    EVAL.run(args)
                execute.assert_not_called()
                self.assertEqual(target.read_text(encoding="utf-8"), "Earlier experiment: keep this exact content.")

    def test_unusable_output_parent_fails_before_any_runner_call(self):
        parent = self.root / "not-a-directory"
        parent.write_text("Existing file.", encoding="utf-8")
        with mock.patch.object(EVAL, "execute") as execute, self.assertRaises((ValueError, OSError)):
            EVAL.run(self.args(out=parent / "run.json"))
        execute.assert_not_called()

    def test_each_finished_attempt_is_durable_before_the_next_runner_call(self):
        args = self.args()
        calls = []
        real_fsync = os.fsync

        def execute(*_):
            events = self.events(args)
            finished = [event for event in events if event["event"] == "attempt_finished"]
            self.assertEqual(len(finished), len(calls))
            self.assertGreaterEqual(fsync.call_count, len(events))
            calls.append(True)
            return self.answer(f"Captured attempt {len(calls)}.")

        with mock.patch.object(EVAL.os, "fsync", wraps=real_fsync) as fsync, \
                mock.patch.object(EVAL, "execute", side_effect=execute), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            EVAL.run(args)
        events = self.events(args)
        self.assertEqual(events[0]["event"], "header")
        self.assertIn("record", events[0])
        self.assertEqual(events[-1]["event"], "complete")
        record = EVAL.read_run(args.out)
        self.assertEqual(record["state"], "complete")
        self.assertNotIn("runner", record)
        self.assertIn("command", record["runner_identity"])
        finished = [event["result"] for event in events if event["event"] == "attempt_finished"]
        self.assertEqual(finished, record["results"])

    def test_interruption_retains_completed_attempt_and_rejects_partial_run(self):
        args = self.args()
        with mock.patch.object(EVAL, "execute", side_effect=[self.answer("Keep the first answer."), KeyboardInterrupt()]), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(KeyboardInterrupt):
            EVAL.run(args)
        events = self.events(args)
        finished = [event["result"] for event in events if event["event"] == "attempt_finished"]
        self.assertEqual([row["answer"] for row in finished], ["Keep the first answer."])
        self.assertEqual(events[-1]["event"], "failed")
        self.assertNotIn("complete", [event["event"] for event in events])
        with self.assertRaises(ValueError):
            EVAL.read_run(args.out)

    def test_runner_drift_retains_all_answers_without_a_comparable_run(self):
        args = self.args()
        calls = []

        def execute(*_):
            calls.append(True)
            self.runner.write_text(f"print('Changed after attempt {len(calls)}.')\n", encoding="utf-8")
            return self.answer(f"Paid response {len(calls)}.")

        with mock.patch.object(EVAL, "execute", side_effect=execute), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(ValueError):
            EVAL.run(args)
        events = self.events(args)
        finished = [event["result"] for event in events if event["event"] == "attempt_finished"]
        self.assertEqual(len(finished), 1)
        self.assertEqual(len(finished), len(calls))
        self.assertEqual(events[-1]["event"], "failed")
        with self.assertRaises(ValueError):
            EVAL.read_run(args.out)

    def test_final_serialization_failure_keeps_every_finished_attempt(self):
        args = self.args()
        with mock.patch.object(EVAL, "execute", return_value=self.answer("Keep this completed response.")), \
                mock.patch.object(EVAL.json, "dump", side_effect=OSError("Simulated final output failure")), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(OSError):
            EVAL.run(args)
        events = self.events(args)
        finished = [event["result"] for event in events if event["event"] == "attempt_finished"]
        self.assertEqual(len(finished), args.repeat)
        self.assertTrue(all(row["answer"] == "Keep this completed response." for row in finished))
        self.assertEqual(events[-1]["event"], "failed")
        with self.assertRaises((ValueError, OSError)):
            EVAL.read_run(args.out)

    def test_failed_final_fsync_cannot_leave_a_comparable_complete_record(self):
        args = self.args()
        real_fsync = os.fsync

        def fail_final_fsync(fd):
            current = os.fstat(fd)
            target = args.out.stat()
            if (current.st_dev, current.st_ino) == (target.st_dev, target.st_ino):
                raise OSError("Simulated final output fsync failure")
            return real_fsync(fd)

        with mock.patch.object(EVAL, "execute", return_value=self.answer()), \
                mock.patch.object(EVAL.os, "fsync", side_effect=fail_final_fsync), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(OSError):
            EVAL.run(args)
        events = self.events(args)
        self.assertEqual(sum(event["event"] == "attempt_finished" for event in events), args.repeat)
        self.assertEqual(events[-1]["event"], "failed")
        with self.assertRaises((ValueError, OSError)):
            EVAL.read_run(args.out)

    def test_harness_hash_is_captured_before_runner_execution(self):
        args = self.args()
        executed = []
        original_read = Path.read_bytes

        def read_bytes(path):
            if path.resolve() == Path(EVAL.__file__).resolve():
                return b"after execution" if executed else b"before execution"
            return original_read(path)

        def execute(*_):
            executed.append(True)
            return self.answer()

        with mock.patch.object(Path, "read_bytes", autospec=True, side_effect=read_bytes), \
                mock.patch.object(EVAL, "execute", side_effect=execute), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            EVAL.run(args)
        record = EVAL.read_run(args.out)
        self.assertEqual(record["harness_sha256"], hashlib.sha256(b"before execution").hexdigest())

    def test_incomplete_state_is_rejected_even_with_all_rows_and_valid_hash(self):
        args = self.args()
        complete = self.run_capture(args)
        incomplete = dict(complete, state="incomplete")
        incomplete.pop("sha256")
        incomplete["sha256"] = EVAL.digest(incomplete)
        path = self.root / "incomplete.json"
        path.write_text(json.dumps(incomplete), encoding="utf-8")
        with self.assertRaises(ValueError):
            EVAL.read_run(path)
        with self.assertRaises(ValueError):
            EVAL.compare(complete, incomplete, EVAL.judgments(complete, None), EVAL.judgments(incomplete, None))

    def test_input_fingerprint_is_independent_of_skill_and_checked_in_comparison(self):
        before = self.run_capture(self.args(name="before"))
        skill = self.root / "candidate"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Explain the evidence.", encoding="utf-8")
        after = self.run_capture(self.args(name="after", skill=str(skill)))
        self.assertEqual(before["results"][0]["input_sha256"], after["results"][0]["input_sha256"])
        self.assertNotEqual(before["results"][0]["prompt_sha256"], after["results"][0]["prompt_sha256"])
        EVAL.compare(before, after, EVAL.judgments(before, None), EVAL.judgments(after, None))
        after["results"][0]["input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            EVAL.compare(before, after, EVAL.judgments(before, None), EVAL.judgments(after, None))


if __name__ == "__main__":
    unittest.main()
