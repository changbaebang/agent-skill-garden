#!/usr/bin/env python3
"""Pull change links, tracker keys, and thread coordinates out of request text.

A deployment request scatters its facts: the chat thread names a tracker key
and maybe a pull request, the tracker item carries the change as a link card
whose URL is invisible in the rendered view, and a reply says only "#482".
This module scans raw text (a thread export, an item's JSON, a pasted
message) and returns every distinct reference it finds, so the search order
in the skill can be applied to all three sources with the same tool.

Change links are recognised on any host by the path segment before the
number: ``pull``, ``pulls``, ``merge_requests``, or ``pull-requests``. Bare
``#N`` mentions are resolved only when ``--default-repo`` names the
repository they belong to. Tracker keys are matched as whole tokens so a
digit inside the project prefix does not truncate the key.

A chat permalink of the ``archives/<channel>/p<digits>`` form is converted to
the channel identifier and the message timestamp the host's thread API
expects; when the link carries a ``thread_ts`` query parameter, that parent
timestamp is returned so the whole thread is read, not one reply.

No network access and no organization values.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import parse_qs, urlparse

CHANGE_URL = re.compile(
    r"https?://(?P<host>[^/\s\"'<>]+)/(?P<path>[^\s\"'<>]+?)/(?:-/)?"
    r"(?:pull|pulls|merge_requests|pull-requests)/(?P<number>\d+)"
)
BARE_REF = re.compile(r"(?<![\w/#])(?:PR\s*|pull request\s*)?#(?P<number>\d+)\b", re.IGNORECASE)
TRACKER_KEY = re.compile(r"\b([A-Z][A-Z0-9]*-[0-9]+)\b")
PERMALINK = re.compile(r"/archives/(?P<channel>[A-Za-z0-9]+)/p(?P<digits>\d{7,})")


def _unescape(text: str) -> str:
    """JSON exports from some APIs escape every slash."""
    return text.replace("\\/", "/")


def extract_changes(text: str, default_repo: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return distinct change references in order of first appearance.

    Each entry has ``url``, ``host``, ``repository`` and ``number``. A bare
    ``#N`` mention yields ``url`` and ``host`` of ``None`` with ``repository``
    set to ``default_repo``; without a default repository bare mentions are
    ignored, because a number alone does not identify a change.
    """
    text = _unescape(text or "")
    found: List[Dict[str, Any]] = []
    seen = set()
    for match in CHANGE_URL.finditer(text):
        host = match.group("host").lower()
        repository = match.group("path")
        number = int(match.group("number"))
        key = (host, repository.lower(), number)
        if key in seen:
            continue
        seen.add(key)
        found.append({"url": match.group(0), "host": host, "repository": repository, "number": number})
    if default_repo:
        stripped = CHANGE_URL.sub(" ", text)
        for match in BARE_REF.finditer(stripped):
            number = int(match.group("number"))
            key = (None, default_repo.lower(), number)
            if key in seen or any(item["number"] == number and item["repository"].lower() == default_repo.lower() for item in found):
                continue
            seen.add(key)
            found.append({"url": None, "host": None, "repository": default_repo, "number": number})
    return found


def extract_keys(text: str) -> List[str]:
    """Return every distinct tracker key as a whole token, first appearance first."""
    keys: List[str] = []
    for match in TRACKER_KEY.finditer(_unescape(text or "")):
        key = match.group(1)
        if key not in keys:
            keys.append(key)
    return keys


def parse_permalink(url: str) -> Dict[str, Any]:
    """Channel and timestamps from an ``archives/<channel>/p<digits>`` permalink.

    ``message_ts`` is the linked message. ``thread_ts`` is the parent to read
    the whole thread from: the ``thread_ts`` query parameter when present,
    otherwise the message itself, which is then the root.
    """
    trimmed = (url or "").strip()
    match = PERMALINK.search(trimmed)
    if not match:
        raise ValueError(f"not a recognised thread permalink: {url!r}")
    digits = match.group("digits")
    message_ts = f"{digits[:-6]}.{digits[-6:]}"
    query = parse_qs(urlparse(trimmed).query)
    parent = query.get("thread_ts", [message_ts])[0]
    return {
        "channel": match.group("channel"),
        "message_ts": message_ts,
        "thread_ts": parent,
        "is_reply": parent != message_ts,
        "permalink": trimmed,
    }


def _read_text(source: Optional[str]) -> str:
    if not source or source == "-":
        return sys.stdin.read()
    with open(source, encoding="utf-8") as handle:
        return handle.read()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    changes = commands.add_parser("changes", help="list change links and resolved bare mentions as JSON")
    changes.add_argument("source", nargs="?", help="text or JSON file; - or omitted reads stdin")
    changes.add_argument("--default-repo", metavar="OWNER/REPO", help="repository that bare #N mentions belong to")

    keys = commands.add_parser("keys", help="list tracker keys, one per line")
    keys.add_argument("source", nargs="?", help="text or JSON file; - or omitted reads stdin")

    permalink = commands.add_parser("permalink", help="channel and timestamps from a thread permalink as JSON")
    permalink.add_argument("url")

    args = parser.parse_args(argv)
    try:
        if args.command == "changes":
            print(json.dumps(extract_changes(_read_text(args.source), args.default_repo), indent=2))
            return 0
        if args.command == "keys":
            for key in extract_keys(_read_text(args.source)):
                print(key)
            return 0
        print(json.dumps(parse_permalink(args.url), indent=2))
        return 0
    except OSError as error:
        print(f"cannot read input: {error}", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
