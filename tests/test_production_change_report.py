import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/production-change-report/scripts/change_window.py"
SPEC = importlib.util.spec_from_file_location("change_window", MODULE_PATH)
assert SPEC and SPEC.loader
CW = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CW
SPEC.loader.exec_module(CW)

NOW = "2026-07-30T10:00"


def resolve(phrase, week_start="monday"):
    zone = CW.parse_zone("+09:00")
    return CW.resolve_interval(phrase, CW.parse_iso(NOW, zone), week_start)


class IntervalTests(unittest.TestCase):
    def test_inclusive_date_range(self):
        r = resolve("7.24~7.26")
        self.assertEqual(r["start"], "2026-07-24T00:00+09:00")
        self.assertEqual(r["end"], "2026-07-27T00:00+09:00")

    def test_explicit_time_kept(self):
        r = resolve("7.22 16:00~7.29 16:00")
        self.assertEqual(r["start"], "2026-07-22T16:00+09:00")
        self.assertEqual(r["end"], "2026-07-29T16:00+09:00")

    def test_last_week_is_calendar_week(self):
        r = resolve("last week")
        self.assertEqual(r["start"], "2026-07-20T00:00+09:00")
        self.assertEqual(r["end"], "2026-07-27T00:00+09:00")

    def test_korean_last_week_matches(self):
        self.assertEqual(resolve("지난주")["start"], resolve("last week")["start"])

    def test_unresolvable_raises(self):
        with self.assertRaises(ValueError):
            resolve("whenever")


class SelectTests(unittest.TestCase):
    def test_filters_base_and_time(self):
        zone = CW.parse_zone("+09:00")
        start = CW.parse_iso("2026-07-24T00:00", zone)
        end = CW.parse_iso("2026-07-27T00:00", zone)
        prs = [
            {"number": 1, "title": "Add thing", "baseRefName": "main", "mergedAt": "2026-07-25T01:00:00Z"},
            {"number": 2, "title": "Other base", "baseRefName": "dev", "mergedAt": "2026-07-25T01:00:00Z"},
            {"number": 3, "title": "Too late", "baseRefName": "main", "mergedAt": "2026-07-28T01:00:00Z"},
        ]
        out = CW.select_requests(prs, "main", start, end)
        self.assertEqual([p["number"] for p in out["selected"]], [1])
        self.assertEqual(len(out["excluded"]), 2)


if __name__ == "__main__":
    unittest.main()
