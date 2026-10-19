from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core" / "skills" / "work-request-kickoff" / "scripts" / "extract_refs.py"


def load():
    spec = importlib.util.spec_from_file_location("extract_refs", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXTRACT = load()

PERMALINK = "https://chat.example/archives/C123ABC/p1700000000123456?thread_ts=1699999999.000100"


class PermalinkTests(unittest.TestCase):
    def test_permalink_yields_channel_message_and_thread_root(self) -> None:
        result = EXTRACT.extract(PERMALINK)
        self.assertEqual(result["permalink"]["channel_id"], "C123ABC")
        self.assertEqual(result["permalink"]["message_ts"], "1700000000.123456")
        self.assertEqual(result["permalink"]["thread_root_ts"], "1699999999.000100")
        self.assertEqual(result["links"], [])
        self.assertEqual(result["tracker_keys"], [])

    def test_permalink_without_thread_parameter_has_no_root(self) -> None:
        result = EXTRACT.extract("https://chat.example/archives/C123ABC/p1700000000123456")
        self.assertIsNone(result["permalink"]["thread_root_ts"])

    def test_text_without_permalink_reports_none(self) -> None:
        result = EXTRACT.extract("Please take OPS-41 over from the platform side.")
        self.assertIsNone(result["permalink"])
        self.assertEqual(result["tracker_keys"], ["OPS-41"])

    def test_second_permalink_is_kept_as_a_link(self) -> None:
        text = PERMALINK + "\nearlier: https://chat.example/archives/C123ABC/p1600000000000001"
        result = EXTRACT.extract(text)
        self.assertEqual(result["permalink"]["message_ts"], "1700000000.123456")
        self.assertEqual(result["links"], ["https://chat.example/archives/C123ABC/p1600000000000001"])


class ReferenceTests(unittest.TestCase):
    TEXT = (
        "<@U77> @dana can you kick off OPS-41? Spec: https://wiki.example/pages/9 "
        "(see https://tracker.example/browse/OPS-41). Related: DOCS-7, and the draft "
        "https://git.example/team/repo/pull/88. Mail me at dana@mail.example."
    )

    def test_tracker_keys_are_deduplicated_in_order(self) -> None:
        result = EXTRACT.extract(self.TEXT)
        self.assertEqual(result["tracker_keys"], ["OPS-41", "DOCS-7"])

    def test_pull_requests_are_separated_from_other_links(self) -> None:
        result = EXTRACT.extract(self.TEXT)
        self.assertEqual(result["pull_requests"], ["https://git.example/team/repo/pull/88"])
        self.assertEqual(
            result["links"],
            ["https://wiki.example/pages/9", "https://tracker.example/browse/OPS-41"],
        )

    def test_mentions_exclude_email_addresses(self) -> None:
        result = EXTRACT.extract(self.TEXT)
        self.assertEqual(result["mentions"], ["<@U77>", "@dana"])

    def test_trailing_punctuation_is_not_part_of_a_link(self) -> None:
        result = EXTRACT.extract("Doc here: https://wiki.example/pages/9.")
        self.assertEqual(result["links"], ["https://wiki.example/pages/9"])

    def test_encoding_names_are_not_tracker_keys(self) -> None:
        result = EXTRACT.extract("The file is UTF-8 and the digest is SHA-256; ticket OPS-3.")
        self.assertEqual(result["tracker_keys"], ["OPS-3"])

    def test_merge_request_links_count_as_pull_requests(self) -> None:
        result = EXTRACT.extract("https://git.example/team/repo/-/merge_requests/12")
        self.assertEqual(result["pull_requests"], ["https://git.example/team/repo/-/merge_requests/12"])


class SignalTests(unittest.TestCase):
    def test_pull_request_alone_is_flagged_as_review_shape(self) -> None:
        result = EXTRACT.extract("Review please: https://git.example/team/repo/pull/88")
        self.assertTrue(result["signals"]["pull_request_only"])

    def test_pull_request_with_tracker_key_is_not_review_shape(self) -> None:
        result = EXTRACT.extract("OPS-41 draft: https://git.example/team/repo/pull/88")
        self.assertFalse(result["signals"]["pull_request_only"])

    def test_pull_request_with_document_is_not_review_shape(self) -> None:
        result = EXTRACT.extract("https://git.example/team/repo/pull/88 per https://wiki.example/pages/9")
        self.assertFalse(result["signals"]["pull_request_only"])

    def test_no_pull_request_is_not_review_shape(self) -> None:
        result = EXTRACT.extract(PERMALINK)
        self.assertFalse(result["signals"]["pull_request_only"])


class CommandLineTests(unittest.TestCase):
    def run_script(self, *args: str, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *args],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_argument_input_prints_json(self) -> None:
        completed = self.run_script(PERMALINK)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["permalink"]["channel_id"], "C123ABC")

    def test_stdin_input_is_accepted(self) -> None:
        completed = self.run_script(stdin="OPS-41 https://wiki.example/pages/9\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["tracker_keys"], ["OPS-41"])

    def test_empty_input_fails_with_exit_two(self) -> None:
        completed = self.run_script(stdin="   \n")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("empty input", completed.stderr)


if __name__ == "__main__":
    unittest.main()
