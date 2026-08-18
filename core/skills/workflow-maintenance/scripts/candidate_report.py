#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_patterns() -> list[str]:
    repo_root = Path(__file__).resolve().parents[4]
    pattern_file = repo_root / "config" / "forbidden-patterns.txt"
    return [
        line.strip()
        for line in pattern_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only promotion candidate report")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--canonical", type=Path)
    args = parser.parse_args()
    candidate = args.candidate / "SKILL.md" if args.candidate.is_dir() else args.candidate
    text = candidate.read_text(encoding="utf-8", errors="replace")
    import re

    findings = {
        f"pattern_{index + 1}": len(re.findall(pattern, text))
        for index, pattern in enumerate(load_patterns())
    }
    report: dict[str, object] = {
        "candidate": str(candidate),
        "lines": len(text.splitlines()),
        "risk_matches": findings,
    }
    if args.canonical:
        canonical = args.canonical / "SKILL.md" if args.canonical.is_dir() else args.canonical
        canonical_text = canonical.read_text(encoding="utf-8", errors="replace")
        report["canonical"] = str(canonical)
        report["same_content"] = text == canonical_text
        report["line_delta"] = len(text.splitlines()) - len(canonical_text.splitlines())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
