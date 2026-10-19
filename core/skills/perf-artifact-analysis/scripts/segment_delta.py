#!/usr/bin/env python3
"""Per-segment percentile deltas with thin-sample flags and noise subtraction.

Input is a JSON document with two runs, each mapping a segment name to its
samples in milliseconds:

    {"before": {"backend": [..], "render": [..], "end_to_end": [..]},
     "after":  {"backend": [..], "render": [..], "end_to_end": [..]}}

Two percentile formulas are offered because harnesses and aggregators differ,
and numbers from different formulas must not be compared.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

NEAREST_RANK = "nearest-rank"
LINEAR = "linear"
METHODS = (NEAREST_RANK, LINEAR)


def nearest_rank(samples: Sequence[float], p: float) -> float:
    """sorted[ceil(n * p) - 1]; p=0 yields the minimum."""
    ordered = sorted(samples)
    if not ordered:
        raise ValueError("no samples")
    rank = math.ceil(len(ordered) * p)
    return float(ordered[max(rank, 1) - 1])


def linear(samples: Sequence[float], p: float) -> float:
    """Interpolate at index (n - 1) * p, the default of most numeric libraries."""
    ordered = sorted(samples)
    if not ordered:
        raise ValueError("no samples")
    index = (len(ordered) - 1) * p
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return float(ordered[low])
    fraction = index - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def percentile(samples: Sequence[float], p: float, method: str) -> float:
    if not 0.0 <= p <= 1.0:
        raise ValueError("percentile must be between 0 and 1")
    if method == NEAREST_RANK:
        return nearest_rank(samples, p)
    if method == LINEAR:
        return linear(samples, p)
    raise ValueError(f"unknown method {method!r}")


def segment_rows(
    before: dict,
    after: dict,
    p: float,
    method: str,
    min_n: int,
    noise: Sequence[str],
) -> list[dict]:
    rows: list[dict] = []
    for name in sorted(set(before) | set(after)):
        left = list(before.get(name) or [])
        right = list(after.get(name) or [])
        row: dict = {
            "segment": name,
            "n_before": len(left),
            "n_after": len(right),
            "before": None,
            "after": None,
            "delta": None,
            "flags": [],
        }
        if not left or not right:
            row["flags"].append("missing")
        else:
            row["before"] = percentile(left, p, method)
            row["after"] = percentile(right, p, method)
            row["delta"] = row["after"] - row["before"]
        if left and right and min(len(left), len(right)) < min_n:
            row["flags"].append("thin")
        if name in noise:
            row["flags"].append("noise")
        rows.append(row)
    return rows


def attribute(rows: Sequence[dict], total: str | None) -> dict:
    """Total delta, the noise part, and what remains attributable."""
    usable = [row for row in rows if row["delta"] is not None]
    noise_delta = sum(row["delta"] for row in usable if "noise" in row["flags"])
    if total is not None:
        matches = [row for row in usable if row["segment"] == total]
        if not matches:
            raise ValueError(f"total segment {total!r} is missing from one run")
        total_delta = matches[0]["delta"]
        basis = f"segment {total}"
    else:
        total_delta = sum(row["delta"] for row in usable)
        basis = "sum of segment deltas"
    return {
        "basis": basis,
        "total_delta": total_delta,
        "noise_delta": noise_delta,
        "attributed_delta": total_delta - noise_delta,
    }


def compare_methods(before: dict, after: dict, p: float) -> list[dict]:
    out: list[dict] = []
    for run_name, run in (("before", before), ("after", after)):
        for name in sorted(run):
            samples = list(run[name] or [])
            if not samples:
                continue
            values = {method: percentile(samples, p, method) for method in METHODS}
            out.append(
                {
                    "run": run_name,
                    "segment": name,
                    "n": len(samples),
                    NEAREST_RANK: values[NEAREST_RANK],
                    LINEAR: values[LINEAR],
                    "differs": values[NEAREST_RANK] != values[LINEAR],
                }
            )
    return out


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def render(rows: Sequence[dict], summary: dict, p: float, method: str) -> list[str]:
    lines = [f"percentile p{int(round(p * 100))} method={method}"]
    for row in rows:
        flags = ",".join(row["flags"]) or "-"
        lines.append(
            f"{row['segment']:<20} n={row['n_before']}/{row['n_after']:<5} "
            f"before={_fmt(row['before']):>8} after={_fmt(row['after']):>8} "
            f"delta={_fmt(row['delta']):>8} flags={flags}"
        )
    lines.append(
        f"total_delta={summary['total_delta']:.1f} ({summary['basis']}) "
        f"noise_delta={summary['noise_delta']:.1f} "
        f"attributed_delta={summary['attributed_delta']:.1f}"
    )
    return lines


def render_comparison(rows: Sequence[dict]) -> list[str]:
    lines = ["percentile formulas side by side"]
    for row in rows:
        marker = "differs" if row["differs"] else "same"
        lines.append(
            f"{row['run']:<6} {row['segment']:<20} n={row['n']:<5} "
            f"nearest-rank={row[NEAREST_RANK]:.1f} linear={row[LINEAR]:.1f} {marker}"
        )
    return lines


def load(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="JSON file with before/after runs, or -")
    parser.add_argument("--percentile", type=float, default=0.5, help="0..1, default 0.5")
    parser.add_argument("--method", choices=METHODS, default=NEAREST_RANK)
    parser.add_argument("--min-n", type=int, default=5, help="flag segments thinner than this")
    parser.add_argument(
        "--noise",
        action="append",
        default=[],
        help="segment whose delta is variance, not effect; repeatable",
    )
    parser.add_argument("--total", help="segment that holds the end-to-end metric")
    parser.add_argument(
        "--compare-methods",
        action="store_true",
        help="print both percentile formulas instead of the delta table",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    document = load(args.input)
    before = document.get("before") or {}
    after = document.get("after") or {}
    if not before or not after:
        print("input needs both 'before' and 'after' runs", file=sys.stderr)
        return 2

    if args.compare_methods:
        comparison = compare_methods(before, after, args.percentile)
        if args.json:
            print(json.dumps(comparison))
        else:
            for line in render_comparison(comparison):
                print(line)
        return 0

    rows = segment_rows(before, after, args.percentile, args.method, args.min_n, args.noise)
    try:
        summary = attribute(rows, args.total)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"rows": rows, "summary": summary}))
    else:
        for line in render(rows, summary, args.percentile, args.method):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
