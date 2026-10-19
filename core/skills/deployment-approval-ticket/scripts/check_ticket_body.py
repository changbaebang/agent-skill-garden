#!/usr/bin/env python3
"""Check a drafted approval-ticket body against the headings the guide requires.

An approval automation reads heading text literally and expects the answer list
to begin on the line after the heading. This check reproduces those rules so a
draft fails here, before creation, instead of on deployment morning.

The required headings are an input. They come from the live guide on every run;
nothing here knows what they are.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Tuple

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
CHECKED_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[[xX]\]")
TEMPLATE_BRACE = re.compile(r"\{[^{}\n]*\}")
FENCE = re.compile(r"^\s*(```|~~~)")
BOLD_LABEL = re.compile(r"^\*\*[^*]+\*\*:?\s*")


@dataclass
class Finding:
    level: str
    subject: str
    message: str


def loose(text: str) -> str:
    """Comparison key for near-miss detection: case, spacing, and punctuation folded."""
    return re.sub(r"[\W_]+", "", text).casefold()


def body_lines(text: str) -> List[Tuple[int, str, bool]]:
    """Return (line number, line, inside fenced code) for every line."""
    result: List[Tuple[int, str, bool]] = []
    fenced = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            fenced = not fenced
            result.append((number, line, True))
            continue
        result.append((number, line, fenced))
    return result


def headings(lines: List[Tuple[int, str, bool]]) -> List[Tuple[int, int, str]]:
    """Return (index into lines, level, heading text) for every heading outside code."""
    found: List[Tuple[int, int, str]] = []
    for index, (_, line, fenced) in enumerate(lines):
        if fenced:
            continue
        match = HEADING.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2).strip()))
    return found


def item_text(line: str) -> str:
    match = LIST_ITEM.match(line)
    text = match.group(1).strip() if match else ""
    text = BOLD_LABEL.sub("", text).strip()
    return text


def check_section(
    lines: List[Tuple[int, str, bool]],
    start: int,
    heading: str,
    findings: List[Finding],
) -> None:
    """Validate the lines that follow a required heading until the next heading."""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        number, line, fenced = lines[index]
        if not fenced and HEADING.match(line):
            end = index
            break

    first: Optional[int] = None
    for index in range(start + 1, end):
        if lines[index][1].strip():
            first = index
            break

    if first is None:
        findings.append(Finding("FAIL", heading, "nothing follows the heading"))
        return
    number, line, _ = lines[first]
    if not LIST_ITEM.match(line):
        findings.append(
            Finding(
                "FAIL",
                heading,
                f"line {number} follows the heading but is not a list item; "
                "the automation reads the section as missing",
            )
        )
        return

    findings.append(Finding("PASS", heading, f"list item starts on line {number}"))
    for index in range(first, end):
        number, line, fenced = lines[index]
        if fenced or not LIST_ITEM.match(line):
            continue
        if not item_text(line):
            findings.append(
                Finding("FAIL", heading, f"line {number} is an empty list item; write the answer")
            )


def check(body: str, required: List[str], allow_checked: bool = False) -> List[Finding]:
    findings: List[Finding] = []
    lines = body_lines(body)
    found = headings(lines)

    for heading in required:
        exact = [index for index, _, text in found if text == heading]
        if len(exact) == 1:
            check_section(lines, exact[0], heading, findings)
        elif len(exact) > 1:
            numbers = ", ".join(str(lines[index][0]) for index in exact)
            findings.append(Finding("FAIL", heading, f"heading appears more than once (lines {numbers})"))
        else:
            near = [text for _, _, text in found if loose(text) == loose(heading) or loose(heading) in loose(text)]
            if near:
                findings.append(
                    Finding(
                        "FAIL",
                        heading,
                        "heading missing; near miss found: " + "; ".join(repr(text) for text in near)
                        + ". The text must match the guide character for character",
                    )
                )
            else:
                findings.append(Finding("FAIL", heading, "heading missing"))

    for number, line, fenced in lines:
        if fenced:
            continue
        if not allow_checked and CHECKED_ITEM.match(line):
            findings.append(
                Finding("FAIL", "checklist", f"line {number} is already checked; items stay unchecked at creation")
            )
        brace = TEMPLATE_BRACE.search(line)
        if brace:
            findings.append(
                Finding("FAIL", "template", f"line {number} still contains the template brace {brace.group(0)}")
            )

    return findings


def read_headings_file(path: Path) -> List[str]:
    values: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        values.append(line)
    return values


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a drafted approval-ticket body against required headings"
    )
    parser.add_argument("body", type=Path, help="Markdown file holding the ticket body")
    parser.add_argument(
        "--heading",
        action="append",
        default=[],
        help="A required heading, copied exactly from the guide; repeatable",
    )
    parser.add_argument(
        "--headings-file",
        type=Path,
        help="File with one required heading per line; blank lines and # comments ignored",
    )
    parser.add_argument(
        "--allow-checked",
        action="store_true",
        help="Do not fail on checked checklist items",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of lines")
    args = parser.parse_args(argv)

    required = list(args.heading)
    if args.headings_file:
        try:
            required.extend(read_headings_file(args.headings_file))
        except OSError as error:
            print(f"ERROR: cannot read headings file: {error}", file=sys.stderr)
            return 2
    if not required:
        print(
            "ERROR: no required headings given; copy them from the guide with --heading or --headings-file",
            file=sys.stderr,
        )
        return 2

    try:
        body = args.body.read_text(encoding="utf-8")
    except OSError as error:
        print(f"ERROR: cannot read body: {error}", file=sys.stderr)
        return 2

    findings = check(body, required, allow_checked=args.allow_checked)
    failures = sum(1 for finding in findings if finding.level == "FAIL")
    if args.json:
        print(json.dumps({"findings": [asdict(f) for f in findings], "failures": failures}, indent=2, ensure_ascii=False))
    else:
        for finding in findings:
            print(f"{finding.level:4} {finding.subject}: {finding.message}")
        print(f"Summary: pass={len(findings) - failures} fail={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
