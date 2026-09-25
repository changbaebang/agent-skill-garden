from __future__ import annotations

import argparse
import contextlib
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
SPEC = importlib.util.spec_from_file_location("skill_eval_efficiency", ROOT / "scripts/skill_eval.py")
assert SPEC and SPEC.loader
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


class SkillEvaluationEfficiencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / "suite.json"
        self.suite.write_text(json.dumps({
            "version": 1, "id": "efficiency-fixture", "cases": [
                {"id": name, "split": split, "task": "Review the supplied source.",
                 "inputs": {"source.txt": f"Source for {name}."},
                 "checks": [{"id": "evidence", "criterion": "Explain the supplied evidence."}]}
                for name, split in (("first", "calibration"), ("second", "holdout"))
            ]}), encoding="utf-8")
        self.runner = self.root / "runner.py"
        self.runner.write_text("print('Scripted fixture answer.')\n", encoding="utf-8")
        self.skill = self.root / "skill"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("Use concrete evidence.\n" * 1024, encoding="utf-8")

    def args(self, **changes):
        values = dict(suite=self.suite, skill=str(self.skill), label="fixture", model="scripted",
                      environment="efficiency-fixture", split="all", repeat=20, timeout=1.0,
                      synthetic=True, out=self.root / "run.json",
                      runner=[sys.executable, str(self.runner)])
        values.update(changes)
        return argparse.Namespace(**values)

    @staticmethod
    def answer():
        return dict(status="ok", elapsed_seconds=0.01, answer="Scripted fixture answer.",
                    error="", exit_code=0, stdout_truncated=False, stderr_truncated=False)

    def events(self, args):
        path = Path(str(args.out) + ".journal.jsonl")
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    @contextlib.contextmanager
    def quiet(self):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield

    def capture(self, args):
        with mock.patch.object(EVAL, "execute", return_value=self.answer()), self.quiet():
            EVAL.run(args)
        return EVAL.read_run(args.out)

    def test_journal_collision_cleans_unused_output_without_any_runner_call(self):
        args = self.args()
        journal = Path(str(args.out) + ".journal.jsonl")
        original = b"An earlier capture must remain byte-for-byte intact.\n"
        journal.write_bytes(original)
        with mock.patch.object(EVAL, "execute") as execute, self.assertRaises(FileExistsError):
            EVAL.run(args)
        execute.assert_not_called()
        self.assertFalse(args.out.exists())
        self.assertEqual(journal.read_bytes(), original)

    def test_failed_setup_preserves_replacement_visible_before_ownership_check(self):
        output = self.root / "race.json"
        journal = self.root / "race.json.journal.jsonl"
        replacement = self.root / "replacement.json"
        replacement.write_text("Another process owns this file.", encoding="utf-8")
        real_open = Path.open
        inodes = []

        def replace_output_before_journal_open(path, *args, **kwargs):
            if path == journal:
                inodes.append(output.stat().st_ino)
                os.replace(replacement, output)
                inodes.append(output.stat().st_ino)
                raise FileExistsError("Simulated conflicting journal reservation")
            return real_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", replace_output_before_journal_open), \
                self.assertRaises(FileExistsError):
            with EVAL.capture_outputs(output, journal):
                self.fail("The journal reservation should have failed")
        self.assertNotEqual(*inodes)
        self.assertEqual(output.read_text(encoding="utf-8"), "Another process owns this file.")

    def test_repeated_capture_hashes_runner_contents_only_at_start_and_finish(self):
        args = self.args()
        with mock.patch.object(EVAL, "runner_identity", wraps=EVAL.runner_identity) as identity, \
                mock.patch.object(EVAL, "execute", return_value=self.answer()) as execute, self.quiet():
            EVAL.run(args)
        self.assertEqual(execute.call_count, 40)
        self.assertEqual(identity.call_count, 4)
        commands = [call.args[0] for call in identity.call_args_list]
        self.assertEqual(commands.count([sys.executable, str(self.runner)]), 2)
        self.assertEqual(commands.count([sys.executable]), 2)
        self.assertEqual(len(EVAL.read_run(args.out)["results"]), 40)

    def test_same_size_edit_with_restored_mtime_stops_before_the_next_runner_call(self):
        args = self.args()
        original = self.runner.read_bytes()
        before = self.runner.stat()

        def change_runner(*_):
            self.runner.write_bytes(original.replace(b"Scripted", b"Modified"))
            os.utime(self.runner, ns=(before.st_atime_ns, before.st_mtime_ns))
            after = self.runner.stat()
            self.assertEqual(after.st_size, before.st_size)
            self.assertEqual(after.st_ino, before.st_ino)
            self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
            self.assertNotEqual(after.st_ctime_ns, before.st_ctime_ns)
            return self.answer()

        with mock.patch.object(EVAL, "execute", side_effect=change_runner) as execute, self.quiet(), \
                self.assertRaisesRegex(ValueError, "runner files changed"):
            EVAL.run(args)
        self.assertEqual(execute.call_count, 1)
        events = self.events(args)
        self.assertEqual(sum(event["event"] == "attempt_finished" for event in events), 1)
        self.assertEqual(events[-1]["event"], "failed")
        with self.assertRaises(ValueError):
            EVAL.read_run(args.out)

    def test_deleted_runner_reports_drift_and_preserves_completed_answers(self):
        for delete_on in (1, 4):
            with self.subTest(delete_on=delete_on):
                self.runner.write_text("print('Scripted fixture answer.')\n", encoding="utf-8")
                args = self.args(repeat=2, out=self.root / f"deleted-{delete_on}.json")
                calls = []

                def delete_runner(*_):
                    calls.append(True)
                    if len(calls) == delete_on:
                        self.runner.unlink()
                    return self.answer()

                with mock.patch.object(EVAL, "execute", side_effect=delete_runner), self.quiet(), \
                        self.assertRaisesRegex(ValueError, "runner files changed.*run journal"):
                    EVAL.run(args)
                self.assertEqual(len(calls), delete_on)
                finished = [event for event in self.events(args) if event["event"] == "attempt_finished"]
                self.assertEqual(len(finished), delete_on)
                self.assertEqual(args.out.read_bytes(), b"")

    def test_final_content_hash_drift_preserves_answers_and_blocks_comparison(self):
        args = self.args(repeat=2)
        calls = []

        def change_after_last_attempt(*_):
            calls.append(True)
            if len(calls) == 4:
                previous = self.runner.stat()
                self.runner.write_bytes(self.runner.read_bytes().replace(b"Scripted", b"Modified"))
                os.utime(self.runner, ns=(previous.st_atime_ns, previous.st_mtime_ns))
                self.assertEqual(self.runner.stat().st_size, previous.st_size)
            return self.answer()

        with mock.patch.object(EVAL, "execute", side_effect=change_after_last_attempt), self.quiet(), \
                self.assertRaisesRegex(ValueError, "runner files changed"):
            EVAL.run(args)
        finished = [event["result"] for event in self.events(args) if event["event"] == "attempt_finished"]
        self.assertEqual(len(finished), 4)
        self.assertTrue(all(row["answer"] == "Scripted fixture answer." for row in finished))
        self.assertEqual(self.events(args)[-1]["event"], "failed")
        report = self.root / "report.md"
        with self.quiet():
            result = EVAL.main(["compare", str(args.out), str(args.out), "--out", str(report)])
        self.assertEqual(result, 2)
        self.assertFalse(report.exists())

    def test_read_run_builds_full_and_skill_free_prompt_once_per_case(self):
        args = self.args()
        self.capture(args)
        with mock.patch.object(EVAL, "prompt_for", wraps=EVAL.prompt_for) as prompt:
            record = EVAL.read_run(args.out)
        self.assertEqual(len(record["results"]), 40)
        calls = [(call.args[0]["id"], bool(call.args[1]["files"])) for call in prompt.call_args_list]
        self.assertCountEqual(calls, [(name, has_skill) for name in ("first", "second")
                                     for has_skill in (True, False)])

    def test_cached_prompt_hashes_still_validate_every_repeated_row(self):
        args = self.args()
        record = self.capture(args)
        tampered_path = self.root / "tampered.json"
        for index in range(len(record["results"])):
            for field, message in (("input_sha256", "input hash mismatch"),
                                   ("prompt_sha256", "prompt hash mismatch")):
                with self.subTest(row=index, field=field):
                    tampered = json.loads(json.dumps(record))
                    tampered["results"][index][field] = "0" * 64
                    tampered.pop("sha256")
                    tampered["sha256"] = EVAL.digest(tampered)
                    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, message):
                        EVAL.read_run(tampered_path)


if __name__ == "__main__":
    unittest.main()
