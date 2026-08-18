#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_skill(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"invalid frontmatter: {path}")
    frontmatter = match.group(1)
    name_match = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.MULTILINE)
    description_match = re.search(
        r"^description:\s*(?:>|>-|\|)?\s*\n(?P<body>(?:[ \t]+.*\n?)*)",
        frontmatter,
        re.MULTILINE,
    )
    if not name_match or not description_match:
        raise ValueError(f"missing name or block description: {path}")
    name = name_match.group(1).strip().strip("\"'")
    description = " ".join(
        line.strip() for line in description_match.group("body").splitlines()
    ).strip()
    body = text[match.end() :].strip()
    return {
        "name": name,
        "description_characters": len(description),
        "body_characters": len(body),
        "body_lines": len(body.splitlines()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report deterministic context-size proxies for Agent Skills"
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail when configured budgets are exceeded"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    skills = [
        parse_skill(path)
        for path in sorted((root / "core" / "skills").glob("*/SKILL.md"))
    ]
    budgets = json.loads(
        (root / "config" / "context-budget.json").read_text(encoding="utf-8")
    )
    catalog_characters = sum(
        len(str(skill["name"])) + int(skill["description_characters"])
        for skill in skills
    )
    report = {
        "note": "Character counts are deterministic proxies, not model token counts.",
        "skill_count": len(skills),
        "catalog_characters": catalog_characters,
        "budgets": budgets,
        "skills": skills,
    }

    failures: list[str] = []
    if catalog_characters > budgets["max_catalog_characters"]:
        failures.append(
            f"catalog characters {catalog_characters} exceed "
            f"{budgets['max_catalog_characters']}"
        )
    for skill in skills:
        if skill["description_characters"] > budgets["max_single_description_characters"]:
            failures.append(f"{skill['name']}: description budget exceeded")
        if skill["body_characters"] > budgets["max_single_skill_body_characters"]:
            failures.append(f"{skill['name']}: body budget exceeded")

    if args.json:
        report["failures"] = failures
        print(json.dumps(report, indent=2))
    else:
        print("# Context footprint")
        print()
        print("Character counts are deterministic proxies, not model token counts.")
        print(f"Catalog: {catalog_characters}/{budgets['max_catalog_characters']} characters")
        print()
        print("| Skill | Description chars | Body chars | Body lines |")
        print("| --- | ---: | ---: | ---: |")
        for skill in skills:
            print(
                f"| {skill['name']} | {skill['description_characters']} | "
                f"{skill['body_characters']} | {skill['body_lines']} |"
            )

    if args.check and failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
