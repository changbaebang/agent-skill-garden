#!/usr/bin/env python3
"""Deterministic helpers for the production change report.

Subcommands:

  interval PHRASE [--now ISO] [--tz ZONE] [--week-start monday|sunday]
      Resolve a natural-language period into a half-open interval [start, end)
      in one time zone. Prints JSON with start, end, the interpretation used,
      and whether the end was clamped to observation time.

  select --prs FILE --base BRANCH --start ISO --end ISO
         [--wrapper-title REGEX ...] [--wrapper-head REGEX ...]
      Keep pull requests merged into BRANCH with a merge time inside
      [start, end). Explain every exclusion. Mark likely wrappers (release or
      test-branch merges carrying other changes) and reverts, and pair a revert
      with the request it undoes when the titles allow it.

No network access. The script knows no organization: repositories, branches,
time zones, and naming conventions all arrive on the command line.

English and Korean phrasings are recognized for the same period shapes.
Examples: "7.24~7.26", "7.22 16:00~7.29 16:00", "2026-07-24 to 2026-07-26",
"last 7 days", "last week", "last June", "2026-06", "since 7.1", "yesterday",
"지난 1주일", "지난주", "지난 6월", "지난 6개월간", "7월 24일~7월 26일", "7.1 이후".
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Dict, List, Optional, Sequence, Tuple

# --- time zones --------------------------------------------------------------

OFFSET = re.compile(r"^(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)


def parse_zone(text: str) -> tzinfo:
    """Accept ``Z``, ``UTC``, a fixed offset such as ``+09:00``, or a zone name."""
    trimmed = text.strip()
    if trimmed.upper() in ("Z", "UTC", "GMT"):
        return timezone.utc
    match = OFFSET.match(trimmed)
    if match:
        sign = 1 if match.group(1) == "+" else -1
        hours = int(match.group(2))
        minutes = int(match.group(3) or 0)
        if hours > 23 or minutes > 59:
            raise ValueError(f"invalid offset: {text}")
        return timezone(sign * timedelta(hours=hours, minutes=minutes), trimmed)
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError as error:  # pragma: no cover - only on very old interpreters
        raise ValueError(f"zone names need Python 3.9 or newer: {text}") from error
    try:
        return ZoneInfo(trimmed)
    except Exception as error:
        raise ValueError(f"unknown time zone: {text}") from error


def parse_iso(text: str, zone: tzinfo) -> datetime:
    """Parse an ISO 8601 date or date-time; a naive value is read in ``zone``."""
    trimmed = text.strip()
    if trimmed.endswith(("Z", "z")):
        trimmed = trimmed[:-1] + "+00:00"
    try:
        value = datetime.fromisoformat(trimmed)
    except ValueError as error:
        raise ValueError(f"not an ISO 8601 date or date-time: {text}") from error
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def iso(value: datetime) -> str:
    return value.isoformat(timespec="minutes")


# --- calendar arithmetic ----------------------------------------------------


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def month_start(year: int, month: int, zone: tzinfo) -> datetime:
    return datetime(year, month, 1, tzinfo=zone)


def day_start(day: date, zone: tzinfo) -> datetime:
    return datetime.combine(day, time.min, tzinfo=zone)


def week_start_of(day: date, week_start: str) -> date:
    # Monday is 0 in ``weekday()``; a Sunday-start week shifts the anchor by one.
    offset = day.weekday() if week_start == "monday" else (day.weekday() + 1) % 7
    return day - timedelta(days=offset)


# --- phrase normalization ---------------------------------------------------

MONTH_NAMES = {
    name.lower(): index
    for index, name in enumerate(calendar.month_name)
    if name
}
MONTH_NAMES.update(
    {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
)
MONTH_NAMES["sept"] = 9

UNIT_DAYS = {"day": 1, "days": 1, "일": 1, "week": 7, "weeks": 7, "주": 7, "주일": 7}
UNIT_MONTHS = {"month": 1, "months": 1, "개월": 1, "달": 1}


def normalize(phrase: str) -> str:
    text = phrase.strip().lower()
    text = text.replace("～", "~").replace("∼", "~").replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text


# A single date, optionally with a time. ISO first so ``2026-07-24`` is not read
# as ``07.24`` inside it; the slash/dot form must not start inside a longer number.
DATE_TOKEN = re.compile(
    r"(?P<iso>(?P<iy>\d{4})-(?P<im>\d{1,2})-(?P<id>\d{1,2})(?:[ t](?P<ih>\d{1,2}):(?P<imin>\d{2}))?)"
    r"|(?P<kr>(?:(?P<ky>\d{4})\s*년\s*)?(?P<km>\d{1,2})\s*월\s*(?P<kd>\d{1,2})\s*일(?:\s*(?P<kh>\d{1,2}):(?P<kmin>\d{2}))?)"
    r"|(?P<dot>(?<![\d.])(?:(?P<dy>\d{4})[./])?(?P<dm>\d{1,2})[./](?P<dd>\d{1,2})\.?(?![\d./])(?:\s+(?P<dh>\d{1,2}):(?P<dmin>\d{2}))?)"
)

MONTH_ONLY = re.compile(
    r"^(?P<last>last |previous |지난 ?)?"
    r"(?:(?P<year>\d{4})(?:년)?[- ]?)?"
    r"(?:(?P<name>[a-z]{3,9})|(?P<num>\d{1,2})\s*월)"
    r"(?: 한 ?달| 한달|간| month)?$"
)

TRAILING = re.compile(
    r"^(?:last|past|trailing|previous|지난|최근)\s*(?P<n>\d+)\s*(?P<unit>days?|weeks?|months?|일|주일|주|개월|달)(?:간|동안)?$"
    r"|^(?:past|trailing)\s+(?P<unit2>day|week|month)$"
    r"|^(?:최근|지난)\s*(?P<n3>\d+)(?P<unit3>일|주일|주|개월)(?:간|동안)?$"
)

SINCE = re.compile(r"^(?:since|from|after)\s+(?P<rest>.+?)(?:\s+(?:onward|onwards|until now|to now|to date))?$|^(?P<rest2>.+?)\s*(?:이후|부터|이래|이후로)$")

RANGE_SEPARATOR = re.compile(r"\s*(?:~|\.\.|…|\bto\b|\bthrough\b|\buntil\b|\btill\b|부터|에서|까지)\s*|\s+-\s+")


class Token:
    __slots__ = ("year", "month", "day", "hour", "minute", "has_time")

    def __init__(self, year: Optional[int], month: int, day: int, hour: Optional[int], minute: Optional[int]) -> None:
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.has_time = hour is not None


def _tokens(text: str) -> List[Token]:
    found: List[Token] = []
    for match in DATE_TOKEN.finditer(text):
        kind = match.lastgroup if match.lastgroup in ("iso", "kr", "dot") else None
        for prefix in ("i", "k", "d"):
            if match.group(prefix + "m") is not None:
                year = match.group(prefix + "y")
                hour = match.group(prefix + "h")
                minute = match.group(prefix + "min")
                found.append(
                    Token(
                        int(year) if year else None,
                        int(match.group(prefix + "m")),
                        int(match.group(prefix + "d")),
                        int(hour) if hour is not None else None,
                        int(minute) if minute is not None else None,
                    )
                )
                break
        del kind
    return found


def _resolve_day(token: Token, now: datetime, not_after: Optional[date] = None) -> date:
    """Pick the year for a token: explicit, else the latest occurrence not in the future.

    ``not_after`` lets a range start inherit the end's year and step back one
    year when it would otherwise follow the end.
    """
    if token.year is not None:
        return _safe_date(token.year, token.month, token.day)
    anchor = not_after if not_after is not None else now.date()
    candidate = _safe_date(anchor.year, token.month, token.day)
    if candidate > anchor:
        candidate = _safe_date(anchor.year - 1, token.month, token.day)
    return candidate


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as error:
        raise ValueError(f"not a calendar date: {year}-{month:02d}-{day:02d}") from error


def _token_start(token: Token, day: date, zone: tzinfo) -> datetime:
    if token.has_time:
        return datetime.combine(day, time(token.hour or 0, token.minute or 0), tzinfo=zone)
    return day_start(day, zone)


# --- resolution --------------------------------------------------------------


def resolve_interval(phrase: str, now: datetime, week_start: str = "monday") -> dict:
    """Return ``{"start", "end", "interpretation", "clamped_to_now", "exact_time"}``.

    ``now`` must be time-zone aware; the result shares its zone. Raises
    ``ValueError`` when the phrase has no supported reading.
    """
    if now.tzinfo is None:
        raise ValueError("observation time must carry a time zone")
    if week_start not in ("monday", "sunday"):
        raise ValueError("week start must be monday or sunday")
    zone = now.tzinfo
    text = normalize(phrase)
    if not text:
        raise ValueError("empty period")
    today = now.date()

    def result(start: datetime, end: datetime, interpretation: str, exact_time: bool = False) -> dict:
        clamped = False
        if end > now and not exact_time:
            end = now
            clamped = True
        if start >= end:
            raise ValueError(f"interval is empty: {iso(start)} to {iso(end)}")
        return {
            "phrase": phrase,
            "start": iso(start),
            "end": iso(end),
            "timezone": start.strftime("%z")[:3] + ":" + start.strftime("%z")[3:] if start.utcoffset() is not None else None,
            "interpretation": interpretation,
            "clamped_to_now": clamped,
            "exact_time": exact_time,
        }

    # Relative single days.
    if text in ("today", "오늘", "금일"):
        return result(day_start(today, zone), day_start(today + timedelta(days=1), zone), "today, clamped to observation time")
    if text in ("yesterday", "어제", "전일"):
        start = day_start(today - timedelta(days=1), zone)
        return result(start, start + timedelta(days=1), "yesterday, whole calendar day")

    # Calendar week, month, year.
    if text in ("last week", "previous week", "지난주", "지난 주", "전주", "저번주", "저번 주"):
        this_week = day_start(week_start_of(today, week_start), zone)
        return result(this_week - timedelta(days=7), this_week, f"previous calendar week starting {week_start}")
    if text in ("this week", "current week", "이번주", "이번 주", "금주"):
        return result(day_start(week_start_of(today, week_start), zone), now, f"current calendar week starting {week_start}, through observation time")
    if text in ("last month", "previous month", "지난달", "지난 달", "전월", "저번달", "저번 달"):
        this_month = month_start(today.year, today.month, zone)
        return result(add_months(this_month, -1), this_month, "previous calendar month")
    if text in ("this month", "current month", "이번달", "이번 달", "당월", "금월"):
        return result(month_start(today.year, today.month, zone), now, "current calendar month through observation time")
    if text in ("last year", "previous year", "작년", "지난해", "전년"):
        return result(month_start(today.year - 1, 1, zone), month_start(today.year, 1, zone), "previous calendar year")
    if text in ("this year", "current year", "올해", "금년", "이번 해"):
        return result(month_start(today.year, 1, zone), now, "current calendar year through observation time")

    # Trailing windows.
    trailing = TRAILING.match(text)
    if trailing:
        if trailing.group("unit2"):
            count, unit = 1, trailing.group("unit2")
        elif trailing.group("unit3"):
            count, unit = int(trailing.group("n3")), trailing.group("unit3")
        else:
            count, unit = int(trailing.group("n")), trailing.group("unit")
        if count <= 0:
            raise ValueError("a trailing window needs a positive count")
        if unit in UNIT_MONTHS:
            start = add_months(now, -count)
            label = f"trailing {count} calendar month(s) ending at observation time"
        else:
            start = now - timedelta(days=count * UNIT_DAYS[unit])
            label = f"trailing {count * UNIT_DAYS[unit]} days ending at observation time"
        return result(start, now, label, exact_time=True)

    # Explicit dates: a range, a single day, or an open-ended "since".
    tokens = _tokens(text)
    if len(tokens) >= 2:
        if len(tokens) > 2:
            raise ValueError(f"more than two dates in one period: {phrase}")
        first, second = tokens
        end_day = _resolve_day(second, now)
        start_day = _resolve_day(first, now, not_after=end_day)
        start = _token_start(first, start_day, zone)
        if second.has_time:
            end = _token_start(second, end_day, zone)
            label = "explicit date-times, kept exactly"
        else:
            end = day_start(end_day + timedelta(days=1), zone)
            label = "two calendar dates, both inclusive"
        return result(start, end, label, exact_time=second.has_time or first.has_time)
    if len(tokens) == 1:
        token = tokens[0]
        day = _resolve_day(token, now)
        since = SINCE.match(text)
        if since:
            start = _token_start(token, day, zone)
            return result(start, now, "open-ended period from the date through observation time", exact_time=True)
        if token.has_time:
            raise ValueError(f"a single date-time needs a second boundary: {phrase}")
        start = day_start(day, zone)
        return result(start, start + timedelta(days=1), "single calendar day")

    # Month by name or number, optionally with a year or "last".
    month = MONTH_ONLY.match(text)
    if month:
        if month.group("name"):
            number = MONTH_NAMES.get(month.group("name"))
            if number is None:
                raise ValueError(f"not a month name: {month.group('name')}")
        else:
            number = int(month.group("num"))
        if not 1 <= number <= 12:
            raise ValueError(f"not a month: {number}")
        if month.group("year"):
            year = int(month.group("year"))
            label = "named month with explicit year"
        elif month.group("last"):
            year = today.year
            if add_months(month_start(year, number, zone), 1) > now:
                year -= 1
            label = "most recent completed occurrence of the named month"
        else:
            year = today.year
            if month_start(year, number, zone) > now:
                year -= 1
            label = "most recent occurrence of the named month that has started"
        start = month_start(year, number, zone)
        return result(start, add_months(start, 1), label)

    raise ValueError(f"could not resolve the period: {phrase}")


# --- pull-request selection -------------------------------------------------

DEFAULT_WRAPPER_TITLE = (
    r"^\s*(?:release|deploy|deployment|rollup|roll-up|hotfix release)\b",
    r"\b(?:release|deploy|deployment|rollup|roll-up)\b.*\b(?:to|into)\b",
    r"(?:->|→)\s*\S+\s*$",
)
DEFAULT_WRAPPER_HEAD = (
    r"^(?:qa|staging|stage|release|releases|develop|dev|test|integration|rc)(?:/|$)",
)
REVERT_TITLE = re.compile(r"^\s*revert\b[:\s]*", re.IGNORECASE)
QUOTED = re.compile(r"[\"“”'‘’]([^\"“”'‘’]+)[\"“”'‘’]")


def _field(item: dict, *names: str):
    for name in names:
        if name in item and item[name] is not None:
            return item[name]
    return None


def _title_key(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def select_requests(
    requests: Sequence[dict],
    base: str,
    start: datetime,
    end: datetime,
    wrapper_title: Optional[Sequence[str]] = None,
    wrapper_head: Optional[Sequence[str]] = None,
) -> dict:
    """Filter exported pull requests to the merge basis and annotate them."""
    if start >= end:
        raise ValueError("start must be before end")
    title_patterns = [re.compile(p, re.IGNORECASE) for p in (wrapper_title or DEFAULT_WRAPPER_TITLE)]
    head_patterns = [re.compile(p, re.IGNORECASE) for p in (wrapper_head or DEFAULT_WRAPPER_HEAD)]
    zone = start.tzinfo or timezone.utc

    selected: List[dict] = []
    excluded: List[dict] = []
    for item in requests:
        number = _field(item, "number", "id")
        title = str(_field(item, "title") or "")
        entry = {"number": number, "title": title, "url": _field(item, "url", "html_url")}
        state = _field(item, "state")
        merged_at = _field(item, "mergedAt", "merged_at")
        request_base = _field(item, "baseRefName", "base_ref", "base")
        if isinstance(request_base, dict):
            request_base = request_base.get("ref")
        head = _field(item, "headRefName", "head_ref", "head")
        if isinstance(head, dict):
            head = head.get("ref")

        if not merged_at:
            excluded.append(dict(entry, reason="not merged"))
            continue
        if state and str(state).upper() != "MERGED":
            excluded.append(dict(entry, reason=f"state {state}"))
            continue
        if request_base != base:
            excluded.append(dict(entry, reason=f"base {request_base!r} is not {base!r}"))
            continue
        try:
            merged = parse_iso(str(merged_at), zone)
        except ValueError:
            excluded.append(dict(entry, reason=f"unreadable merge time {merged_at!r}"))
            continue
        if not start <= merged < end:
            excluded.append(dict(entry, reason="merged outside the interval", mergedAt=iso(merged)))
            continue

        wrapper_reason = None
        for pattern in head_patterns:
            if head and pattern.search(str(head)):
                wrapper_reason = f"head branch {head!r}"
                break
        if wrapper_reason is None:
            for pattern in title_patterns:
                if pattern.search(title):
                    wrapper_reason = "title"
                    break
        selected.append(
            dict(
                entry,
                mergedAt=iso(merged),
                head=head,
                author=_author(item),
                wrapper=wrapper_reason is not None,
                wrapper_reason=wrapper_reason,
                revert=bool(REVERT_TITLE.match(title)),
                reverted_by=None,
            )
        )

    selected.sort(key=lambda row: row["mergedAt"])
    _pair_reverts(selected)
    return {
        "base": base,
        "start": iso(start),
        "end": iso(end),
        "selected": selected,
        "excluded": excluded,
        "counts": {
            "selected": len(selected),
            "wrappers": sum(1 for row in selected if row["wrapper"]),
            "reverts": sum(1 for row in selected if row["revert"]),
            "reverted": sum(1 for row in selected if row["reverted_by"] is not None),
            "excluded": len(excluded),
        },
    }


def _author(item: dict) -> Optional[str]:
    author = _field(item, "author", "user")
    if isinstance(author, dict):
        return author.get("login") or author.get("name")
    return author if isinstance(author, str) else None


def _pair_reverts(selected: List[dict]) -> None:
    """Link a revert to the earlier request whose title it quotes."""
    by_title: Dict[str, List[dict]] = {}
    for row in selected:
        if not row["revert"]:
            by_title.setdefault(_title_key(row["title"]), []).append(row)
    for row in selected:
        if not row["revert"]:
            continue
        stripped = REVERT_TITLE.sub("", row["title"])
        candidates = [_title_key(q) for q in QUOTED.findall(stripped)] or [_title_key(stripped)]
        for key in candidates:
            for original in by_title.get(key, []):
                if original["mergedAt"] <= row["mergedAt"] and original["reverted_by"] is None:
                    original["reverted_by"] = row["number"]
                    break


# --- command line -------------------------------------------------------------


def _cmd_interval(args: argparse.Namespace) -> int:
    zone = parse_zone(args.tz)
    now = parse_iso(args.now, zone) if args.now else datetime.now(zone)
    try:
        payload = resolve_interval(args.phrase, now, args.week_start)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    payload["now"] = iso(now)
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def _cmd_select(args: argparse.Namespace) -> int:
    zone = parse_zone(args.tz)
    start = parse_iso(args.start, zone)
    end = parse_iso(args.end, zone)
    with open(args.prs, encoding="utf-8") as handle:
        requests = json.load(handle)
    if isinstance(requests, dict):
        requests = requests.get("items") or requests.get("data") or []
    if not isinstance(requests, list):
        print("ERROR: the export must be a JSON array of pull requests", file=sys.stderr)
        return 2
    try:
        payload = select_requests(requests, args.base, start, end, args.wrapper_title, args.wrapper_head)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    interval = sub.add_parser("interval", help="resolve a period phrase into [start, end)")
    interval.add_argument("phrase")
    interval.add_argument("--now", help="observation time, ISO 8601; defaults to the current time")
    interval.add_argument("--tz", default="UTC", help="fixed offset such as +09:00 or a zone name; default UTC")
    interval.add_argument("--week-start", default="monday", choices=("monday", "sunday"))
    interval.set_defaults(func=_cmd_interval)

    select = sub.add_parser("select", help="filter exported pull requests to the merge basis")
    select.add_argument("--prs", required=True, help="JSON array exported from the code host")
    select.add_argument("--base", required=True, help="verified production branch name")
    select.add_argument("--start", required=True, help="interval start, ISO 8601")
    select.add_argument("--end", required=True, help="interval end, ISO 8601, exclusive")
    select.add_argument("--tz", default="UTC", help="zone for naive --start/--end values; default UTC")
    select.add_argument("--wrapper-title", action="append", help="regex marking a wrapper by title; replaces the defaults")
    select.add_argument("--wrapper-head", action="append", help="regex marking a wrapper by head branch; replaces the defaults")
    select.set_defaults(func=_cmd_select)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
