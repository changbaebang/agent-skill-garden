import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/standup-draft/scripts/standup_draft.py"
SPEC = importlib.util.spec_from_file_location("standup_draft", MODULE_PATH)
assert SPEC and SPEC.loader
DRAFT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DRAFT
SPEC.loader.exec_module(DRAFT)


def evidence() -> dict:
    return {
        "report_date": "2026-05-21",
        "previous_report_date": "2026-05-20",
        "previous_next": ["Land the checkout retry fix (ABC-12)", "Monitor the release"],
        "pull_requests": [
            {"number": 101, "title": "Retry failed checkout submits", "state": "merged",
             "updated_at": "2026-05-20T10:12:00Z", "role": "author"},
            {"number": 104, "title": "Split the cart hook", "state": "open",
             "updated_at": "2026-05-20T17:40:00Z", "role": "author"},
            {"number": 90, "title": "Old change", "state": "merged",
             "updated_at": "2026-05-01T10:00:00Z", "role": "author"},
        ],
        "issues": [
            {"key": "ABC-12", "summary": "Checkout retry", "status": "Done",
             "status_category": "done", "updated_at": "2026-05-20T11:00:00Z"},
            {"key": "ABC-20", "summary": "Banner contract", "status": "Blocked",
             "status_category": "in_progress", "blocked": True,
             "blocked_reason": "waiting on the contract", "updated_at": "2026-05-19T09:00:00Z"},
        ],
        "sessions": [{"topic": "Refactored the retry helper", "at": "2026-05-20T15:00:00Z"}],
        "gaps": ["chat: no reply in previous thread"],
    }


class WindowTests(unittest.TestCase):
    def test_default_window_is_yesterday(self):
        w = DRAFT.compute_window("2026-05-21", None)
        self.assertEqual((w["done_from"], w["done_to"], w["days"]), ("2026-05-20", "2026-05-21", 1))

    def test_weekend_widens_to_previous_standup(self):
        w = DRAFT.compute_window("2026-05-25", "2026-05-22")
        self.assertEqual(w["done_from"], "2026-05-22")
        self.assertEqual(w["days"], 3)

    def test_previous_not_before_report_is_rejected(self):
        with self.assertRaises(ValueError):
            DRAFT.compute_window("2026-05-21", "2026-05-21")

    def test_in_window_uses_date_part(self):
        w = DRAFT.compute_window("2026-05-21", None)
        self.assertTrue(DRAFT.in_window("2026-05-20T23:59:00+09:00", w))
        self.assertFalse(DRAFT.in_window("2026-05-19T23:59:00Z", w))
        self.assertFalse(DRAFT.in_window(None, w))


class CarryOverTests(unittest.TestCase):
    def test_key_match_reflects_and_missing_is_reported(self):
        item = DRAFT.Item(text="Fixed retry (ABC-12)", keys=["ABC-12"])
        result = DRAFT.carry_over(["Land the fix (ABC-12)", "Monitor the release"], [item])
        self.assertEqual(result["reflected"], ["Land the fix (ABC-12)"])
        self.assertEqual(result["unreflected"], ["Monitor the release"])


class DraftTests(unittest.TestCase):
    def render(self, data=None) -> str:
        data = data or evidence()
        window = DRAFT.compute_window(data["report_date"], data.get("previous_report_date"))
        return DRAFT.render(DRAFT.classify(data, window), window, data.get("format"))

    def test_draft_contents(self):
        text = self.render()
        self.assertIn("Draft only. Nothing was posted.", text)
        self.assertIn("101", text)
        self.assertNotIn("Old change", text)
        self.assertIn("Yesterday's next not reflected in today's done: Monitor the release", text)
        self.assertIn("chat: no reply in previous thread", text)
        self.assertIn("waiting on the contract", text)

    def test_custom_labels_and_bullet(self):
        data = evidence()
        data["format"] = {"labels": {"done": "Yesterday"}, "bullet": "*"}
        text = self.render(data)
        self.assertIn("\nYesterday\n* ", text)

    def test_cli_draft_and_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "e.json"
            path.write_text(json.dumps(evidence()), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(DRAFT.main(["draft", "--input", str(path)]), 0)
            self.assertIn("### Carry-over check", out.getvalue())
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(DRAFT.main(["window", "--date", "2026-05-21", "--json"]), 0)
            self.assertEqual(json.loads(out.getvalue())["done_from"], "2026-05-20")

    def test_cli_bad_input_returns_error(self):
        self.assertEqual(DRAFT.main(["draft", "--input", "/nonexistent/e.json"]), 1)


if __name__ == "__main__":
    unittest.main()
