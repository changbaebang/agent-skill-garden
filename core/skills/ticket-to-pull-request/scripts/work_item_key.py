#!/usr/bin/env python3
"""Extract tracker work-item keys without truncating them, and build branch names.

A key such as ``AB1CD-42`` carries a digit inside its project prefix. The common
pattern ``[A-Z]+-[0-9]+`` searched without an anchor starts matching after that
digit and returns ``CD-42``, which links to the wrong item or to nothing. This
module matches the whole token and prefers the longest key when several appear.

No network access and no organization values: pass ``--prefer`` when one
project prefix should win ties.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from typing import Iterable, List, Optional, Sequence

KEY_PATTERN = re.compile(r"\b([A-Z][A-Z0-9]*-[0-9]+)\b")
DEFAULT_BRANCH_PREFIX = "feature"
DEFAULT_MAX_BRANCH_LENGTH = 72


def extract_keys(text: str) -> List[str]:
    """Return every distinct key in ``text`` in order of first appearance."""
    seen: List[str] = []
    for match in KEY_PATTERN.finditer(text):
        key = match.group(1)
        if key not in seen:
            seen.append(key)
    return seen


def primary_key(text: str, prefer: Optional[Iterable[str]] = None) -> Optional[str]:
    """Pick one key: a preferred prefix wins, then the longest, then the first.

    ``prefer`` lists project prefixes (the part before the hyphen) in priority
    order. Prefix comparison is exact, so ``AB`` does not claim ``ABC-1``.
    """
    keys = extract_keys(text)
    if not keys:
        return None
    for prefix in prefer or ():
        wanted = prefix.upper().rstrip("-")
        for key in keys:
            if key.split("-", 1)[0] == wanted:
                return key
    longest = max(len(key) for key in keys)
    for key in keys:
        if len(key) == longest:
            return key
    return keys[0]


def slugify(title: str, max_length: int = 40) -> str:
    """Lower-case ASCII slug; characters outside ASCII letters and digits drop out."""
    normalized = unicodedata.normalize("NFKD", title)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def branch_name(
    key: str,
    title: str = "",
    prefix: str = DEFAULT_BRANCH_PREFIX,
    max_length: int = DEFAULT_MAX_BRANCH_LENGTH,
) -> str:
    """Build ``<prefix>/<KEY>-<slug>``; without a usable slug, ``<prefix>/<KEY>``."""
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError(f"not a tracker key: {key!r}")
    head = f"{prefix.strip('/')}/{key}" if prefix else key
    budget = max_length - len(head) - 1
    slug = slugify(title, max_length=max(budget, 0)) if budget > 0 else ""
    return f"{head}-{slug}" if slug else head


def _read_text(values: Sequence[str]) -> str:
    if not values or values == ["-"]:
        return sys.stdin.read()
    return " ".join(values)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="print every key, one per line")
    extract.add_argument("text", nargs="*", help="text to scan, or - for stdin")

    primary = subparsers.add_parser("primary", help="print the single best key")
    primary.add_argument("text", nargs="*", help="text to scan, or - for stdin")
    primary.add_argument(
        "--prefer",
        action="append",
        default=[],
        metavar="PREFIX",
        help="project prefix that wins ties; repeatable, highest priority first",
    )

    branch = subparsers.add_parser("branch", help="build a branch name from a key")
    branch.add_argument("key")
    branch.add_argument("--title", default="", help="item title to slugify")
    branch.add_argument("--prefix", default=DEFAULT_BRANCH_PREFIX)
    branch.add_argument("--max-length", type=int, default=DEFAULT_MAX_BRANCH_LENGTH)

    args = parser.parse_args(argv)

    if args.command == "extract":
        for key in extract_keys(_read_text(args.text)):
            print(key)
        return 0
    if args.command == "primary":
        key = primary_key(_read_text(args.text), args.prefer)
        if key is None:
            print("no tracker key found", file=sys.stderr)
            return 1
        print(key)
        return 0
    try:
        print(branch_name(args.key, args.title, args.prefix, args.max_length))
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
