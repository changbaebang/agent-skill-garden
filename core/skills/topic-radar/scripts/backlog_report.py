#!/usr/bin/env python3
"""Deterministic helpers for a topic radar and its learning backlog.

summary        count backlog items by status and area and flag stale items
promote-check  verify that one item may be promoted into draft input
overlap        compare candidate titles with published titles by token overlap

The script reads local Markdown only, never the network, and its output never
includes item body text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional


FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
KEY_VALUE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-?")
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOKEN = re.compile(r"\w+")

STATUSES = ("queued", "in-progress", "done", "draft-ready", "dropped")
PROMOTABLE = ("done", "draft-ready")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "in", "is", "it", "of", "on", "or", "the", "to", "vs", "what", "when",
    "why", "with", "your",
}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key_match = KEY_VALUE.match(line)
        if key_match:
            fields[key_match.group(1)] = (key_match.group(2) or "").strip()
    return fields, text[match.end():]


def unquote(value: str) -> str:
    return value.strip().strip("\"'").strip()


def parse_list(value: str) -> list[str]:
    inner = value.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    return [unquote(item) for item in inner.split(",") if unquote(item)]


def parse_date(value: str) -> Optional[date]:
    text = unquote(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def date_from_name(path: Path) -> Optional[date]:
    match = DATE_PREFIX.match(path.name)
    return parse_date(match.group(1)) if match else None


def slug_from_name(path: Path) -> str:
    return DATE_PREFIX.sub("", path.stem, count=1) or path.stem


def section(body: str, heading: str) -> str:
    wanted = heading.strip().lower()
    headings = list(HEADING.finditer(body))
    for index, match in enumerate(headings):
        if match.group(1).strip().lower() == wanted:
            start = match.end()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
            return body[start:end]
    return ""


def section_filled(text: str) -> bool:
    """True when at least one line carries content beyond a template label."""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        line = re.sub(r"^(?:[-*+]|\d+\.)\s*", "", line)
        if line.startswith("(") and line.endswith(")"):
            continue
        if ":" in line:
            _label, _sep, rest = line.partition(":")
            if rest.strip() and " | " not in rest:
                return True
            continue
        if line:
            return True
    return False


def labelled_value(text: str, label: str) -> str:
    pattern = re.compile(
        r"^\s*(?:[-*+]\s*)?" + re.escape(label) + r"\s*:\s*(.*)$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text)
    return unquote(match.group(1)).strip("`") if match else ""


def load_items(root: Path) -> list[dict[str, object]]:
    items_dir = root / "items"
    records: list[dict[str, object]] = []
    if not items_dir.is_dir():
        return records
    for path in sorted(items_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        fields, body = parse_frontmatter(text)
        added = parse_date(fields.get("added", "")) or date_from_name(path)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "slug": slug_from_name(path),
                "status": unquote(fields.get("status", "")) or "unknown",
                "areas": parse_list(fields.get("area", "")),
                "added": added.isoformat() if added else "",
                "draft_slug": unquote(fields.get("draft_slug", "")),
                "source": unquote(fields.get("source", "")),
                "body": body,
            }
        )
    return records


def summarize(records: list[dict[str, object]], today: date, stale_days: int) -> dict[str, object]:
    status_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    stale: list[dict[str, object]] = []
    unknown: list[str] = []
    awaiting: list[dict[str, object]] = []
    promoted: list[dict[str, object]] = []

    for record in records:
        status = str(record["status"])
        status_counts[status] += 1
        for area in record["areas"]:  # type: ignore[union-attr]
            area_counts[str(area)] += 1
        if status not in STATUSES:
            unknown.append(str(record["path"]))
        added = parse_date(str(record["added"]))
        if status == "queued" and added is not None:
            age = (today - added).days
            if age >= stale_days:
                stale.append(
                    {
                        "path": record["path"],
                        "slug": record["slug"],
                        "added": record["added"],
                        "age_days": age,
                    }
                )
        if status == "done":
            awaiting.append(
                {"path": record["path"], "slug": record["slug"], "draft_slug": record["draft_slug"]}
            )
        elif status == "draft-ready":
            promoted.append(
                {"path": record["path"], "slug": record["slug"], "draft_slug": record["draft_slug"]}
            )

    stale.sort(key=lambda item: (-int(item["age_days"]), str(item["path"])))
    return {
        "schema_version": 1,
        "today": today.isoformat(),
        "stale_days": stale_days,
        "item_count": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "area_counts": dict(sorted(area_counts.items())),
        "unknown_status": unknown,
        "stale_queued": stale,
        "awaiting_promotion": awaiting,
        "draft_ready": promoted,
        "privacy_note": "Item body text is not included.",
    }


def promote_findings(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    fields, body = parse_frontmatter(text)
    findings: list[dict[str, str]] = []

    def add(level: str, check: str, detail: str) -> None:
        findings.append({"level": level, "check": check, "detail": detail})

    status = unquote(fields.get("status", "")) or "unknown"
    if status in PROMOTABLE:
        add("PASS", "status", f"status is {status}")
    else:
        add("FAIL", "status", f"status is {status}; promotion needs one of {', '.join(PROMOTABLE)}")

    if unquote(fields.get("source", "")):
        add("PASS", "source", "source link is present for the skeleton back-reference")
    else:
        add("FAIL", "source", "frontmatter source is empty")

    angle = section(body, "Draft angle")
    slug = unquote(fields.get("draft_slug", "")) or labelled_value(angle, "draft_slug")
    if not slug:
        add("FAIL", "draft_slug", "no draft slug in frontmatter or the Draft angle section")
    elif not KEBAB.match(slug):
        add("FAIL", "draft_slug", f"draft slug {slug!r} is not kebab-case")
    else:
        add("PASS", "draft_slug", f"draft slug is {slug}")

    if section_filled(section(body, "After learning")):
        add("PASS", "after_learning", "takeaways are recorded")
    else:
        add("FAIL", "after_learning", "After learning section holds only template labels")

    if section_filled(angle):
        add("PASS", "draft_angle", "draft angle is recorded")
    else:
        add("FAIL", "draft_angle", "Draft angle section holds only template labels")

    return findings


def tokens(title: str) -> set[str]:
    return {
        token
        for token in TOKEN.findall(title.lower())
        if len(token) > 1 and token not in STOPWORDS
    }


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def published_titles(source: Path) -> list[str]:
    if source.is_file():
        return [line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    titles: list[str] = []
    for path in sorted(source.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        fields, body = parse_frontmatter(text)
        title = unquote(fields.get("title", ""))
        if not title:
            heading = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
            title = heading.group(1).strip() if heading else slug_from_name(path).replace("-", " ")
        titles.append(title)
    return titles


def overlap_report(candidates: list[str], published: list[str], threshold: float) -> dict[str, object]:
    results: list[dict[str, object]] = []
    published_tokens = [(title, tokens(title)) for title in published]
    for candidate in candidates:
        candidate_tokens = tokens(candidate)
        scored = sorted(
            (
                {"title": title, "score": round(jaccard(candidate_tokens, pub_tokens), 3)}
                for title, pub_tokens in published_tokens
            ),
            key=lambda item: (-float(item["score"]), str(item["title"])),
        )
        matches = [item for item in scored if float(item["score"]) >= threshold]
        results.append(
            {
                "candidate": candidate,
                "best_score": float(scored[0]["score"]) if scored else 0.0,
                "matches": matches,
            }
        )
    return {
        "schema_version": 1,
        "threshold": threshold,
        "published_count": len(published),
        "results": results,
    }


def print_summary(report: dict[str, object]) -> None:
    print(f"items: {report['item_count']}")
    for status, count in report["status_counts"].items():  # type: ignore[union-attr]
        print(f"  {status}: {count}")
    if report["area_counts"]:
        print("areas:")
        for area, count in report["area_counts"].items():  # type: ignore[union-attr]
            print(f"  {area}: {count}")
    if report["unknown_status"]:
        print("unknown status:")
        for path in report["unknown_status"]:  # type: ignore[union-attr]
            print(f"  {path}")
    print(f"stale queued (>= {report['stale_days']} days): {len(report['stale_queued'])}")  # type: ignore[arg-type]
    for item in report["stale_queued"]:  # type: ignore[union-attr]
        print(f"  {item['slug']} added {item['added']} ({item['age_days']} days)")
    print(f"awaiting promotion: {len(report['awaiting_promotion'])}")  # type: ignore[arg-type]
    for item in report["awaiting_promotion"]:  # type: ignore[union-attr]
        print(f"  {item['slug']} -> {item['draft_slug'] or '(no draft slug)'}")
    print(f"draft-ready: {len(report['draft_ready'])}")  # type: ignore[arg-type]
    for item in report["draft_ready"]:  # type: ignore[union-attr]
        print(f"  {item['slug']} -> {item['draft_slug'] or '(no draft slug)'}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Topic radar backlog helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    summary = sub.add_parser("summary", help="count items by status and area")
    summary.add_argument("root", type=Path, help="radar root containing items/")
    summary.add_argument("--today", type=str, default=None, help="YYYY-MM-DD, default today")
    summary.add_argument("--stale-days", type=int, default=30)
    summary.add_argument("--json", action="store_true")

    check = sub.add_parser("promote-check", help="verify promotion preconditions")
    check.add_argument("item", type=Path, help="path to one item file")
    check.add_argument("--json", action="store_true")

    overlap = sub.add_parser("overlap", help="compare candidate titles with published titles")
    overlap.add_argument("titles", nargs="+", help="candidate titles")
    overlap.add_argument("--published", type=Path, required=True, help="title list file or posts directory")
    overlap.add_argument("--threshold", type=float, default=0.5)
    overlap.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "summary":
        root = args.root.expanduser().resolve()
        if not root.is_dir():
            parser.error(f"root is not a directory: {root}")
        if args.stale_days < 0:
            parser.error("--stale-days must be zero or more")
        today = parse_date(args.today) if args.today else date.today()
        if today is None:
            parser.error("--today must be YYYY-MM-DD")
        report = summarize(load_items(root), today, args.stale_days)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_summary(report)
        return 0

    if args.command == "promote-check":
        item = args.item.expanduser()
        if not item.is_file():
            parser.error(f"item is not a file: {item}")
        findings = promote_findings(item)
        failed = any(finding["level"] == "FAIL" for finding in findings)
        if args.json:
            print(json.dumps({"item": item.name, "ready": not failed, "findings": findings}, indent=2))
        else:
            for finding in findings:
                print(f"{finding['level']:4} {finding['check']}: {finding['detail']}")
            print("READY" if not failed else "BLOCKED")
        return 1 if failed else 0

    published = args.published.expanduser()
    if not published.exists():
        parser.error(f"published index not found: {published}")
    if not 0.0 <= args.threshold <= 1.0:
        parser.error("--threshold must be between 0 and 1")
    report = overlap_report(args.titles, published_titles(published), args.threshold)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for result in report["results"]:  # type: ignore[union-attr]
            matches = result["matches"]
            state = "OVERLAP" if matches else "clear"
            print(f"{state:7} {result['candidate']} (best {result['best_score']:.2f})")
            for match in matches:
                print(f"        {match['score']:.2f} {match['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
