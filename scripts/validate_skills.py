#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skills_root = root / "core" / "skills"
    errors = 0
    skills = sorted(path for path in skills_root.iterdir() if path.is_dir())
    if not skills:
        fail("no skills found")
        return 1

    for skill in skills:
        entry = skill / "SKILL.md"
        if not entry.is_file():
            fail(f"{skill.name}: missing SKILL.md")
            errors += 1
            continue
        text = entry.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        if not match:
            fail(f"{skill.name}: invalid frontmatter")
            errors += 1
            continue
        frontmatter = match.group(1)
        name_match = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.MULTILINE)
        description_match = re.search(
            r"^description:\s*(?:>|>-|\|)?\s*\n(?P<body>(?:[ \t]+.*\n?)*)",
            frontmatter,
            re.MULTILINE,
        )
        parsed_name = name_match.group(1).strip().strip('"\'') if name_match else ""
        if parsed_name != skill.name:
            fail(f"{skill.name}: name must match directory")
            errors += 1
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", parsed_name) or len(parsed_name) > 64:
            fail(f"{skill.name}: name must be hyphen-case and at most 64 characters")
            errors += 1
        if not description_match:
            fail(f"{skill.name}: missing description")
            errors += 1
        else:
            description = " ".join(
                line.strip() for line in description_match.group("body").splitlines()
            ).strip()
            if not description or len(description) > 1024 or "<" in description or ">" in description:
                fail(f"{skill.name}: description must be 1-1024 characters without angle brackets")
                errors += 1
        top_level_keys = re.findall(r"^([a-z][a-z0-9-]*):", frontmatter, re.MULTILINE)
        unexpected = sorted(set(top_level_keys) - {"name", "description"})
        if unexpected:
            fail(f"{skill.name}: non-portable frontmatter keys: {', '.join(unexpected)}")
            errors += 1
        if "TODO" in text:
            fail(f"{skill.name}: unresolved TODO")
            errors += 1
        if len(text.splitlines()) > 500:
            fail(f"{skill.name}: SKILL.md exceeds 500 lines")
            errors += 1

    if errors:
        return 1
    print(f"Validated {len(skills)} portable skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
