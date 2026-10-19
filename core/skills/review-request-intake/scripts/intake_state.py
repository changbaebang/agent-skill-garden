#!/usr/bin/env python3
"""Deterministic helpers for review request intake."""
import json
import re
import sys
from urllib.parse import urlparse, parse_qs


def parse_permalink(url, pattern=None):
    """Default format is Slack-style archives/<channel>/p<ts>[?thread_ts=].

    For another chat tool pass a regex with named groups `channel` and
    `message`; the raw ids are returned unchanged.
    """
    url = url.strip()
    if pattern:
        m = re.search(pattern, url)
        if not m or not {"channel", "message"} <= set(m.groupdict()):
            raise ValueError("not a message permalink")
        return {"channel": m.group("channel"), "message_ts": m.group("message"),
                "thread_ts": parse_qs(urlparse(url).query).get("thread_ts", [m.group("message")])[0]}
    m = re.search(r"archives/([A-Za-z0-9]+)/p(\d{7,})", url)
    if not m:
        raise ValueError("not a message permalink")
    raw = m.group(2)
    ts = raw[:-6] + "." + raw[-6:]
    q = parse_qs(urlparse(url).query)
    parent = q.get("thread_ts", [ts])[0]
    return {"channel": m.group(1), "message_ts": ts, "thread_ts": parent}


def decide(f):
    if f.get("state", "OPEN").upper() in ("MERGED", "CLOSED"):
        return "withdraw"
    if f.get("docs_only"):
        return "skip-docs"
    head = f.get("head")
    last = f.get("last_reviewed_head")
    prior = f.get("my_last_review", "none")
    if head and f.get("completed_head") == head and not f.get("new_human_evidence_same_head"):
        return "skip"
    if prior == "none" and not last:
        return "review"
    open_prior = prior in ("commented", "changes_requested")
    if last and head and head != last:
        return "re-review"
    if open_prior and f.get("author_replied_after_review"):
        return "re-review"
    if f.get("new_human_evidence_same_head"):
        return "audit"
    return "skip"


def main(argv):
    if len(argv) >= 3 and argv[1] == "permalink":
        try:
            pat = argv[3] if len(argv) >= 4 else None
            print(json.dumps(parse_permalink(argv[2], pat)))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    if len(argv) >= 2 and argv[1] == "decide":
        print(decide(json.load(sys.stdin)))
        return 0
    print("usage: intake_state.py permalink <url> [regex] | decide < facts.json", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
