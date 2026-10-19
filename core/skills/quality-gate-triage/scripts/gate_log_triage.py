#!/usr/bin/env python3
"""Deterministic helpers for the quality-gate triage workflow.

Subcommands:

  classify [--log FILE] [--patterns FILE]
      Read one gate step log (a file, or stdin) and print the verdict with the
      lines that prove it. Verdicts: passed, failed, no-verdict, conflicting,
      unknown. The first output line is ``verdict<TAB>VALUE``; every following
      line is ``kind<TAB>line-number<TAB>text`` for a line the verdict rests on.
  tally [--runs FILE] [--branch NAME]
      Read run rows (``run_id``, ``branch``, ``commit``, ``verdict``,
      tab-separated; ``commit`` may be omitted) and print how no-verdict runs
      are distributed across branches, plus commits that ran more than once.

No network access. Fetching logs and run lists belongs to the caller. The
default patterns describe how gate tools usually word a verdict or a timeout;
pass ``--patterns`` with a JSON object of ``passed``, ``failed``, ``incomplete``
and ``condition`` regular-expression lists to match a tool that words them
differently.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

PASSED = "passed"
FAILED = "failed"
NO_VERDICT = "no-verdict"
CONFLICTING = "conflicting"
UNKNOWN = "unknown"
INCOMPLETE = "incomplete"
CONDITION = "condition"

DEFAULT_PATTERNS: Dict[str, List[str]] = {
    PASSED: [
        r"quality\s*gate[^\n]*\b(passed|succeeded|success|ok)\b",
    ],
    FAILED: [
        r"quality\s*gate[^\n]*\b(failed|failure|error|red)\b",
    ],
    INCOMPLETE: [
        r"timeout\s+reached",
        r"timed\s+out",
        r"time\s*out\s+(waiting|exceeded|while|for)",
        r"\b(not|never)\s+(finished|completed)\b",
        r"still\s+(running|pending|in\s+progress)",
        r"analysis\s+(is\s+)?(pending|in\s+progress|unavailable)",
        r"no\s+(quality\s*gate\s+)?(status|verdict|result)\s+(was\s+)?(found|returned|available)",
    ],
    CONDITION: [
        r"\b(less|greater|lower|higher|more|fewer)\s+than\b",
        r"\bthreshold\b",
        r"\bnew\s+code\b[^\n]*%",
    ],
}

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


# --- classify --------------------------------------------------------------


def load_patterns(path: Optional[str]) -> Dict[str, List[re.Pattern]]:
    raw: Dict[str, List[str]] = {key: list(value) for key, value in DEFAULT_PATTERNS.items()}
    if path:
        override = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(override, dict):
            raise ValueError("patterns file must contain a JSON object")
        for key, value in override.items():
            if key not in raw:
                raise ValueError(f"unknown pattern group {key!r}")
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError(f"pattern group {key!r} must be a list of strings")
            raw[key] = list(value)
    return {key: [re.compile(item, re.IGNORECASE) for item in value] for key, value in raw.items()}


def _matches(line: str, patterns: Sequence[re.Pattern]) -> bool:
    return any(pattern.search(line) for pattern in patterns)


def classify_lines(
    lines: Iterable[str], patterns: Optional[Dict[str, List[re.Pattern]]] = None
) -> Tuple[str, List[Tuple[str, int, str]]]:
    """Return the verdict and the evidence lines it rests on.

    Per line, an incomplete signal wins over a failed signal, because a timed
    out step often also prints an error. Across the log: any incomplete line
    without a passed line means no verdict was ever produced; a failed line
    without a passed line is a real failure; a passed line alone is a pass;
    a passed line next to failed or incomplete lines is conflicting and must
    be read by a person.
    """
    compiled = patterns or load_patterns(None)
    evidence: List[Tuple[str, int, str]] = []
    seen = {PASSED: False, FAILED: False, INCOMPLETE: False}
    for number, raw in enumerate(lines, start=1):
        line = ANSI.sub("", raw.rstrip("\r\n"))
        if not line.strip():
            continue
        kind: Optional[str] = None
        if _matches(line, compiled[INCOMPLETE]):
            kind = INCOMPLETE
        elif _matches(line, compiled[PASSED]):
            kind = PASSED
        elif _matches(line, compiled[FAILED]):
            kind = FAILED
        elif _matches(line, compiled[CONDITION]):
            kind = CONDITION
        if kind is None:
            continue
        if kind in seen:
            seen[kind] = True
        evidence.append((kind, number, line.strip()))

    if seen[PASSED] and (seen[FAILED] or seen[INCOMPLETE]):
        verdict = CONFLICTING
    elif seen[INCOMPLETE]:
        verdict = NO_VERDICT
    elif seen[FAILED]:
        verdict = FAILED
    elif seen[PASSED]:
        verdict = PASSED
    else:
        verdict = UNKNOWN
    if verdict != FAILED:
        evidence = [item for item in evidence if item[0] != CONDITION]
    return verdict, evidence


def render_classification(verdict: str, evidence: Sequence[Tuple[str, int, str]]) -> str:
    out = [f"verdict\t{verdict}"]
    out.extend(f"{kind}\t{number}\t{text}" for kind, number, text in evidence)
    return "\n".join(out) + "\n"


# --- tally -----------------------------------------------------------------


def parse_runs(lines: Iterable[str]) -> List[Tuple[str, str, str, str]]:
    """Return (run_id, branch, commit, verdict) rows; commit may be empty."""
    rows: List[Tuple[str, str, str, str]] = []
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) == 3:
            run_id, branch, verdict = parts
            commit = ""
        elif len(parts) >= 4:
            run_id, branch, commit, verdict = parts[:4]
        else:
            raise ValueError(f"expected 3 or 4 tab-separated columns: {line!r}")
        rows.append((run_id, branch, commit, verdict))
    return rows


def tally_runs(rows: Sequence[Tuple[str, str, str, str]], current_branch: Optional[str] = None) -> "OrderedDict[str, object]":
    per_branch: "OrderedDict[str, List[int]]" = OrderedDict()
    commits: Dict[Tuple[str, str], int] = {}
    no_verdict_total = 0
    for _run_id, branch, commit, verdict in rows:
        counts = per_branch.setdefault(branch, [0, 0])
        counts[1] += 1
        if verdict == NO_VERDICT:
            counts[0] += 1
            no_verdict_total += 1
        if commit:
            commits[(branch, commit)] = commits.get((branch, commit), 0) + 1

    affected = [branch for branch, (missing, _total) in per_branch.items() if missing]
    if not affected:
        reading = "none"
    elif len(affected) >= 2:
        reading = "repo-wide"
    elif current_branch is not None and affected[0] == current_branch:
        reading = "branch-local"
    else:
        reading = "single-branch"

    result: "OrderedDict[str, object]" = OrderedDict()
    result["runs_total"] = len(rows)
    result["runs_no_verdict"] = no_verdict_total
    result["branches_total"] = len(per_branch)
    result["branches_no_verdict"] = len(affected)
    result["duplicate_commits"] = sum(1 for count in commits.values() if count > 1)
    result["reading"] = reading
    result["per_branch"] = OrderedDict(
        (branch, (missing, total)) for branch, (missing, total) in per_branch.items()
    )
    return result


def render_tally(result: "OrderedDict[str, object]") -> str:
    out: List[str] = []
    for key in ("runs_total", "runs_no_verdict", "branches_total", "branches_no_verdict", "duplicate_commits", "reading"):
        out.append(f"{key}\t{result[key]}")
    per_branch = result["per_branch"]
    assert isinstance(per_branch, dict)
    for branch, (missing, total) in per_branch.items():
        out.append(f"branch\t{branch}\t{missing}/{total}")
    return "\n".join(out) + "\n"


# --- command line ----------------------------------------------------------


def _read_lines(path: Optional[str]) -> List[str]:
    if path:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    return sys.stdin.read().splitlines()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    classify_parser = sub.add_parser("classify", help="classify one gate step log")
    classify_parser.add_argument("--log", help="log file; stdin when omitted")
    classify_parser.add_argument("--patterns", help="JSON file overriding pattern groups")

    tally_parser = sub.add_parser("tally", help="tally no-verdict runs by branch")
    tally_parser.add_argument("--runs", help="tab-separated run rows; stdin when omitted")
    tally_parser.add_argument("--branch", help="the branch under triage, to tell branch-local from single-branch")

    args = parser.parse_args(argv)
    try:
        if args.command == "classify":
            verdict, evidence = classify_lines(_read_lines(args.log), load_patterns(args.patterns))
            sys.stdout.write(render_classification(verdict, evidence))
            return 0
        if args.command == "tally":
            sys.stdout.write(render_tally(tally_runs(parse_runs(_read_lines(args.runs)), args.branch)))
            return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
