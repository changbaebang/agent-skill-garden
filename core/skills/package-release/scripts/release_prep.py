#!/usr/bin/env python3
"""Deterministic helpers for preparing a package release.

Three subcommands, all of them text operations with no network and no git:

  suggest    read the Unreleased section of a Keep-a-Changelog file and propose
             the bump level from what it contains; the decision stays with the
             person running the release
  changelog  turn the ``## [Unreleased]`` header into ``## [X.Y.Z] - DATE`` and
             retarget its compare link; dry-run unless --write is given
  scan       list every line that still carries the old version literal,
             skipping lock files, the changelog, and dependency directories

The old version is read from a manifest (package.json, pyproject.toml or
Cargo.toml) when --old is not given. Nothing here assumes a registry, a package
manager, a repository host, or an organization.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

UNRELEASED_HEADER = re.compile(r"^##\s*\[Unreleased\]\s*$", re.IGNORECASE)
VERSION_HEADER = re.compile(r"^##\s*\[(?P<version>[^\]]+)\](?:\s*-\s*(?P<date>\S+))?\s*$")
SUBSECTION = re.compile(r"^###\s+(?P<name>[A-Za-z]+)\s*$")
UNRELEASED_LINK = re.compile(
    r"^\[Unreleased\]:\s*(?P<url>\S+?)(?P<old>v?[0-9][^.]*\.[^.]*\.[^.]*?)\.\.\.HEAD\s*$",
    re.IGNORECASE,
)
SEMVER = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<rest>[-+].*)?$")
BREAKING_MARKER = re.compile(r"\bbreaking\b", re.IGNORECASE)
FUTURE_TENSE = re.compile(r"\b(next release|upcoming release|will be released)\b", re.IGNORECASE)

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "target",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    ".turbo",
    ".next",
}
SKIP_FILES = {
    "CHANGELOG.md",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "Cargo.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
}
MANIFESTS = ("package.json", "pyproject.toml", "Cargo.toml")

# Keep-a-Changelog subsection names, grouped by the bump they imply.
FEATURE_SECTIONS = {"added", "changed", "deprecated"}
FIX_SECTIONS = {"fixed", "security"}
REMOVAL_SECTIONS = {"removed"}


class ReleaseError(Exception):
    """A refusal the caller should see as a message, not a traceback."""


# --- manifest -----------------------------------------------------------------


def read_manifest_version(root: Path) -> Tuple[str, str]:
    """Return (manifest path, version) for the first recognised manifest."""
    for name in MANIFESTS:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        version: Optional[str] = None
        if name == "package.json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as error:
                raise ReleaseError(f"{path}: not valid JSON ({error})")
            value = data.get("version") if isinstance(data, dict) else None
            version = value if isinstance(value, str) else None
        elif name == "pyproject.toml":
            version = _toml_version(text, "project") or _toml_version(text, "tool.poetry")
        elif name == "Cargo.toml":
            version = _toml_version(text, "package")
        if version:
            return str(path), version
        raise ReleaseError(f"{path}: no version field found")
    raise ReleaseError(f"no manifest found in {root} (looked for {', '.join(MANIFESTS)})")


def _toml_version(text: str, table: str) -> Optional[str]:
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_table = line.strip("[]").strip() == table
            continue
        if in_table:
            match = re.match(r'version\s*=\s*"([^"]+)"', line)
            if match:
                return match.group(1)
    return None


# --- changelog parsing ---------------------------------------------------------


def split_unreleased(lines: List[str]) -> Tuple[int, int]:
    """Return (header index, end index) of the Unreleased section.

    ``end`` is the index of the next ``##`` header or the first link definition
    block, whichever comes first, so the section body is ``lines[start+1:end]``.
    """
    start = next((i for i, line in enumerate(lines) if UNRELEASED_HEADER.match(line)), -1)
    if start < 0:
        raise ReleaseError("no '## [Unreleased]' header found")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or re.match(r"^\[[^\]]+\]:\s*\S+", lines[i]):
            end = i
            break
    return start, end


def section_counts(body: Iterable[str]) -> Tuple[dict, List[str], bool]:
    """Count bullet items per subsection; return (counts, preamble, breaking)."""
    counts: dict = {}
    preamble: List[str] = []
    current: Optional[str] = None
    breaking = False
    for line in body:
        sub = SUBSECTION.match(line)
        if sub:
            current = sub.group("name").lower()
            counts.setdefault(current, 0)
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if BREAKING_MARKER.search(stripped):
            breaking = True
        if current is None:
            preamble.append(stripped)
        elif stripped.startswith(("-", "*", "+")):
            counts[current] += 1
    return counts, preamble, breaking


def has_items(counts: dict, preamble: List[str]) -> bool:
    return any(counts.values()) or bool(preamble)


# --- suggest ------------------------------------------------------------------


def parse_semver(text: str) -> Tuple[int, int, int]:
    match = SEMVER.match(text.strip().lstrip("v"))
    if not match:
        raise ReleaseError(f"not a MAJOR.MINOR.PATCH version: {text!r}")
    return int(match.group("major")), int(match.group("minor")), int(match.group("patch"))


def suggest_bump(current: str, counts: dict, breaking: bool) -> Tuple[str, str, str]:
    """Return (level, proposed version, reason)."""
    major, minor, patch = parse_semver(current)
    removal = any(counts.get(name, 0) for name in REMOVAL_SECTIONS)
    feature = any(counts.get(name, 0) for name in FEATURE_SECTIONS)
    fix = any(counts.get(name, 0) for name in FIX_SECTIONS)

    if breaking or removal:
        why = "a breaking change or a removal is listed"
        if major == 0:
            return "minor", f"0.{minor + 1}.0", why + "; on 0.x a minor carries breaking changes"
        return "major", f"{major + 1}.0.0", why
    if feature:
        return "minor", f"{major}.{minor + 1}.0", "additions or changes without a breaking change"
    if fix:
        return "patch", f"{major}.{minor}.{patch + 1}", "fixes only"
    return "patch", f"{major}.{minor}.{patch + 1}", "items without a recognised subsection; confirm by reading them"


def cmd_suggest(args: argparse.Namespace) -> int:
    changelog = Path(args.changelog)
    lines = changelog.read_text(encoding="utf-8").splitlines()
    start, end = split_unreleased(lines)
    counts, preamble, breaking = section_counts(lines[start + 1 : end])
    if not has_items(counts, preamble):
        print("ERROR: the Unreleased section is empty; nothing to release", file=sys.stderr)
        return 1
    current = args.current
    if not current:
        _, current = read_manifest_version(Path(args.root))
    level, proposed, reason = suggest_bump(current, counts, breaking)
    print(f"current : {current}")
    print(f"proposed: {proposed} ({level}) because {reason}")
    for name, count in sorted(counts.items()):
        print(f"  {name:<10} {count}")
    if preamble:
        print(f"  preamble   {len(preamble)} line(s) outside any subsection")
    if parse_semver(current)[0] == 0:
        print(
            "note    : on 0.x, '^' ranges pin to the minor, so this proposal is about the\n"
            "          contract, not the number; 1.0 is a decision to freeze the documented surface"
        )
    print("decision: yours; this is evidence from the changelog, not an instruction")
    return 0


# --- changelog ----------------------------------------------------------------


def promote_unreleased(text: str, version: str, release_date: str) -> Tuple[str, List[str]]:
    """Return (new text, notes). Raises ReleaseError on every refusal."""
    parse_semver(version)
    date.fromisoformat(release_date)
    lines = text.splitlines()
    start, end = split_unreleased(lines)
    for i, line in enumerate(lines):
        match = VERSION_HEADER.match(line)
        if match and i != start and match.group("version").lstrip("v") == version.lstrip("v"):
            raise ReleaseError(f"a header for {version} already exists at line {i + 1}")
    counts, preamble, _ = section_counts(lines[start + 1 : end])
    if not has_items(counts, preamble):
        raise ReleaseError("the Unreleased section is empty; fill it before promoting the header")

    notes: List[str] = []
    for line in preamble:
        if FUTURE_TENSE.search(line):
            notes.append(f"preamble reads as future tense; rewrite in the present: {line!r}")

    lines[start] = f"## [{version}] - {release_date}"
    for i, line in enumerate(lines):
        link = UNRELEASED_LINK.match(line)
        if link:
            prefix = "v" if link.group("old").startswith("v") else ""
            lines[i] = f"[{version}]: {link.group('url')}{link.group('old')}...{prefix}{version}"
            notes.append(f"compare link retargeted on line {i + 1}")
            break
    else:
        notes.append("no '[Unreleased]: ...compare/...HEAD' link found; add a version link by hand if the file uses them")

    trailing = "\n" if text.endswith("\n") else ""
    return "\n".join(lines) + trailing, notes


def cmd_changelog(args: argparse.Namespace) -> int:
    changelog = Path(args.changelog)
    original = changelog.read_text(encoding="utf-8")
    release_date = args.date or date.today().isoformat()
    updated, notes = promote_unreleased(original, args.version, release_date)
    before = original.splitlines()
    after = updated.splitlines()
    for i, (old, new) in enumerate(zip(before, after)):
        if old != new:
            print(f"- {i + 1}: {old}")
            print(f"+ {i + 1}: {new}")
    for note in notes:
        print(f"note: {note}")
    if args.write:
        changelog.write_text(updated, encoding="utf-8")
        print(f"written: {changelog}")
    else:
        print("dry run: pass --write to apply")
    return 0


# --- scan ---------------------------------------------------------------------


def literal_pattern(version: str) -> re.Pattern:
    # Whole-token match: 0.4.0 must not match 10.4.0, 0.4.01 or 0.4.0.1.
    return re.compile(r"(?<![0-9.])" + re.escape(version) + r"(?![0-9.])")


def iter_files(root: Path, extra_skips: Iterable[str]) -> Iterable[Path]:
    skips = {Path(p).name for p in extra_skips}
    for path in sorted(root.rglob("*")):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts[:-1]):
            continue
        if not path.is_file() or path.name in SKIP_FILES or path.name in skips:
            continue
        yield path


def scan_literals(root: Path, version: str, extra_skips: Iterable[str] = ()) -> List[Tuple[Path, int, str]]:
    pattern = literal_pattern(version)
    hits: List[Tuple[Path, int, str]] = []
    for path in iter_files(root, extra_skips):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append((path.relative_to(root), number, line.strip()))
    return hits


def cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root)
    old = args.old
    if not old:
        manifest, old = read_manifest_version(root)
        print(f"old version {old} read from {manifest}")
    hits = scan_literals(root, old, args.exclude)
    for path, number, line in hits:
        print(f"{path}:{number}: {line}")
    print(f"{len(hits)} line(s) carry {old}; lock files, the changelog and dependency directories were skipped")
    return 0


# --- cli ----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    suggest = sub.add_parser("suggest", help="propose a bump level from the Unreleased section")
    suggest.add_argument("--changelog", default="CHANGELOG.md")
    suggest.add_argument("--current", help="current version; read from the manifest when omitted")
    suggest.add_argument("--root", default=".", help="directory holding the manifest")
    suggest.set_defaults(func=cmd_suggest)

    changelog = sub.add_parser("changelog", help="promote the Unreleased header to a version header")
    changelog.add_argument("--changelog", default="CHANGELOG.md")
    changelog.add_argument("--version", required=True, help="the version being released")
    changelog.add_argument("--date", help="release date as YYYY-MM-DD; today when omitted")
    changelog.add_argument("--write", action="store_true", help="apply the change; dry run otherwise")
    changelog.set_defaults(func=cmd_changelog)

    scan = sub.add_parser("scan", help="list lines that still carry the old version literal")
    scan.add_argument("--root", default=".")
    scan.add_argument("--old", help="old version; read from the manifest when omitted")
    scan.add_argument("--exclude", action="append", default=[], help="extra file name to skip; repeatable")
    scan.set_defaults(func=cmd_scan)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ReleaseError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
