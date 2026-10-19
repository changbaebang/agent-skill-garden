#!/usr/bin/env python3
"""Extract the references a chat work request carries, without looking anything up.

Input is a chat permalink, pasted thread text, or both. Output is JSON with:

- ``permalink``: channel id, message timestamp, and thread root when the text
  holds a link of the shape ``.../archives/<channel-id>/p<digits>``, optionally
  followed by a ``thread_ts`` query parameter;
- ``tracker_keys``: upper-case ``KEY-123`` tokens in order of first appearance;
- ``pull_requests``: links to pull or merge requests;
- ``links``: every other http(s) link, the permalink excluded;
- ``mentions``: ``@name`` and ``<@ID>`` tokens;
- ``signals.pull_request_only``: true when the text links a pull request and
  names neither a tracker item nor another document. That is the shape of a
  review request, which the workflow hands off instead of kicking off.

The script knows no organization: hosts, projects, and channels come from the
text itself. It performs no network access.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import List, Optional
from urllib.parse import parse_qs, urlsplit

URL = re.compile(r"https?://[^\s<>\"'\]]+")
PERMALINK_PATH = re.compile(r"/archives/([A-Za-z0-9]+)/p(\d{7,})")
PULL_REQUEST_PATH = re.compile(r"/(?:pull|pulls|merge_requests|pull-requests)/\d+(?![0-9])")
TRACKER_KEY = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]*)-(\d+)(?![A-Za-z0-9])")
MENTION_ID = re.compile(r"<@([A-Za-z0-9]+)>")
MENTION_NAME = re.compile(r"(?<![\w/.:<])@([A-Za-z0-9][\w.-]*)")
TRAILING_PUNCTUATION = ".,;:!?)>\"'"

# Upper-case tokens that look like tracker keys but never are.
NOT_TRACKER_PROJECTS = {"UTF", "SHA", "ISO", "RFC"}


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _clean_url(raw: str) -> str:
    url = raw
    while url and url[-1] in TRAILING_PUNCTUATION:
        # A closing parenthesis is part of the link only when the link opened one.
        if url[-1] == ")" and url.count("(") >= url.count(")"):
            break
        url = url[:-1]
    return url


def _timestamp(digits: str) -> str:
    return f"{digits[:-6]}.{digits[-6:]}"


def parse_permalink(url: str) -> Optional[dict]:
    """Return the chat permalink parts, or ``None`` when the URL is not one."""
    parts = urlsplit(url)
    match = PERMALINK_PATH.search(parts.path)
    if not match:
        return None
    query = parse_qs(parts.query)
    thread_root = query.get("thread_ts", [None])[0]
    return {
        "url": url,
        "channel_id": match.group(1),
        "message_ts": _timestamp(match.group(2)),
        "thread_root_ts": thread_root,
    }


def is_pull_request(url: str) -> bool:
    return PULL_REQUEST_PATH.search(urlsplit(url).path) is not None


def tracker_keys(text: str) -> List[str]:
    keys = []
    for match in TRACKER_KEY.finditer(text):
        project = match.group(1)
        if project in NOT_TRACKER_PROJECTS:
            continue
        keys.append(f"{project}-{match.group(2)}")
    return _dedupe(keys)


def mentions(text: str) -> List[str]:
    found = [f"<@{identifier}>" for identifier in MENTION_ID.findall(text)]
    found.extend(f"@{name.rstrip('.')}" for name in MENTION_NAME.findall(text))
    return _dedupe(found)


def extract(text: str) -> dict:
    """Return every reference found in ``text``. Raises ``ValueError`` on empty input."""
    if not text or not text.strip():
        raise ValueError("empty input")

    urls = _dedupe([_clean_url(raw) for raw in URL.findall(text)])
    permalink = None
    pull_requests = []
    links = []
    for url in urls:
        parsed = parse_permalink(url)
        if parsed and permalink is None:
            permalink = parsed
            continue
        if parsed:
            links.append(url)
            continue
        if is_pull_request(url):
            pull_requests.append(url)
        else:
            links.append(url)

    keys = tracker_keys(text)
    return {
        "permalink": permalink,
        "tracker_keys": keys,
        "pull_requests": pull_requests,
        "links": links,
        "mentions": mentions(text),
        "signals": {
            "pull_request_only": bool(pull_requests) and not keys and not links,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract chat permalink parts, tracker keys, links, and mentions from a work request"
    )
    parser.add_argument(
        "text",
        nargs="*",
        help="permalink or pasted text; read from standard input when omitted",
    )
    args = parser.parse_args(argv)
    text = "\n".join(args.text) if args.text else sys.stdin.read()
    try:
        result = extract(text)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
