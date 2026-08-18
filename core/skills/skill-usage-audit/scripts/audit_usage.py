#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


CATEGORY_RULES = [
    ("skill-maintenance", re.compile(r"스킬|skill|agent.?skill|claude|codex|cursor", re.I)),
    ("code-review", re.compile(r"코드\s*리뷰|pr\s*리뷰|재리뷰|review|release.?block|approve", re.I)),
    ("issue-planning", re.compile(r"jira|ticket|티켓|범위|scope|요구사항|acceptance|story.?point|estimate", re.I)),
    ("release-deploy", re.compile(r"배포|deploy|release|qa|stage|staging|smoke", re.I)),
    ("incident-observability", re.compile(r"장애|incident|sentry|grafana|datadog|monitor|알림|voc", re.I)),
    ("testing-verification", re.compile(r"검증|verify|test|테스트|lint|type.?check|ci|부작용|side.?effect", re.I)),
    ("knowledge-writing", re.compile(r"문서|블로그|회고|draft|초안|write|publish|confluence|wiki", re.I)),
    ("git-collaboration", re.compile(r"github|pull request|\bpr\b|commit|커밋|push|merge|머지|branch|브랜치", re.I)),
    ("local-development", re.compile(r"로컬|local|dev.?server|서버|mkcert|localhost", re.I)),
    ("research-learning", re.compile(r"조사|research|learn|학습|비교|찾아|설명", re.I)),
    ("implementation", re.compile(r"구현|수정|리팩터|refactor|bug|버그|fix|code|코드", re.I)),
]

SYSTEM_PROMPT = re.compile(
    r"^\s*(?:<heartbeat>|<recommended_plugins>|<task-notification>|<command-|"
    r"<local-command|<environment_context>|<skills_instructions>|<app-context>|"
    r"<permissions instructions>|<apps_instructions>|<plugins_instructions>|"
    r"<collaboration_mode>|# AGENTS\.md instructions)",
    re.I,
)
SKILL_PATH = re.compile(r"(?:^|[/\\])skills[/\\](?:\.system[/\\])?([a-z0-9:_-]+)[/\\]SKILL\.md", re.I)
SKILL_URI = re.compile(r"skill://(?:[^/]+/)?([a-z0-9:_-]+)/SKILL\.md", re.I)
SKILL_DOLLAR = re.compile(r"(?:^|[\s`])\$([a-z0-9][a-z0-9:_-]*)(?=[\s`,.)\]}]|$)", re.I)
SKILL_SLASH = re.compile(r"^\s*/([a-z0-9][a-z0-9:_-]*)(?=\s|$)", re.I)


@dataclass
class Turn:
    host: str
    category: str
    timestamp: str
    skills: set[str] = field(default_factory=set)
    tool_calls: int = 0
    tools_before_first_skill: int | None = None

    @property
    def has_skill_evidence(self) -> bool:
        return bool(self.skills)

    @property
    def skill_first(self) -> bool:
        return self.has_skill_evidence and self.tools_before_first_skill == 0


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def category_for(prompt: str) -> str:
    for name, pattern in CATEGORY_RULES:
        if pattern.search(prompt):
            return name
    return "other"


def explicit_skills(prompt: str, installed: set[str]) -> set[str]:
    candidates = set(SKILL_DOLLAR.findall(prompt)) | set(SKILL_SLASH.findall(prompt))
    return {name.lower() for name in candidates if not installed or name.lower() in installed}


def text_blocks(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") in {"text", "input_text"}
    ).strip()


def installed_skills(roots: Iterable[Path]) -> set[str]:
    result: set[str] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                result.add(entry.name.lower())
    return result


def claude_files(root: Path) -> Iterable[Path]:
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob("*/*.jsonl") if path.is_file())


def parse_claude(root: Path, cutoff: datetime, installed: set[str]) -> list[Turn]:
    turns: list[Turn] = []
    for path in claude_files(root):
        if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            continue
        current: Turn | None = None
        with path.open(encoding="utf-8", errors="replace") as stream:
            for raw_line in stream:
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                timestamp = parse_timestamp(event.get("timestamp"))
                if timestamp and timestamp < cutoff:
                    continue
                event_type = event.get("type")
                message = event.get("message") if isinstance(event.get("message"), dict) else {}
                content = message.get("content")

                if event_type == "user":
                    if event.get("isMeta") or event.get("sourceToolUseID"):
                        continue
                    prompt = text_blocks(content).strip()
                    if not prompt or SYSTEM_PROMPT.search(prompt):
                        continue
                    skills = explicit_skills(prompt, installed)
                    current = Turn(
                        host="claude",
                        category=category_for(prompt),
                        timestamp=(timestamp or datetime.now(timezone.utc)).isoformat(),
                        skills=skills,
                        tools_before_first_skill=0 if skills else None,
                    )
                    turns.append(current)
                    continue

                if event_type != "assistant" or current is None or not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    if block.get("name") == "Skill":
                        tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                        skill_name = tool_input.get("skill")
                        if isinstance(skill_name, str) and skill_name:
                            current.skills.add(skill_name.lower())
                            if current.tools_before_first_skill is None:
                                current.tools_before_first_skill = current.tool_calls
                    else:
                        current.tool_calls += 1
    return turns


def codex_skill_reads(arguments: str) -> set[str]:
    return {name.lower() for name in SKILL_PATH.findall(arguments) + SKILL_URI.findall(arguments)}


def parse_codex(root: Path, cutoff: datetime, installed: set[str]) -> list[Turn]:
    turns: list[Turn] = []
    if not root.is_dir():
        return []
    for path in sorted(root.glob("**/*.jsonl")):
        if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            continue
        current_turn_id: str | None = None
        current: Turn | None = None
        with path.open(encoding="utf-8", errors="replace") as stream:
            for raw_line in stream:
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                timestamp = parse_timestamp(event.get("timestamp"))
                if timestamp and timestamp < cutoff:
                    continue
                payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
                if event.get("type") == "turn_context" and isinstance(payload.get("turn_id"), str):
                    current_turn_id = payload["turn_id"]
                    current = None
                    continue
                if event.get("type") == "event_msg" and payload.get("type") == "user_message":
                    prompt = payload.get("message")
                    if not isinstance(prompt, str):
                        continue
                    prompt = prompt.strip()
                    if not prompt or SYSTEM_PROMPT.search(prompt):
                        continue
                    skills = explicit_skills(prompt, installed)
                    current = Turn(
                        host="codex",
                        category=category_for(prompt),
                        timestamp=(timestamp or datetime.now(timezone.utc)).isoformat(),
                        skills=skills,
                        tools_before_first_skill=0 if skills else None,
                    )
                    turns.append(current)
                    continue
                if event.get("type") != "response_item":
                    continue
                event_turn_id = (
                    payload.get("internal_chat_message_metadata_passthrough", {}).get("turn_id")
                    if isinstance(payload.get("internal_chat_message_metadata_passthrough"), dict)
                    else None
                ) or current_turn_id
                if not isinstance(event_turn_id, str) or event_turn_id != current_turn_id:
                    continue
                item_type = payload.get("type")
                if item_type not in {"function_call", "custom_tool_call"}:
                    continue
                if current is None:
                    continue
                arguments = payload.get("arguments") or payload.get("input") or ""
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                skills = codex_skill_reads(arguments)
                if skills:
                    current.skills.update(skills)
                    if current.tools_before_first_skill is None:
                        current.tools_before_first_skill = current.tool_calls
                current.tool_calls += 1
    return turns


def host_summary(turns: list[Turn], installed: set[str]) -> dict[str, object]:
    evidenced = [turn for turn in turns if turn.has_skill_evidence]
    counts = Counter(skill for turn in turns for skill in turn.skills)
    return {
        "tasks": len(turns),
        "skill_evidence_tasks": len(evidenced),
        "skill_first_tasks": sum(turn.skill_first for turn in evidenced),
        "installed_skills": len(installed),
        "evidenced_skills": len(counts),
        "no_evidence_skills": sorted(installed - set(counts)),
        "top_skills": counts.most_common(10),
    }


def build_report(
    turns: list[Turn],
    by_host_installed: dict[str, set[str]],
    days: int,
) -> dict[str, object]:
    category_counts = Counter(turn.category for turn in turns)
    category_evidence = Counter(turn.category for turn in turns if turn.has_skill_evidence)
    category_first = Counter(turn.category for turn in turns if turn.skill_first)
    total = len(turns)
    categories = [
        {
            "category": category,
            "tasks": count,
            "share": round(count / total, 4) if total else 0,
            "skill_evidence_tasks": category_evidence[category],
            "skill_first_tasks": category_first[category],
        }
        for category, count in category_counts.most_common()
    ]
    candidates = [
        row
        for row in categories
        if row["tasks"] >= 3
        and row["skill_evidence_tasks"] / row["tasks"] < 0.5
    ]
    return {
        "period_days": days,
        "privacy": "Raw prompts are classified in memory and are not included in this report.",
        "limitations": [
            "Task categories are keyword-based signals, not time tracking or productivity scores.",
            "Codex skill evidence is inferred from explicit invocation or SKILL.md reads.",
            "No evidence does not prove that a skill was never selected.",
        ],
        "total_tasks": total,
        "focus_categories": categories[:5],
        "categories": categories,
        "repeated_unstructured_candidates": candidates,
        "hosts": {
            host: host_summary([turn for turn in turns if turn.host == host], installed)
            for host, installed in by_host_installed.items()
        },
    }


def print_markdown(report: dict[str, object]) -> None:
    print("# Local agent workflow audit")
    print()
    print(f"- Period: last {report['period_days']} day(s)")
    print(f"- Tasks classified: {report['total_tasks']}")
    print(f"- Privacy: {report['privacy']}")
    print()
    print("## Focus work signals")
    print()
    print("| Category | Tasks | Share | Skill evidence | Skill-first |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for row in report["focus_categories"]:
        print(
            f"| {row['category']} | {row['tasks']} | {row['share']:.1%} | "
            f"{row['skill_evidence_tasks']} | {row['skill_first_tasks']} |"
        )
    print()
    print("## Host summaries")
    for host, summary in report["hosts"].items():
        print()
        print(f"### {host}")
        print(f"- Tasks: {summary['tasks']}")
        print(f"- Tasks with skill evidence: {summary['skill_evidence_tasks']}")
        print(f"- Skill-first evidence: {summary['skill_first_tasks']}")
        print(f"- Installed / evidenced skills: {summary['installed_skills']} / {summary['evidenced_skills']}")
        if summary["top_skills"]:
            top = ", ".join(f"{name} ({count})" for name, count in summary["top_skills"])
            print(f"- Top skill evidence: {top}")
        if summary["no_evidence_skills"]:
            print(f"- Installed with no evidence in this window: {', '.join(summary['no_evidence_skills'])}")
    print()
    print("## Repeated work to inspect")
    print()
    candidates = report["repeated_unstructured_candidates"]
    if candidates:
        for row in candidates:
            print(
                f"- {row['category']}: {row['tasks']} task(s), "
                f"{row['skill_evidence_tasks']} with skill evidence"
            )
    else:
        print("- No category crossed the default repetition and low-evidence thresholds.")
    print()
    print("## Interpretation limits")
    for limitation in report["limitations"]:
        print(f"- {limitation}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit local Claude Code and Codex workflow evidence without exporting prompts"
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--host", choices=["all", "claude", "codex"], default="all")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--claude-sessions", type=Path, default=Path.home() / ".claude" / "projects")
    parser.add_argument("--codex-sessions", type=Path, default=Path.home() / ".codex" / "sessions")
    parser.add_argument("--claude-skills", type=Path, default=Path.home() / ".claude" / "skills")
    parser.add_argument("--shared-skills", type=Path, default=Path.home() / ".agents" / "skills")
    args = parser.parse_args()
    if args.days <= 0:
        parser.error("--days must be positive")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    by_host_installed: dict[str, set[str]] = {}
    turns: list[Turn] = []
    if args.host in {"all", "claude"}:
        claude_installed = installed_skills([args.claude_skills, args.shared_skills])
        by_host_installed["claude"] = claude_installed
        turns.extend(parse_claude(args.claude_sessions, cutoff, claude_installed))
    if args.host in {"all", "codex"}:
        codex_installed = installed_skills([args.shared_skills])
        by_host_installed["codex"] = codex_installed
        turns.extend(parse_codex(args.codex_sessions, cutoff, codex_installed))

    report = build_report(turns, by_host_installed, args.days)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
