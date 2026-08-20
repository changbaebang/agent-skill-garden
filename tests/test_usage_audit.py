import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/skill-usage-audit/scripts/audit_usage.py"
SPEC = importlib.util.spec_from_file_location("audit_usage", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def write_jsonl(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


class CategoryScoringTest(unittest.TestCase):
    """A category must follow the request, not the machine it was typed on."""

    def test_pasted_locators_are_not_scored_as_prose(self) -> None:
        # The rules match "code" and "codex"; both appear here only inside a path.
        self.assertEqual(AUDIT.category_for("이 파일 좀 봐줘 /home/me/Codes/shop/a.ts"), "other")
        self.assertEqual(
            AUDIT.category_for("이 초안 어디 있어? ~/Documents/Codex/notes.md"),
            "knowledge-writing",
        )
        self.assertEqual(
            AUDIT.category_for("https://example.com/blog/local-server-setup 이거 읽어봐"),
            "other",
        )

    def test_injected_context_is_not_scored_as_prose(self) -> None:
        block = "<ide_selection>lines 48 to 51 from /home/me/Codes/shop/a.ts</ide_selection>"
        self.assertEqual(AUDIT.category_for(block + "이 초안 어디에 있어?"), "knowledge-writing")
        self.assertEqual(AUDIT.prose(block).strip(), "")

    def test_host_names_do_not_decide_the_category(self) -> None:
        # Every transcript in scope is produced inside these tools, so their names
        # appear in requests of every kind and must not outrank the request itself.
        self.assertEqual(AUDIT.category_for("claude code 로 PR 리뷰 해줘"), "code-review")
        self.assertEqual(AUDIT.category_for("codex 에서 배포 승인 확인해줘"), "release-deploy")
        self.assertEqual(AUDIT.category_for("cursor 로 이 버그 수정해줘"), "implementation")
        self.assertEqual(AUDIT.category_for("스킬 최적화 해줘"), "skill-maintenance")

    def test_short_latin_tokens_require_word_boundaries(self) -> None:
        self.assertEqual(AUDIT.category_for("prefix 를 바꿔줘"), "other")       # not "fix"
        self.assertEqual(AUDIT.category_for("이 decision 을 기록해줘"), "other")  # not "ci"
        self.assertEqual(AUDIT.category_for("specific 한 조건 알려줘"), "other")  # not "ci"
        self.assertEqual(AUDIT.category_for("이 버그 fix 해줘"), "implementation")


class UsageAuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)
        self.cutoff = self.now - timedelta(days=1)
        self.timestamp = self.now.isoformat()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_claude_records_exact_skill_tool_evidence(self) -> None:
        secret_prompt = "PR 리뷰를 해줘 SECRET-CUSTOMER-42"
        write_jsonl(
            self.root / "project" / "session.jsonl",
            [
                {
                    "timestamp": self.timestamp,
                    "type": "user",
                    "message": {"role": "user", "content": [{"type": "text", "text": secret_prompt}]},
                },
                {
                    "timestamp": self.timestamp,
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Skill",
                                "input": {"skill": "critical-review"},
                            }
                        ],
                    },
                },
            ],
        )

        turns = AUDIT.parse_claude(self.root, self.cutoff, {"critical-review"})
        report = AUDIT.build_report(turns, {"claude": {"critical-review"}}, 1)

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].category, "code-review")
        self.assertTrue(turns[0].skill_first)
        self.assertEqual(turns[0].skills, {"critical-review"})
        self.assertNotIn(secret_prompt, json.dumps(report, ensure_ascii=False))

    def test_editor_context_blocks_do_not_become_turns_or_categories(self) -> None:
        opened_file = (
            "<ide_opened_file>The user opened the file "
            "/home/dev/Codes/shop/src/checkout.ts in the IDE.</ide_opened_file>"
        )
        selection = (
            "<ide_selection>The user selected lines 48 to 51 from "
            "/home/dev/Codes/shop/src/checkout.ts</ide_selection>"
        )
        write_jsonl(
            self.root / "project" / "session.jsonl",
            [
                {
                    "timestamp": self.timestamp,
                    "type": "user",
                    "message": {"role": "user", "content": [{"type": "text", "text": opened_file}]},
                },
                {
                    "timestamp": self.timestamp,
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": selection + "이 블로그 초안 어디에 있어?"}],
                    },
                },
            ],
        )

        turns = AUDIT.parse_claude(self.root, self.cutoff, set())

        # A context block alone is not a request, so it must not become a turn at all.
        # Left in place it would match the implementation rule through the "Codes"
        # path segment and be reported as coding work.
        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].category, "knowledge-writing")

    def test_codex_infers_skill_evidence_from_skill_file_read(self) -> None:
        turn_id = "turn-1"
        write_jsonl(
            self.root / "2026" / "08" / "18" / "session.jsonl",
            [
                {
                    "timestamp": self.timestamp,
                    "type": "turn_context",
                    "payload": {"turn_id": turn_id},
                },
                {
                    "timestamp": self.timestamp,
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "변경 부작용을 검증해줘",
                    },
                },
                {
                    "timestamp": self.timestamp,
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": {
                            "cmd": "sed -n '1,220p' /tmp/.agents/skills/side-effect-check/SKILL.md"
                        },
                    },
                },
            ],
        )

        turns = AUDIT.parse_codex(self.root, self.cutoff, {"side-effect-check"})
        report = AUDIT.build_report(turns, {"codex": {"side-effect-check"}}, 1)

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0].category, "testing-verification")
        self.assertTrue(turns[0].skill_first)
        self.assertEqual(report["hosts"]["codex"]["skill_evidence_tasks"], 1)

    def test_repeated_low_evidence_category_becomes_candidate(self) -> None:
        turns = [
            AUDIT.Turn(host="codex", category="implementation", timestamp=self.timestamp)
            for _ in range(3)
        ]

        report = AUDIT.build_report(turns, {"codex": set()}, 7)

        self.assertEqual(
            report["repeated_unstructured_candidates"],
            [
                {
                    "category": "implementation",
                    "tasks": 3,
                    "share": 1.0,
                    "skill_evidence_tasks": 0,
                    "skill_first_tasks": 0,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
