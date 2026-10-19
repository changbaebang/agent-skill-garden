#!/usr/bin/env python3
"""Deterministic scoring and grading for the optional weekly risk forecast.

``score`` turns six component values into a 0-100 attention score and a band.
``grade`` turns hit, partial, miss, and undecidable counts into precision
figures. Neither is a probability; the score ranks where to look first.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, Optional

COMPONENT_LIMITS: Dict[str, int] = {
    "recurrence": 25,
    "exposure": 25,
    "change": 20,
    "blast_radius": 15,
    "observability": 10,
    "uncertainty": 15,
}
CALIBRATION_MINIMUM = 8


def band_for(score: int) -> str:
    if score >= 70:
        return "very-high"
    if score >= 50:
        return "high"
    if score >= 25:
        return "watch"
    return "omit"


def score(components: Dict[str, int]) -> dict:
    """Validate component ranges and return the score with its band."""
    missing = sorted(set(COMPONENT_LIMITS) - set(components))
    if missing:
        raise ValueError(f"missing components: {', '.join(missing)}")
    for name, limit in COMPONENT_LIMITS.items():
        value = components[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > limit:
            raise ValueError(f"{name} must be an integer between 0 and {limit}, got {value!r}")
    positive = sum(components[name] for name in COMPONENT_LIMITS if name != "uncertainty")
    total = max(0, min(100, positive - components["uncertainty"]))
    return {
        "components": {name: components[name] for name in COMPONENT_LIMITS},
        "score": total,
        "band": band_for(total),
        "publish": total >= 25,
    }


def grade(hit: int, partial: int, miss: int, undecidable: int) -> dict:
    """Return strict and broad precision, keeping undecidable out of the denominator."""
    for name, value in (("hit", hit), ("partial", partial), ("miss", miss), ("undecidable", undecidable)):
        if value < 0:
            raise ValueError(f"{name} must not be negative")
    decidable = hit + partial + miss
    strict = round(hit / decidable, 3) if decidable else None
    broad = round((hit + partial) / decidable, 3) if decidable else None
    return {
        "decidable": decidable,
        "undecidable": undecidable,
        "strict_hit_rate": strict,
        "broad_hit_rate": broad,
        "calibrated": decidable >= CALIBRATION_MINIMUM,
    }


def _render_score(result: dict) -> str:
    parts = " ".join(f"{name}={value}" for name, value in result["components"].items())
    return f"score={result['score']} band={result['band']} publish={str(result['publish']).lower()} ({parts})"


def _render_grade(result: dict) -> str:
    def pct(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value * 100:.1f}%"

    return (
        f"decidable={result['decidable']} undecidable={result['undecidable']} "
        f"strict={pct(result['strict_hit_rate'])} broad={pct(result['broad_hit_rate'])} "
        f"calibrated={str(result['calibrated']).lower()}"
    )


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Score or grade a weekly incident-risk forecast")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of one line")
    commands = parser.add_subparsers(dest="command", required=True)

    scorer = commands.add_parser("score", help="compute the attention score and band")
    for name, limit in COMPONENT_LIMITS.items():
        scorer.add_argument(f"--{name.replace('_', '-')}", type=int, required=True, help=f"0-{limit}")

    grader = commands.add_parser("grade", help="compute precision from graded outcomes")
    for name in ("hit", "partial", "miss", "undecidable"):
        grader.add_argument(f"--{name}", type=int, default=0)

    args = parser.parse_args(argv)
    try:
        if args.command == "score":
            result = score({name: getattr(args, name) for name in COMPONENT_LIMITS})
            text = _render_score(result)
        else:
            result = grade(args.hit, args.partial, args.miss, args.undecidable)
            text = _render_grade(result)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.json else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
