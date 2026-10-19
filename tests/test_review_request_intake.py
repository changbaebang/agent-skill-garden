import importlib.util
import pathlib
import unittest

p = pathlib.Path(__file__).resolve().parents[1] / "core" / "skills" / "review-request-intake" / "scripts" / "intake_state.py"
spec = importlib.util.spec_from_file_location("intake_state", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class T(unittest.TestCase):
    def test_permalink(self):
        r = m.parse_permalink("https://chat.test/archives/CAB12/p1700000000123456")
        self.assertEqual(r["channel"], "CAB12")
        self.assertEqual(r["message_ts"], "1700000000.123456")

    def test_permalink_reply_uses_parent(self):
        r = m.parse_permalink("https://chat.test/archives/CAB12/p1700000009123456?thread_ts=1700000000.123456")
        self.assertEqual(r["thread_ts"], "1700000000.123456")

    def test_permalink_custom_pattern(self):
        r = m.parse_permalink("https://chat.test/c/ROOM9/m/42",
                              r"/c/(?P<channel>\w+)/m/(?P<message>\d+)")
        self.assertEqual((r["channel"], r["message_ts"]), ("ROOM9", "42"))

    def test_completed_head_skips_with_reply(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "a", "last_reviewed_head": "a",
                                   "my_last_review": "commented", "completed_head": "a",
                                   "author_replied_after_review": True}), "skip")

    def test_completed_head_moved(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "b", "last_reviewed_head": "a",
                                   "my_last_review": "approved", "completed_head": "a"}), "re-review")

    def test_permalink_bad(self):
        with self.assertRaises(ValueError):
            m.parse_permalink("https://chat.test/x")

    def test_withdraw_and_docs(self):
        self.assertEqual(m.decide({"state": "MERGED"}), "withdraw")
        self.assertEqual(m.decide({"state": "OPEN", "docs_only": True}), "skip-docs")

    def test_first_review(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "a"}), "review")

    def test_head_moved(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "b", "last_reviewed_head": "a",
                                   "my_last_review": "commented"}), "re-review")

    def test_author_reply_same_head(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "a", "last_reviewed_head": "a",
                                   "my_last_review": "commented",
                                   "author_replied_after_review": True}), "re-review")

    def test_nothing_changed(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "a", "last_reviewed_head": "a",
                                   "my_last_review": "approved"}), "skip")

    def test_audit(self):
        self.assertEqual(m.decide({"state": "OPEN", "head": "a", "last_reviewed_head": "a",
                                   "my_last_review": "approved",
                                   "new_human_evidence_same_head": True}), "audit")


if __name__ == "__main__":
    unittest.main()
