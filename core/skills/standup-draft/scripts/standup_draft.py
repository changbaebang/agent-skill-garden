#!/usr/bin/env python3
"""Assemble a standup draft from already-collected evidence.

Two subcommands:

``window``  computes the report date and the span that counts as "done".
``draft``   reads an evidence JSON document (see references/sources.md) and
            prints the draft, the evidence table, confidence, and the
            carry-over check.

The script performs no lookups. Collecting records from chat, the code host,
the tracker, and local sessions belongs to the caller, so the classification
and cross-check logic stays testable offline.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence

KEY_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
MAX_BULLETS = 7
MAX_OPEN_ASSIGNMENTS = 5
DEFAULT_LABELS = {"done": "Done", "next": "Next", "blockers": "Blockers"}
DEFAULT_BULLET = "-"
HARD_SOURCES = ("pr", "tracker", "chat")


# --------------------------------------------------------------------------- window


def compute_window(report: Optional[str], previous: Optional[str], today: Optional[date] = None) -> dict:
    """Return the report date and the inclusive done window as ISO dates.

    The done window starts at the previous report date when one is given and
    at the day before the report otherwise. Both ends are inclusive: work that
    landed on the morning of the report still counts as done.
    """
    report_date = date.fromisoformat(report) if report else (today or date.today())
    if previous:
        start = date.fromisoformat(previous)
        if start >= report_date:
            raise ValueError("previous report date must be earlier than the report date")
    else:
        start = report_date - timedelta(days=1)
    return {
        "report_date": report_date.isoformat(),
        "done_from": start.isoformat(),
        "done_to": report_date.isoformat(),
        "days": (report_date - start).days,
    }


def in_window(timestamp: Optional[str], window: dict) -> bool:
    """Compare on the date part only; timestamps arrive in several zones."""
    if not timestamp or len(timestamp) < 10:
        return False
    day = timestamp[:10]
    return window["done_from"] <= day <= window["done_to"]


# --------------------------------------------------------------------------- items


@dataclass
class Item:
    text: str
    sources: List[str] = field(default_factory=list)
    kinds: List[str] = field(default_factory=list)
    keys: List[str] = field(default_factory=list)
    carried: bool = False

    def add(self, kind: str, source: str) -> None:
        if source not in self.sources:
            self.sources.append(source)
        if kind not in self.kinds:
            self.kinds.append(kind)

    @property
    def confidence(self) -> str:
        if len(self.kinds) >= 2:
            return "high"
        if any(kind in HARD_SOURCES for kind in self.kinds):
            return "medium"
        return "low"


def extract_keys(text: str, given: Optional[Iterable[str]] = None) -> List[str]:
    keys = list(given or [])
    for match in KEY_PATTERN.findall(text or ""):
        if match not in keys:
            keys.append(match)
    return keys


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _merge_by_key(items: List[Item], candidate: Item) -> Item:
    """Fold a candidate into an existing item that shares a tracker key."""
    for item in items:
        if set(item.keys) & set(candidate.keys):
            for kind, source in zip(candidate.kinds, candidate.sources):
                item.add(kind, source)
            for key in candidate.keys:
                if key not in item.keys:
                    item.keys.append(key)
            return item
    items.append(candidate)
    return candidate


def _record_keys(record: dict, *fields: str) -> List[str]:
    text = " ".join(str(record.get(name, "")) for name in fields)
    return extract_keys(text, record.get("keys"))


# --------------------------------------------------------------------------- classify


def classify(evidence: dict, window: dict) -> dict:
    done: List[Item] = []
    next_items: List[Item] = []
    blockers: List[Item] = []
    skipped = 0
    reviewed: List[str] = []

    for pr in evidence.get("pull_requests", []):
        number = pr.get("number", "?")
        state = str(pr.get("state", "")).lower()
        role = str(pr.get("role", "author")).lower()
        stamp = pr.get("merged_at") if state == "merged" else pr.get("updated_at")
        if not in_window(stamp or pr.get("updated_at"), window):
            skipped += 1
            continue
        if role == "reviewer":
            reviewed.append(f"pr #{number} reviewed")
            continue
        keys = _record_keys(pr, "title", "body")
        title = pr.get("title", f"pull request #{number}")
        if state == "merged":
            item = Item(f"Merged: {title}", keys=keys)
            item.add("pr", f"pr #{number} merged")
            _merge_by_key(done, item)
        elif state == "open":
            item = Item(f"Land: {title}", keys=keys)
            item.add("pr", f"pr #{number} open")
            _merge_by_key(next_items, item)
        else:
            skipped += 1

    if reviewed:
        item = Item(f"Reviewed {len(reviewed)} pull request{'s' if len(reviewed) != 1 else ''}")
        for source in reviewed:
            item.add("pr", source)
        done.append(item)

    for issue in evidence.get("issues", []):
        key = issue.get("key", "")
        summary = issue.get("summary", "")
        category = str(issue.get("status_category", "")).lower()
        status = issue.get("status", category)
        keys = _record_keys(issue, "key", "summary")
        label = f"{key} {summary}".strip()
        changed = in_window(issue.get("updated_at"), window)
        if issue.get("blocked"):
            reason = issue.get("blocked_reason") or "confirm schedule or owner"
            item = Item(f"{label}: {reason}", keys=keys)
            item.add("tracker", f"tracker {key} blocked")
            _merge_by_key(blockers, item)
            continue
        if category == "done":
            if changed:
                item = Item(f"Closed: {label}", keys=keys)
                item.add("tracker", f"tracker {key} → {status}")
                _merge_by_key(done, item)
            else:
                skipped += 1
            continue
        if category == "in_progress":
            if changed:
                progress = Item(f"Progressed: {label}", keys=keys)
                progress.add("tracker", f"tracker {key} updated")
                _merge_by_key(done, progress)
            item = Item(f"Continue: {label}", keys=keys)
            item.add("tracker", f"tracker {key} {status}")
            _merge_by_key(next_items, item)

    for session in evidence.get("sessions", []):
        if not in_window(session.get("at"), window):
            skipped += 1
            continue
        topic = session.get("topic", "").strip()
        if not topic:
            continue
        item = Item(topic, keys=extract_keys(topic, session.get("keys")))
        item.add("session", "local session")
        if item.keys:
            _merge_by_key(done, item)
        else:
            done.append(item)

    for text in evidence.get("next", []):
        item = Item(str(text), keys=extract_keys(str(text)))
        item.add("chat", "chat thread")
        _merge_by_key(next_items, item)

    for text in evidence.get("blockers", []):
        item = Item(str(text), keys=extract_keys(str(text)))
        item.add("chat", "chat thread")
        _merge_by_key(blockers, item)

    carry = carry_over(evidence.get("previous_next", []), done)
    ordered_next: List[Item] = []
    for text in carry["unreflected"]:
        item = Item(str(text), keys=extract_keys(str(text)), carried=True)
        item.add("chat", "previous standup next")
        existing = _merge_by_key(ordered_next, item)
        existing.carried = True
    for item in next_items:
        _merge_by_key(ordered_next, item)
    ordered_next.sort(key=lambda entry: 0 if entry.carried else 1)

    open_assignments: List[str] = []
    if not ordered_next:
        previous_keys = set()
        for text in evidence.get("previous_next", []):
            previous_keys.update(extract_keys(str(text)))
        candidates = [
            issue
            for issue in evidence.get("issues", [])
            if str(issue.get("status_category", "")).lower() != "done"
            and issue.get("key") not in previous_keys
        ]
        candidates.sort(key=lambda issue: issue.get("updated_at", ""), reverse=True)
        for issue in candidates[:MAX_OPEN_ASSIGNMENTS]:
            open_assignments.append(f"{issue.get('key', '')} {issue.get('summary', '')}".strip())

    return {
        "done": done,
        "next": ordered_next,
        "blockers": blockers,
        "carry_over": carry,
        "open_assignments": open_assignments,
        "skipped": skipped,
        "gaps": list(evidence.get("gaps", [])),
    }


def carry_over(previous_next: Sequence[str], done: Sequence[Item]) -> dict:
    """Match yesterday's next items against today's done by key, then by text."""
    done_keys = {key for item in done for key in item.keys}
    done_text = [_normalize(item.text) for item in done]
    reflected: List[str] = []
    unreflected: List[str] = []
    for text in previous_next:
        text = str(text)
        keys = extract_keys(text)
        if keys and set(keys) & done_keys:
            reflected.append(text)
            continue
        normalized = _normalize(text)
        if normalized and any(normalized in entry or entry in normalized for entry in done_text if entry):
            reflected.append(text)
            continue
        unreflected.append(text)
    return {"reflected": reflected, "unreflected": unreflected}


# --------------------------------------------------------------------------- render


def section_confidence(items: Sequence[Item]) -> str:
    if not items:
        return "n/a"
    order = {"low": 0, "medium": 1, "high": 2}
    weakest = min(items, key=lambda item: order[item.confidence])
    weak_lines = [item.text for item in items if item.confidence == "low"]
    if weak_lines:
        return f"{weakest.confidence} (session-only: {'; '.join(weak_lines)})"
    return weakest.confidence


def render(result: dict, window: dict, fmt: Optional[dict] = None) -> str:
    fmt = fmt or {}
    labels = dict(DEFAULT_LABELS)
    labels.update(fmt.get("labels", {}))
    bullet = fmt.get("bullet", DEFAULT_BULLET)
    report = date.fromisoformat(window["report_date"])
    lines: List[str] = []
    lines.append(f"## Standup draft — {report.isoformat()} ({report.strftime('%A')})")
    lines.append("")
    lines.append("> Draft only. Nothing was posted. Review it, then paste it into the thread yourself.")
    lines.append("")

    overflow: Dict[str, int] = {}

    def emit(name: str, items: Sequence[Item], empty_line: Optional[str]) -> None:
        if not items and empty_line is None:
            return
        lines.append(labels[name])
        if not items:
            lines.append(f"{bullet} {empty_line}")
        shown = list(items[:MAX_BULLETS])
        if len(items) > MAX_BULLETS:
            overflow[name] = len(items) - MAX_BULLETS
        for item in shown:
            suffix = " (carried over from yesterday)" if item.carried else ""
            lines.append(f"{bullet} {item.text}{suffix}")
        lines.append("")

    emit("done", result["done"], "No completed work found in the sources")
    emit("next", result["next"], "No confirmed next item")
    emit("blockers", result["blockers"], None)

    if result["open_assignments"]:
        lines.append("Open assignments (choose from these; links come from the tracker)")
        for entry in result["open_assignments"]:
            lines.append(f"{bullet} {entry}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### Evidence (review only, do not post)")
    lines.append("| Item | Sources |")
    lines.append("| --- | --- |")
    for name in ("done", "next", "blockers"):
        for item in result[name]:
            lines.append(f"| {item.text} | {' · '.join(item.sources)} |")
    for name, count in overflow.items():
        lines.append(f"| {labels[name]} overflow | {count} more item(s) not shown above |")
    if result["skipped"]:
        lines.append(f"| Skipped | {result['skipped']} record(s) outside {window['done_from']}..{window['done_to']} |")
    lines.append("")
    lines.append("### Confidence")
    lines.append(f"- {labels['done']}: {section_confidence(result['done'])}")
    lines.append(f"- {labels['next']}: {section_confidence(result['next'])}")
    lines.append(f"- {labels['blockers']}: {section_confidence(result['blockers'])}")
    lines.append("")
    lines.append("### Carry-over check")
    unreflected = result["carry_over"]["unreflected"]
    lines.append(
        "- Yesterday's next not reflected in today's done: "
        + ("; ".join(unreflected) if unreflected else "none")
    )
    gaps = result["gaps"]
    lines.append("- Sources not checked: " + ("; ".join(gaps) if gaps else "none"))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- cli


def load_evidence(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    window_parser = sub.add_parser("window", help="compute the report date and done window")
    window_parser.add_argument("--date", help="report date, YYYY-MM-DD; defaults to today")
    window_parser.add_argument("--previous", help="previous standup date, YYYY-MM-DD")
    window_parser.add_argument("--json", action="store_true")

    draft_parser = sub.add_parser("draft", help="render the draft from an evidence file")
    draft_parser.add_argument("--input", required=True, help="evidence JSON path, or - for stdin")
    draft_parser.add_argument("--date", help="override report_date from the file")
    draft_parser.add_argument("--previous", help="override previous_report_date from the file")

    args = parser.parse_args(argv)
    try:
        if args.command == "window":
            window = compute_window(args.date, args.previous)
            if args.json:
                print(json.dumps(window, indent=2))
            else:
                for key, value in window.items():
                    print(f"{key}: {value}")
            return 0

        evidence = load_evidence(args.input)
        window = compute_window(
            args.date or evidence.get("report_date"),
            args.previous or evidence.get("previous_report_date"),
        )
        result = classify(evidence, window)
        sys.stdout.write(render(result, window, evidence.get("format")))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
