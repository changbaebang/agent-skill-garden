#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def write_new(path: Path, content: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def initialize_project(root: Path, example: Path) -> Path:
    directory = root / ".agent-garden"
    ignore = directory / ".gitignore"
    profile = directory / "profile.ini"
    if profile.exists() or profile.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing file: {profile}")

    directory.mkdir(parents=True, exist_ok=True)
    if ignore.exists():
        existing = ignore.read_text(encoding="utf-8").splitlines()
        missing = [entry for entry in ("profile.ini", "*.local.ini") if entry not in existing]
        if missing:
            with ignore.open("a", encoding="utf-8") as handle:
                if existing and existing[-1] != "":
                    handle.write("\n")
                handle.write("\n".join(missing) + "\n")
    else:
        write_new(ignore, "profile.ini\n*.local.ini\n")

    shutil.copyfile(example, profile)
    return profile


def initialize_user(home: Path, example: Path) -> Path:
    profile = home / ".agent-garden" / "profile.ini"
    if profile.exists() or profile.is_symlink():
        raise FileExistsError(f"refusing to overwrite existing file: {profile}")
    profile.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example, profile)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a protected local Agent Skill Garden profile"
    )
    parser.add_argument("--scope", choices=("project", "user"), required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()

    example = Path(__file__).resolve().parents[1] / "references" / "profile.example.ini"
    try:
        if args.scope == "project":
            profile = initialize_project(args.root.expanduser().resolve(), example)
        else:
            profile = initialize_user(args.home.expanduser().resolve(), example)
    except FileExistsError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: cannot initialize profile: {error}", file=sys.stderr)
        return 1

    print(f"Created protected profile: {profile}")
    if args.scope == "project":
        print(f"Ignore rule: {profile.parent / '.gitignore'}")
    else:
        print("User profile is outside the project; back it up privately if needed.")
    print("Edit the local values, remove unused integrations, then run profile_doctor.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
