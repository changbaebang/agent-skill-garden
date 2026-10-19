#!/usr/bin/env python3
"""Deterministic helpers for the pull-request checklist workflow.

Subcommands:

  ticket-key TITLE [--project PREFIX]
      Print tracker keys found in a title, one per line, never truncated.
  classify-base BRANCH [--production REGEX ...] [--default-branch NAME]
      Print ``production-bound`` or ``integration``.
  sections --body FILE
      Print the headings found in a description, with their levels.
  upsert --body FILE --sections FILE [--order HEADING ...]
      Print the description with the given sections replaced or inserted.

No network access. Fetching and patching belong to the caller.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

TICKET_KEY = re.compile(r"\b([A-Z][A-Z0-9]*-\d+)\b")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^[ \t]{0,3}(```|~~~)")
BULLET = re.compile(r"^[ \t]*[-*+][ \t]+")
RULE = re.compile(r"^[ \t]{0,3}(<hr[ \t]*/?>|-{3,}|\*{3,}|_{3,})[ \t]*$", re.IGNORECASE)
DEFAULT_PRODUCTION = (
    r"^(main|master|trunk|prod|production|release|hotfix)$",
    r"^release/",
    r"^production/",
    r"^hotfix/",
)
PRODUCTION_BOUND = "production-bound"
INTEGRATION = "integration"


# --- ticket keys -----------------------------------------------------------


def ticket_keys(title: str, project: Optional[str] = None) -> List[str]:
    """Return unique tracker keys in order of appearance.

    The whole key is kept. ``project`` keeps only keys of that project.
    """
    found: List[str] = []
    for key in TICKET_KEY.findall(title):
        if project and key.split("-", 1)[0] != project.upper():
            continue
        if key not in found:
            found.append(key)
    return found


# --- base branch -----------------------------------------------------------


def classify_base(
    branch: str,
    production_patterns: Optional[Sequence[str]] = None,
    default_branch: Optional[str] = None,
) -> str:
    patterns = list(production_patterns) if production_patterns else list(DEFAULT_PRODUCTION)
    if default_branch and branch == default_branch:
        return PRODUCTION_BOUND
    for pattern in patterns:
        if re.search(pattern, branch):
            return PRODUCTION_BOUND
    return INTEGRATION


# --- markdown sections -----------------------------------------------------


def normalize_heading(text: str) -> str:
    return " ".join(text.split())


@dataclass
class Section:
    heading: Optional[str]  # None for the preamble before the first heading
    level: int
    heading_line: str
    lines: List[str] = field(default_factory=list)

    @property
    def key(self) -> Optional[str]:
        return normalize_heading(self.heading) if self.heading is not None else None


def parse_sections(text: str) -> List[Section]:
    """Split markdown into a preamble and heading-delimited sections.

    Headings inside fenced code blocks are content, not boundaries. Every
    heading starts a new section regardless of level; nesting is resolved by
    the caller when it needs a level-aware extent.
    """
    sections: List[Section] = [Section(None, 0, "")]
    in_fence = False
    fence_marker = ""
    for line in text.split("\n"):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, ""
            sections[-1].lines.append(line)
            continue
        heading = None if in_fence else HEADING.match(line)
        if heading:
            sections.append(Section(heading.group(2), len(heading.group(1)), line))
        else:
            sections[-1].lines.append(line)
    return sections


def _extent(sections: List[Section], index: int) -> int:
    """Index one past the last section nested under ``sections[index]``."""
    level = sections[index].level
    end = index + 1
    while end < len(sections) and sections[end].level > level:
        end += 1
    return end


def _strip_blank_edges(lines: Sequence[str]) -> List[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return list(lines[start:end])


def _comment_blocks(lines: Sequence[str]) -> List[List[str]]:
    """Return HTML comment blocks, each as its own list of whole lines."""
    blocks: List[List[str]] = []
    current: Optional[List[str]] = None
    for line in lines:
        if current is None:
            if "<!--" in line:
                current = [line]
                if "-->" in line.split("<!--", 1)[1]:
                    blocks.append(current)
                    current = None
        else:
            current.append(line)
            if "-->" in line:
                blocks.append(current)
                current = None
    return blocks


def split_tail(lines: Sequence[str]) -> "tuple[List[str], List[str]]":
    """Split section content at its first horizontal rule.

    The rule and everything after it, up to the next heading, is the template's
    tail: separators and fixed text that an author does not edit. A ``---`` line
    directly under text is a setext underline, not a rule, and stays content.
    """
    in_fence = False
    fence_marker = ""
    for index, line in enumerate(lines):
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, ""
            continue
        if in_fence or not RULE.match(line):
            continue
        if line.strip().startswith("-") and index > 0 and lines[index - 1].strip():
            continue
        return list(lines[:index]), list(lines[index:])
    return list(lines), []


def dedupe_bullets(lines: Iterable[str]) -> List[str]:
    """Drop later bullets whose stripped text repeats an earlier bullet."""
    seen = set()
    kept: List[str] = []
    for line in lines:
        if BULLET.match(line):
            text = BULLET.sub("", line).strip()
            if text in seen:
                continue
            seen.add(text)
        kept.append(line)
    return kept


def render_content(old_lines: Sequence[str], new_lines: Sequence[str]) -> List[str]:
    """Content under a heading: kept comments, then the new content.

    A horizontal rule inside the old content and everything after it is kept
    as the section's tail. Produces one blank line after the heading and one
    after the content, so a second run over the result parses back to the same
    content.
    """
    editable, tail = split_tail(_strip_blank_edges(old_lines))
    tail = _strip_blank_edges(tail)
    body = dedupe_bullets(_strip_blank_edges(new_lines))
    body_text = "\n".join(body)
    kept: List[str] = []
    for block in _comment_blocks(editable):
        if "\n".join(block) not in body_text:
            kept.extend(block)
    content = kept + ([""] if kept and body else []) + body
    if tail:
        content = content + [""] + tail
    return [""] + content + [""]


def _insert_index(
    sections: List[Section], key: str, order: Sequence[str]
) -> int:
    """Where a missing section goes: after the nearest earlier ordered section
    that exists, else before the nearest later one, else at the end."""
    ordered = [normalize_heading(item) for item in order]
    present = {section.key: index for index, section in enumerate(sections) if section.key}
    if key in ordered:
        position = ordered.index(key)
        for earlier in reversed(ordered[:position]):
            if earlier in present:
                return _extent(sections, present[earlier])
        for later in ordered[position + 1 :]:
            if later in present:
                return present[later]
    return len(sections)


def upsert_sections(body: str, replacements: str, order: Sequence[str] = ()) -> str:
    newline = "\r\n" if "\r\n" in body else "\n"
    trailing_newline = body.endswith(("\n", "\r\n"))
    sections = parse_sections(body.replace("\r\n", "\n"))
    wanted = [
        section
        for section in parse_sections(replacements.replace("\r\n", "\n"))
        if section.heading is not None
    ]
    for new in wanted:
        key = new.key
        existing = next(
            (index for index, section in enumerate(sections) if section.key == key), None
        )
        if existing is not None:
            end = _extent(sections, existing)
            old_lines: List[str] = list(sections[existing].lines)
            for nested in sections[existing + 1 : end]:
                old_lines.append(nested.heading_line)
                old_lines.extend(nested.lines)
            sections[existing].lines = render_content(old_lines, new.lines)
            del sections[existing + 1 : end]
        else:
            index = _insert_index(sections, key or "", order)
            inserted = Section(new.heading, new.level, new.heading_line)
            inserted.lines = render_content([], new.lines)
            sections.insert(index, inserted)
            previous = sections[index - 1]
            if previous.lines and previous.lines[-1].strip():
                previous.lines.append("")
    out: List[str] = []
    for section in sections:
        if section.heading is not None:
            out.append(section.heading_line)
        out.extend(section.lines)
    while out and not out[-1].strip():
        out.pop()
    text = newline.join(out)
    return text + newline if trailing_newline or not body else text


# --- command line ----------------------------------------------------------


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    key_parser = sub.add_parser("ticket-key", help="print tracker keys found in a title")
    key_parser.add_argument("title", nargs="+")
    key_parser.add_argument("--project", help="keep only keys of this project prefix")

    base_parser = sub.add_parser("classify-base", help="classify a base branch")
    base_parser.add_argument("branch")
    base_parser.add_argument(
        "--production",
        action="append",
        help="regular expression for a production-bound branch; repeatable, replaces the defaults",
    )
    base_parser.add_argument("--default-branch", help="the repository default branch name")

    list_parser = sub.add_parser("sections", help="list headings in a description")
    list_parser.add_argument("--body", required=True)

    upsert_parser = sub.add_parser("upsert", help="replace or insert sections in a description")
    upsert_parser.add_argument("--body", required=True, help="current description markdown")
    upsert_parser.add_argument("--sections", required=True, help="replacement sections markdown")
    upsert_parser.add_argument("--order", nargs="*", default=[], help="template heading order")

    args = parser.parse_args(argv)
    if args.command == "ticket-key":
        keys = ticket_keys(" ".join(args.title), args.project)
        sys.stdout.write("".join(f"{key}\n" for key in keys))
        return 0 if keys else 1
    if args.command == "classify-base":
        sys.stdout.write(classify_base(args.branch, args.production, args.default_branch) + "\n")
        return 0
    if args.command == "sections":
        for section in parse_sections(_read(args.body)):
            if section.heading is not None:
                sys.stdout.write(f"{section.level}\t{section.key}\n")
        return 0
    if args.command == "upsert":
        sys.stdout.write(upsert_sections(_read(args.body), _read(args.sections), args.order))
        return 0
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
