#!/usr/bin/env python3
"""Classify a test runner log as pass, assertion-failure, suite-crash, or unknown.

Reads one or more log files (or stdin), sums every summary block it finds,
and applies one rule: failed suites with zero failed tests is a worker crash,
not a code failure. Exit codes: 0 pass, 1 assertion-failure, 2 suite-crash,
3 unknown (no summary found).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

SUITE_LABEL = re.compile(r"(?:^|[\s:])(?:Test Suites|Test Files)\s*:?\s+(?P<rest>.+)$")
TEST_LABEL = re.compile(r"(?:^|[\s:])Tests\s*:?\s+(?P<rest>.+)$")
COUNT = re.compile(r"(\d+)\s+(failed|passed)\b")
TOTAL = re.compile(r"(\d+)\s+total\b|\((\d+)\)")

CRASH_SIGNALS = (
    "SIGSEGV",
    "SIGABRT",
    "SIGKILL",
    "Segmentation fault",
    "worker process has quit unexpectedly",
    "worker process has failed to exit gracefully",
    "Call retries were exceeded",
    "heap out of memory",
    "FATAL ERROR: Reached heap limit",
)

VERDICT_EXIT = {"pass": 0, "assertion-failure": 1, "suite-crash": 2, "unknown": 3}

NEXT_ACTION = {
    "pass": "No failed tests or suites.",
    "assertion-failure": "Failed tests belong to the change; investigate them.",
    "suite-crash": "Failed suites with zero failed tests: rerun at lower concurrency before blaming the change.",
    "unknown": "No summary block found; read the log head for the abort reason.",
}


def parse_counts(rest: str) -> Dict[str, int]:
    counts: Dict[str, int] = {"failed": 0, "passed": 0, "total": 0}
    for number, label in COUNT.findall(rest):
        counts[label] += int(number)
    total_match = TOTAL.search(rest)
    if total_match:
        counts["total"] = int(total_match.group(1) or total_match.group(2))
    return counts


def classify(text: str) -> Dict[str, object]:
    suites = {"failed": 0, "passed": 0, "total": 0}
    tests = {"failed": 0, "passed": 0, "total": 0}
    blocks = 0
    for line in text.splitlines():
        suite_match = SUITE_LABEL.search(line)
        if suite_match:
            blocks += 1
            for key, value in parse_counts(suite_match.group("rest")).items():
                suites[key] += value
            continue
        test_match = TEST_LABEL.search(line)
        if test_match:
            for key, value in parse_counts(test_match.group("rest")).items():
                tests[key] += value

    signals: List[str] = sorted({signal for signal in CRASH_SIGNALS if signal in text})

    if blocks == 0 and tests["total"] == 0 and not signals:
        verdict = "unknown"
    elif tests["failed"] > 0:
        verdict = "assertion-failure"
    elif suites["failed"] > 0 or signals:
        verdict = "suite-crash"
    else:
        verdict = "pass"

    return {
        "verdict": verdict,
        "summary_blocks": blocks,
        "suites": suites,
        "tests": tests,
        "crash_signals": signals,
        "next_action": NEXT_ACTION[verdict],
    }


def read_input(paths: List[str]) -> str:
    if not paths:
        return sys.stdin.read()
    chunks = []
    for path in paths:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            chunks.append(handle.read())
    return "\n".join(chunks)


def render(result: Dict[str, object]) -> str:
    suites = result["suites"]
    tests = result["tests"]
    lines = [
        f"verdict: {result['verdict']}",
        f"summary blocks: {result['summary_blocks']}",
        f"suites: {suites['failed']} failed, {suites['passed']} passed, {suites['total']} total",
        f"tests: {tests['failed']} failed, {tests['passed']} passed, {tests['total']} total",
    ]
    if result["crash_signals"]:
        lines.append("crash signals: " + ", ".join(result["crash_signals"]))
    lines.append(f"next: {result['next_action']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", help="log files; stdin when omitted")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    result = classify(read_input(args.paths))
    print(json.dumps(result, indent=2) if args.json else render(result))
    return VERDICT_EXIT[str(result["verdict"])]


if __name__ == "__main__":
    raise SystemExit(main())
