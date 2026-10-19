#!/usr/bin/env python3
"""Summarize a HAR file by party, initiator, and raw-versus-transfer size.

The HAR fields that prove something are the initiator stack and the request
count; per-request duration is reported but never used for a verdict. Nothing
here touches the network: pass a saved HAR file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit

APP = "app"
THIRD_PARTY = "third-party"
EXTENSION = "extension"

EXTENSION_SCHEMES = (
    "chrome-extension",
    "moz-extension",
    "safari-web-extension",
    "ms-browser-extension",
)


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def is_first_party(host: str, first_party: Iterable[str]) -> bool:
    for root in first_party:
        root = root.lower().lstrip(".")
        if host == root or host.endswith("." + root):
            return True
    return False


def classify(url: str, first_party: Iterable[str]) -> str:
    scheme = urlsplit(url).scheme.lower()
    if scheme in EXTENSION_SCHEMES:
        return EXTENSION
    return APP if is_first_party(host_of(url), first_party) else THIRD_PARTY


def _size(value: object) -> int:
    """HAR writes -1 for unknown sizes; treat that as zero bytes."""
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    return max(number, 0)


def raw_size(entry: dict) -> int:
    content = entry.get("response", {}).get("content", {}) or {}
    return _size(content.get("size"))


def transfer_size(entry: dict) -> int:
    response = entry.get("response", {}) or {}
    transfer = _size(response.get("_transferSize"))
    if transfer:
        return transfer
    return _size(response.get("bodySize")) + _size(response.get("headersSize"))


def compression_ratio(raw: int, transfer: int) -> float | None:
    if raw <= 0 or transfer <= 0:
        return None
    return raw / transfer


def initiator_type(entry: dict) -> str:
    initiator = entry.get("_initiator") or {}
    return str(initiator.get("type") or "unknown")


def initiator_frames(entry: dict, limit: int = 3) -> list[str]:
    """Top call frames that issued the request, innermost first."""
    initiator = entry.get("_initiator") or {}
    stack = initiator.get("stack") or {}
    frames: list[str] = []
    while stack and len(frames) < limit:
        for frame in stack.get("callFrames") or []:
            name = frame.get("functionName") or "(anonymous)"
            location = f"{frame.get('url', '')}:{frame.get('lineNumber', '')}"
            frames.append(f"{name} @ {location}")
            if len(frames) >= limit:
                break
        stack = stack.get("parent") or {}
    return frames


def summarize(entries: Iterable[dict], first_party: Iterable[str]) -> list[dict]:
    rows: list[dict] = []
    first_party = list(first_party)
    for entry in entries:
        url = str(entry.get("request", {}).get("url", ""))
        raw = raw_size(entry)
        transfer = transfer_size(entry)
        rows.append(
            {
                "party": classify(url, first_party),
                "initiator": initiator_type(entry),
                "method": entry.get("request", {}).get("method", ""),
                "status": entry.get("response", {}).get("status", 0),
                "raw": raw,
                "transfer": transfer,
                "ratio": compression_ratio(raw, transfer),
                "time_ms": float(entry.get("time") or 0.0),
                "url": url,
            }
        )
    return rows


def totals(rows: Iterable[dict]) -> dict:
    out: dict = {}
    for row in rows:
        bucket = out.setdefault(row["party"], {"count": 0, "raw": 0, "transfer": 0})
        bucket["count"] += 1
        bucket["raw"] += row["raw"]
        bucket["transfer"] += row["transfer"]
    return out


def default_first_party(entries: list[dict]) -> list[str]:
    """Fall back to the host of the first request when none is given."""
    for entry in entries:
        host = host_of(str(entry.get("request", {}).get("url", "")))
        if host:
            return [host]
    return []


def _kib(value: int) -> str:
    return f"{value / 1024:.0f}"


def _ratio(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}x"


def render(rows: list[dict], first_party: list[str], top: int) -> list[str]:
    lines = [f"first-party roots: {', '.join(first_party) or '(none)'}"]
    for party, bucket in sorted(totals(rows).items()):
        lines.append(
            f"{party:<12} requests={bucket['count']:<4} "
            f"transfer_kib={_kib(bucket['transfer']):>7} raw_kib={_kib(bucket['raw']):>7}"
        )
    largest = sorted(rows, key=lambda row: row["raw"], reverse=True)[:top]
    if largest:
        lines.append(f"largest raw bodies (top {len(largest)}):")
    for row in largest:
        lines.append(
            f"  {row['party']:<12} {row['initiator']:<8} raw_kib={_kib(row['raw']):>7} "
            f"transfer_kib={_kib(row['transfer']):>7} ratio={_ratio(row['ratio']):<6} "
            f"time_ms={row['time_ms']:.0f} {row['url']}"
        )
    return lines


def render_matches(entries: list[dict], needle: str) -> list[str]:
    matched = [
        entry
        for entry in entries
        if needle in str(entry.get("request", {}).get("url", ""))
    ]
    lines = [f"requests matching {needle!r}: {len(matched)}"]
    for entry in matched:
        request = entry.get("request", {})
        lines.append(
            f"  {request.get('method', '')} {request.get('url', '')} "
            f"initiator={initiator_type(entry)} time_ms={float(entry.get('time') or 0):.0f}"
        )
        for frame in initiator_frames(entry):
            lines.append(f"    {frame}")
    return lines


def load_entries(path: str) -> list[dict]:
    if path == "-":
        document = json.load(sys.stdin)
    else:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(document.get("log", {}).get("entries", []))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("har", help="path to a saved HAR file, or - for stdin")
    parser.add_argument(
        "--first-party",
        action="append",
        default=[],
        help="host root treated as the application; repeatable",
    )
    parser.add_argument(
        "--match",
        help="substring of a request URL; prints count and initiator frames",
    )
    parser.add_argument("--top", type=int, default=10, help="largest raw bodies to list")
    parser.add_argument("--json", action="store_true", help="emit rows as JSON")
    args = parser.parse_args(argv)

    entries = load_entries(args.har)
    first_party = args.first_party or default_first_party(entries)
    rows = summarize(entries, first_party)

    if args.json:
        print(json.dumps({"first_party": first_party, "rows": rows, "totals": totals(rows)}))
        return 0
    for line in render(rows, first_party, max(args.top, 0)):
        print(line)
    if args.match:
        for line in render_matches(entries, args.match):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
