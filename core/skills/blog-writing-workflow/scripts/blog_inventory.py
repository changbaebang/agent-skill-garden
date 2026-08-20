#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
KEY_VALUE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
EXCLUDED_PARTS = {
    ".git",
    ".agent-blog",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "_site",
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
    return fields, text[match.end() :]


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts)
    )


def body_metrics(body: str) -> dict[str, int]:
    paragraphs = [
        block.strip()
        for block in re.split(r"\n\s*\n", body)
        if block.strip()
        and not block.lstrip().startswith(("#", "- ", "* ", ">", "```"))
    ]
    return {
        "characters": len(body),
        "whitespace_tokens": len(re.findall(r"\S+", body)),
        "paragraphs": len(paragraphs),
        "h2_headings": len(re.findall(r"^##\s+", body, re.MULTILINE)),
        "h3_headings": len(re.findall(r"^###\s+", body, re.MULTILINE)),
        "list_items": len(re.findall(r"^\s*(?:[-*+] |\d+\. )", body, re.MULTILINE)),
        "code_blocks": len(re.findall(r"^```", body, re.MULTILINE)) // 2,
        "blockquotes": len(re.findall(r"^>\s?", body, re.MULTILINE)),
        "links": len(re.findall(r"(?<!!)\[[^\]]+\]\([^)]+\)", body)),
        "images": len(re.findall(r"!\[[^\]]*\]\([^)]+\)", body)),
    }


def rounded_average(values: list[int]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def select_samples(records: list[dict[str, object]], sample_size: int) -> list[str]:
    ranked = sorted(
        records,
        key=lambda item: (
            str(item["date"]),
            str(item["path"]),
        ),
        reverse=True,
    )
    if len(ranked) <= sample_size:
        return [str(item["path"]) for item in ranked]

    recent_count = max(1, sample_size // 2)
    selected = ranked[:recent_count]
    remaining = sorted(
        ranked[recent_count:],
        key=lambda item: int(item["metrics"]["characters"]),  # type: ignore[index]
        reverse=True,
    )
    slots = sample_size - len(selected)
    if slots:
        step = max(1, len(remaining) // slots)
        selected.extend(remaining[index] for index in range(0, len(remaining), step))
    return [str(item["path"]) for item in selected[:sample_size]]


def build_inventory(root: Path, sample_size: int) -> dict[str, object]:
    records: list[dict[str, object]] = []
    key_counts: Counter[str] = Counter()

    for path in markdown_files(root):
        text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        fields, body = parse_frontmatter(text)
        key_counts.update(fields.keys())
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "date": fields.get("date", ""),
                "metrics": body_metrics(body),
            }
        )

    metric_names = tuple(body_metrics("").keys())
    averages = {
        name: rounded_average(
            [int(record["metrics"][name]) for record in records]  # type: ignore[index]
        )
        for name in metric_names
    }
    return {
        "schema_version": 1,
        "source_name": root.name,
        "post_count": len(records),
        "frontmatter_key_counts": dict(sorted(key_counts.items())),
        "average_body_metrics": averages,
        "sample_paths": select_samples(records, sample_size),
        "privacy_note": "No article body text or frontmatter values are included.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a privacy-conscious Markdown blog inventory"
    )
    parser.add_argument("source", type=Path, help="Blog source directory")
    parser.add_argument("--output", type=Path, help="Write JSON to this path")
    parser.add_argument("--sample-size", type=int, default=12)
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    if args.sample_size < 1:
        parser.error("--sample-size must be at least 1")

    payload = json.dumps(build_inventory(source, args.sample_size), indent=2) + "\n"
    if args.output:
        output = args.output.expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
