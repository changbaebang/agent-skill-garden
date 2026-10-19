#!/usr/bin/env python3
"""Deterministic arithmetic for a requirements document review.

Reads one JSON object (file or stdin) that records which sections are present,
the five axis scores, and optional alignment counts. Prints the derived
document type, readiness score and band, "implement now" eligibility, and
alignment score. The reviewer supplies every judgment; this script only keeps
the arithmetic honest and repeatable.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Sequence

SECTIONS = (
    "background",
    "goals",
    "users",
    "scenarios",
    "acceptance",
    "data",
    "exceptions",
    "impact",
)
AXES = ("clarity", "scope", "risk", "dependencies", "ambiguity")
STATUSES = ("met", "partial", "missing", "undocumented")

AXIS_MIN = 1
AXIS_MAX = 5
WEAK_AXIS = 2
HIGH_BAND = 80
MEDIUM_BAND = 60

COMPLETE = "complete"
DRAFT = "draft"
NOT_REQUIREMENTS = "not a requirements document"


class InputError(ValueError):
    """Raised when the input object cannot be scored as given."""


def _require_int(value: Any, label: str) -> int:
    # bool is a subclass of int; a stray true/false must not become a score.
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputError(f"{label} must be an integer, got {value!r}")
    return value


def classify_document(
    sections_present: Sequence[str], not_requirements_reason: Optional[str]
) -> Dict[str, Any]:
    present = set(sections_present)
    unknown = sorted(present - set(SECTIONS))
    if unknown:
        raise InputError(
            "unknown section key(s): " + ", ".join(unknown)
            + "; expected " + ", ".join(SECTIONS)
        )
    missing = [section for section in SECTIONS if section not in present]
    if not_requirements_reason:
        document_type = NOT_REQUIREMENTS
    elif not present:
        document_type = NOT_REQUIREMENTS
    elif missing:
        document_type = DRAFT
    else:
        document_type = COMPLETE
    return {"document_type": document_type, "missing_sections": missing}


def validate_axes(axes: Any) -> Dict[str, int]:
    if not isinstance(axes, dict):
        raise InputError("axes must be an object keyed by axis name")
    extra = sorted(set(axes) - set(AXES))
    absent = [axis for axis in AXES if axis not in axes]
    if extra or absent:
        raise InputError(
            "axes must contain exactly " + ", ".join(AXES)
            + (f"; unknown: {', '.join(extra)}" if extra else "")
            + (f"; missing: {', '.join(absent)}" if absent else "")
        )
    checked: Dict[str, int] = {}
    for axis in AXES:
        value = _require_int(axes[axis], f"axis {axis}")
        if value < AXIS_MIN or value > AXIS_MAX:
            raise InputError(
                f"axis {axis} must be between {AXIS_MIN} and {AXIS_MAX}, got {value}"
            )
        checked[axis] = value
    return checked


def readiness_score(axes: Dict[str, int]) -> int:
    # mean * 20 with five integer axes is always an integer (sum * 4).
    return sum(axes.values()) * 20 // len(AXES)


def readiness_band(score: int) -> str:
    if score >= HIGH_BAND:
        return "high"
    if score >= MEDIUM_BAND:
        return "medium"
    return "low"


def weakest_axes(axes: Dict[str, int]) -> List[str]:
    lowest = min(axes.values())
    return [axis for axis in AXES if axes[axis] == lowest]


def implement_now_eligible(document_type: str, band: str, axes: Dict[str, int]) -> bool:
    return (
        document_type == COMPLETE
        and band == "high"
        and min(axes.values()) > WEAK_AXIS
    )


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def alignment_score(counts: Any) -> Dict[str, Any]:
    if not isinstance(counts, dict):
        raise InputError("alignment must be an object keyed by status name")
    extra = sorted(set(counts) - set(STATUSES))
    if extra:
        raise InputError("unknown alignment status(es): " + ", ".join(extra))
    checked: Dict[str, int] = {}
    for status in STATUSES:
        value = _require_int(counts.get(status, 0), f"alignment {status}")
        if value < 0:
            raise InputError(f"alignment {status} must not be negative, got {value}")
        checked[status] = value
    denominator = checked["met"] + checked["partial"] + checked["missing"]
    score: Optional[int]
    if denominator == 0:
        score = None
    else:
        score = _round_half_up(
            (checked["met"] + 0.5 * checked["partial"]) / denominator * 100
        )
    return {
        "alignment_score": score,
        "alignment_counts": checked,
        "overbuild_count": checked["undocumented"],
    }


def score(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("input must be a JSON object")
    sections = payload.get("sections_present", [])
    if not isinstance(sections, list) or not all(isinstance(s, str) for s in sections):
        raise InputError("sections_present must be an array of section keys")
    reason = payload.get("not_requirements_reason")
    if reason is not None and not isinstance(reason, str):
        raise InputError("not_requirements_reason must be a string or null")

    result: Dict[str, Any] = classify_document(sections, reason)
    if reason:
        result["not_requirements_reason"] = reason

    axes = validate_axes(payload.get("axes"))
    readiness = readiness_score(axes)
    band = readiness_band(readiness)
    result.update(
        {
            "axes": axes,
            "readiness_score": readiness,
            "readiness_band": band,
            "weakest_axes": weakest_axes(axes),
            "implement_now_eligible": implement_now_eligible(
                result["document_type"], band, axes
            ),
        }
    )

    if "alignment" in payload and payload["alignment"] is not None:
        result.update(alignment_score(payload["alignment"]))
    else:
        result.update(
            {"alignment_score": None, "alignment_counts": None, "overbuild_count": None}
        )
    return result


def render_text(result: Dict[str, Any]) -> str:
    lines = [
        f"Document type: {result['document_type']}",
    ]
    if result.get("missing_sections"):
        lines.append("Missing sections: " + ", ".join(result["missing_sections"]))
    axes = result["axes"]
    lines.append(
        "Axes: " + " · ".join(f"{axis} {axes[axis]}" for axis in AXES)
    )
    lines.append(
        f"Readiness: {result['readiness_score']} ({result['readiness_band']})"
    )
    lines.append("Weakest: " + ", ".join(result["weakest_axes"]))
    lines.append(
        "Implement now eligible: " + ("yes" if result["implement_now_eligible"] else "no")
    )
    if result.get("alignment_counts") is None:
        lines.append("Alignment: not supplied")
    elif result["alignment_score"] is None:
        lines.append("Alignment: not computable (no documented rows)")
    else:
        counts = result["alignment_counts"]
        lines.append(
            f"Alignment: {result['alignment_score']} "
            f"(met {counts['met']} · partial {counts['partial']} · "
            f"missing {counts['missing']} · overbuild {counts['undocumented']})"
        )
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute readiness and alignment figures for a requirements review."
    )
    parser.add_argument(
        "--input", help="JSON file to read; defaults to standard input"
    )
    parser.add_argument(
        "--format", choices=("json", "text"), default="json", help="output format"
    )
    args = parser.parse_args(argv)

    try:
        if args.input:
            with open(args.input, encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read input: {error}", file=sys.stderr)
        return 2

    try:
        result = score(payload)
    except InputError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.format == "text":
        print(render_text(result))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
