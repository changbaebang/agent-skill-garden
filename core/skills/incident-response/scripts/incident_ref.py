#!/usr/bin/env python3
"""Normalize an incident reference into the parts the gather step looks up.

Accepted inputs:

- a tracker key such as ``OPS-17`` or a tracker URL that ends in one;
- an incident channel name such as ``#incident-17`` or ``incident-17``;
- a chat permalink of the shape ``.../archives/<channel-id>/p<digits>``.

The script performs no network access and knows no organization. The channel
naming convention and the tracker project come from the command line, so the
caller supplies them from the environment profile.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Optional

TRACKER_KEY = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]*)-(\d+)(?![A-Za-z0-9])")
PERMALINK = re.compile(r"/archives/([A-Za-z0-9]+)/p(\d{7,})")


def _channel_pattern(prefix: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![A-Za-z0-9])#?" + re.escape(prefix) + r"(\d+)(?![A-Za-z0-9])", re.IGNORECASE)


def _result(**fields: object) -> dict:
    base: dict = {
        "input": None,
        "incident_number": None,
        "tracker_key": None,
        "channel_name": None,
        "channel_id": None,
        "message_ts": None,
        "source": None,
    }
    base.update(fields)
    return base


def parse_reference(text: str, project: Optional[str] = None, channel_prefix: str = "incident-") -> dict:
    """Return the canonical parts of one incident reference.

    Raises ``ValueError`` when the text matches none of the accepted shapes.
    """
    trimmed = text.strip()
    if not trimmed:
        raise ValueError("empty reference")

    channel_name_for = (lambda number: f"{channel_prefix}{number}") if channel_prefix else (lambda number: None)

    # A leading hash can only be a channel, even when the prefix looks like a project key.
    if trimmed.startswith("#"):
        match = _channel_pattern(channel_prefix).fullmatch(trimmed) if channel_prefix else None
        if not match:
            raise ValueError(f"channel reference does not use the prefix {channel_prefix!r}: {trimmed}")
        number = match.group(1)
        return _result(
            input=trimmed,
            incident_number=number,
            tracker_key=f"{project}-{number}" if project else None,
            channel_name=channel_name_for(number),
            source="channel-name",
        )

    # An upper-case project key is a tracker key; a lower-case prefix is a channel.
    key = TRACKER_KEY.search(trimmed)
    if key:
        number = key.group(2)
        return _result(
            input=trimmed,
            incident_number=number,
            tracker_key=f"{key.group(1)}-{number}",
            channel_name=channel_name_for(number),
            source="tracker-key",
        )

    if channel_prefix:
        channel = _channel_pattern(channel_prefix).search(trimmed)
        if channel:
            number = channel.group(1)
            return _result(
                input=trimmed,
                incident_number=number,
                tracker_key=f"{project}-{number}" if project else None,
                channel_name=channel_name_for(number),
                source="channel-name",
            )

    permalink = PERMALINK.search(trimmed)
    if permalink:
        raw = permalink.group(2)
        return _result(
            input=trimmed,
            channel_id=permalink.group(1),
            message_ts=f"{raw[:-6]}.{raw[-6:]}",
            source="chat-permalink",
        )

    raise ValueError(
        "unrecognized reference; expected a tracker key, an incident channel name, or a chat permalink"
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize an incident reference into lookup parts")
    parser.add_argument("reference", help="tracker key, channel name, tracker URL, or chat permalink")
    parser.add_argument(
        "--project",
        help="tracker project key used when only a channel name is given (from the environment profile)",
    )
    parser.add_argument(
        "--channel-prefix",
        default="incident-",
        help="incident channel naming prefix; pass an empty string when channels are not numbered",
    )
    args = parser.parse_args(argv)
    try:
        result = parse_reference(args.reference, project=args.project, channel_prefix=args.channel_prefix)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
