#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_root(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("root must use label=/path format")
    label, raw_path = spec.split("=", 1)
    return label, Path(raw_path).expanduser()


def inspect(label: str, root: Path) -> dict[str, object]:
    skills: list[dict[str, str]] = []
    if root.is_dir():
        for entry in sorted(root.iterdir()):
            skill_file = entry / "SKILL.md"
            if not skill_file.is_file():
                continue
            text = skill_file.read_text(encoding="utf-8", errors="replace")
            name = re.search(r"^name:\s*([^\n]+)", text, re.MULTILINE)
            description = re.search(r"^description:\s*([^\n]*)", text, re.MULTILINE)
            skills.append(
                {
                    "directory": entry.name,
                    "name": name.group(1).strip() if name else "",
                    "description_style": "block" if description and not description.group(1).strip() else "inline",
                    "path": str(skill_file),
                }
            )
    return {"label": label, "root": str(root), "count": len(skills), "skills": skills}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        action="append",
        type=parse_root,
        default=[],
        help="Skill root as label=/path; may be repeated",
    )
    args = parser.parse_args()
    roots = args.root or [
        ("claude", Path.home() / ".claude" / "skills"),
        ("codex", Path.home() / ".agents" / "skills"),
    ]
    print(json.dumps([inspect(label, root) for label, root in roots], indent=2))


if __name__ == "__main__":
    main()
