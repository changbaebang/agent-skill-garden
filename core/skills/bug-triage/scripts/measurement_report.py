#!/usr/bin/env python3
"""Compare profile-matrix measurements and name the fields that diverge.

Reads the measurements.json written by profile_matrix.mjs, flattens each
profile's measurement into field -> value, prints a markdown table with fields
as rows and profiles as columns, and lists every field whose values differ
between profiles. When exactly one profile differs on a field while all the
others agree, that profile is named: a single clean profile is as likely masked
as fixed, so that field is where to look next.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def flatten(result: Dict[str, Any]) -> Dict[str, str]:
    """Turn one profile result into a flat mapping of comparable fields."""
    fields: Dict[str, str] = {}
    for name, value in (result.get("cssVariables") or {}).items():
        value = value or {}
        fields[f"{name} computed"] = str(value.get("computed") or "")
        fields[f"{name} inline"] = str(value.get("inline") or "")
    for name, value in (result.get("attributes") or {}).items():
        fields[f"attr {name}"] = "" if value is None else str(value)
    for name, value in (result.get("style") or {}).items():
        fields[f"style.{name}"] = "" if value is None else str(value)
    for name, value in (result.get("rect") or {}).items():
        fields[f"rect.{name}"] = "" if value is None else str(value)
    fields["found"] = "yes" if result.get("found") else "no"
    return fields


def usable_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Profiles whose page load failed carry no comparable measurement."""
    return [result for result in results if not result.get("error")]


def divergent_fields(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fields whose values are not identical across all usable profiles.

    Each entry has the field name, the per-profile values, and
    ``single_profile``: the key of the one profile that disagrees with every
    other profile when all the others agree, otherwise ``None``.
    """
    usable = usable_results(results)
    if len(usable) < 2:
        return []
    flat = {result["key"]: flatten(result) for result in usable}
    names = sorted(set().union(*(fields.keys() for fields in flat.values())))
    divergent: List[Dict[str, Any]] = []
    for name in names:
        values = {key: fields.get(name, "") for key, fields in flat.items()}
        distinct = set(values.values())
        if len(distinct) < 2:
            continue
        single: Optional[str] = None
        if len(distinct) == 2 and len(values) > 2:
            groups = {value: [key for key, held in values.items() if held == value] for value in distinct}
            lone = [members for members in groups.values() if len(members) == 1]
            if len(lone) == 1:
                single = lone[0][0]
        divergent.append({"field": name, "values": values, "single_profile": single})
    return divergent


def render_table(data: Dict[str, Any]) -> str:
    """Markdown table: one row per field, one column per profile."""
    results = data.get("results") or []
    usable = usable_results(results)
    if not usable:
        return "No profile produced a measurement."
    flat = {result["key"]: flatten(result) for result in usable}
    keys = [result["key"] for result in usable]
    names = sorted(set().union(*(fields.keys() for fields in flat.values())))
    differing = {entry["field"] for entry in divergent_fields(results)}
    lines = [
        "| Field | " + " | ".join(keys) + " | Differs |",
        "|---|" + "---|" * len(keys) + "---|",
    ]
    for name in names:
        row = [flat[key].get(name, "") or "-" for key in keys]
        lines.append(f"| {name} | " + " | ".join(row) + f" | {'yes' if name in differing else ''} |")
    return "\n".join(lines)


def render_report(data: Dict[str, Any]) -> str:
    results = data.get("results") or []
    parts = [
        f"## Measurements: `{data.get('selector', '')}` at {data.get('url', '')}",
        "",
        render_table(data),
        "",
    ]
    errors = [result for result in results if result.get("error")]
    if errors:
        parts.append("Profiles excluded because the page failed to load:")
        parts.extend(f"- {result['key']}: {result['error']}" for result in errors)
        parts.append("")
    divergent = divergent_fields(results)
    if not divergent:
        if len(usable_results(results)) >= 2:
            parts.append("All usable profiles agree on every field.")
        return "\n".join(parts)
    parts.append("Fields that differ between profiles:")
    for entry in divergent:
        values = ", ".join(f"{key}={value or '-'}" for key, value in entry["values"].items())
        line = f"- {entry['field']}: {values}"
        if entry["single_profile"]:
            line += f" (only {entry['single_profile']} differs: confirm fixed versus masked)"
        parts.append(line)
    return "\n".join(parts)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("measurements", type=Path, help="measurements.json from profile_matrix.mjs")
    parser.add_argument("--json", action="store_true", help="emit the divergent fields as JSON")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.measurements.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"cannot read {args.measurements}: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(divergent_fields(data.get("results") or []), indent=2, ensure_ascii=False))
    else:
        print(render_report(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
