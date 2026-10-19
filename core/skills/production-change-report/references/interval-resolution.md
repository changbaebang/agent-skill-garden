# Interval resolution

Every report starts from one half-open interval `[start, end)` in one named
time zone. Half-open boundaries keep adjacent reports from counting the same
merge twice and make "merged at exactly midnight" unambiguous.

```bash
python3 scripts/change_window.py interval "7.24~7.26" --tz +09:00
python3 scripts/change_window.py interval "last week" --tz Europe/Berlin --week-start monday
python3 scripts/change_window.py interval "7.22 16:00~7.29 16:00" --tz +09:00 --now 2026-07-30T10:00
```

`--tz` takes a fixed offset or a zone name; `--now` pins observation time for
reproducible runs. The script prints the interval, the time zone, whether the
end was clamped to now, and a one-line interpretation to quote in the report.
A phrase it cannot resolve exits non-zero; ask the user instead of guessing.

## Rules

| Phrase shape | Interval |
| --- | --- |
| two dates, `7.24~7.26` or `2026-07-24 to 2026-07-26` | start of the first day through start of the day after the last; both dates inclusive |
| two date-times, `7.22 16:00~7.29 16:00` | exactly as written; never rounded to days |
| one date | that calendar day |
| `since 7.1` or a date followed by an "onward" marker | that day's start through observation time |
| `last 7 days`, `past 2 weeks`, `last 6 months` | trailing window ending at observation time |
| `last week` | previous calendar week, from the configured week start |
| `this week`, `this month`, `this year` | period start through observation time |
| `last month`, `last year` | previous calendar month or year |
| `last June`, `June`, `2026-06` | the named month; "last" means the most recent completed one, a bare name means the most recent one that has started, clamped to observation time if ongoing |
| `yesterday`, `today` | that calendar day, today clamped to observation time |

The script accepts the common Korean phrasings of the same shapes, for
example:

```text
지난 1주일 · 지난 2주 · 지난 6개월간 · 최근 7일
지난주 · 이번주 · 지난달 · 이번달 · 작년 · 올해 · 어제 · 오늘
지난 6월 · 6월 · 2026년 6월 · 7월 24일~7월 26일 · 7.1 이후
```

## Omitted years

A month and day without a year is the most recent occurrence that is not in
the future. In a range the end date is resolved first; the start takes the same
year unless it would then come after the end, in which case it belongs to the
previous year, so `12.20~1.5` crosses the year boundary correctly.

## Trailing versus calendar

"Last 7 days" and "last week" differ by up to six days of coverage and by
where the boundaries fall. Never substitute one for the other. When a user
mixes them in one request, show both intervals and ask which one the report
should use.

## State the reading

Print the resolved interval at the top of the report even when the phrase was
exact. When the script chose between readings, quote its interpretation line so
the reader can object to the boundary rather than to the content.
