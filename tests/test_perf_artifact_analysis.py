from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "perf-artifact-analysis"
    / "scripts"
)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HAR = load("har_summary")
DELTA = load("segment_delta")


def entry(
    url: str,
    *,
    raw: int = 0,
    transfer: int = 0,
    initiator: str = "script",
    frames: list[dict] | None = None,
    time: float = 10.0,
    method: str = "GET",
) -> dict:
    record = {
        "request": {"method": method, "url": url},
        "response": {
            "status": 200,
            "content": {"size": raw},
            "_transferSize": transfer,
        },
        "time": time,
        "_initiator": {"type": initiator},
    }
    if frames is not None:
        record["_initiator"]["stack"] = {"callFrames": frames}
    return record


class PartyRuleTests(unittest.TestCase):
    def test_subdomain_of_a_first_party_root_is_the_application(self) -> None:
        self.assertEqual(
            HAR.classify("https://static.example.com/app.js", ["example.com"]), HAR.APP
        )

    def test_lookalike_host_is_third_party(self) -> None:
        self.assertEqual(
            HAR.classify("https://notexample.com/x.js", ["example.com"]), HAR.THIRD_PARTY
        )

    def test_extension_scheme_wins_over_host(self) -> None:
        self.assertEqual(
            HAR.classify("chrome-extension://abc/hook.js", ["abc"]), HAR.EXTENSION
        )

    def test_first_party_defaults_to_the_first_request_host(self) -> None:
        entries = [entry("https://shop.example.org/"), entry("https://cdn.other.net/a.js")]
        self.assertEqual(HAR.default_first_party(entries), ["shop.example.org"])


class SizeTests(unittest.TestCase):
    def test_unknown_sizes_count_as_zero(self) -> None:
        record = entry("https://example.com/a", raw=-1)
        record["response"]["_transferSize"] = -1
        record["response"]["bodySize"] = -1
        self.assertEqual(HAR.raw_size(record), 0)
        self.assertEqual(HAR.transfer_size(record), 0)
        self.assertIsNone(HAR.compression_ratio(0, 0))

    def test_transfer_falls_back_to_body_plus_headers(self) -> None:
        record = entry("https://example.com/a", raw=100)
        del record["response"]["_transferSize"]
        record["response"]["bodySize"] = 30
        record["response"]["headersSize"] = 10
        self.assertEqual(HAR.transfer_size(record), 40)

    def test_ratio_is_raw_over_transfer(self) -> None:
        self.assertAlmostEqual(HAR.compression_ratio(3220, 928), 3.47, places=2)


class SummaryTests(unittest.TestCase):
    def test_totals_are_grouped_by_party(self) -> None:
        rows = HAR.summarize(
            [
                entry("https://example.com/app.js", raw=3000, transfer=900),
                entry("https://example.com/api", raw=50, transfer=40, initiator="script"),
                entry("https://tags.vendor.io/t.js", raw=400, transfer=100),
                entry("chrome-extension://zzz/hook.js", raw=700, transfer=700),
            ],
            ["example.com"],
        )
        total = HAR.totals(rows)
        self.assertEqual(total[HAR.APP]["count"], 2)
        self.assertEqual(total[HAR.APP]["raw"], 3050)
        self.assertEqual(total[HAR.THIRD_PARTY]["raw"], 400)
        self.assertEqual(total[HAR.EXTENSION]["count"], 1)

    def test_initiator_frames_follow_async_parents(self) -> None:
        record = entry(
            "https://example.com/api",
            frames=[{"functionName": "onClick", "url": "https://example.com/c.js", "lineNumber": 4}],
        )
        record["_initiator"]["stack"]["parent"] = {
            "callFrames": [
                {"functionName": "dispatch", "url": "https://example.com/r.js", "lineNumber": 9}
            ]
        }
        self.assertEqual(
            HAR.initiator_frames(record),
            ["onClick @ https://example.com/c.js:4", "dispatch @ https://example.com/r.js:9"],
        )

    def test_match_reports_count_and_frames(self) -> None:
        lines = HAR.render_matches(
            [
                entry(
                    "https://example.com/api/items",
                    frames=[{"functionName": "useItems", "url": "u.js", "lineNumber": 1}],
                ),
                entry("https://example.com/api/other"),
            ],
            "/api/items",
        )
        self.assertEqual(lines[0], "requests matching '/api/items': 1")
        self.assertTrue(any("useItems @ u.js:1" in line for line in lines))

    def test_cli_reads_stdin_and_emits_json(self) -> None:
        document = {"log": {"entries": [entry("https://example.com/a.js", raw=10, transfer=5)]}}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(document))):
                self.assertEqual(HAR.main(["-", "--json"]), 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["first_party"], ["example.com"])
        self.assertEqual(payload["rows"][0]["ratio"], 2.0)


class PercentileTests(unittest.TestCase):
    SAMPLES = list(range(1, 11))

    def test_nearest_rank_and_linear_differ_on_the_same_data(self) -> None:
        self.assertEqual(DELTA.nearest_rank(self.SAMPLES, 0.9), 9.0)
        self.assertAlmostEqual(DELTA.linear(self.SAMPLES, 0.9), 9.1)

    def test_median_of_even_count(self) -> None:
        self.assertEqual(DELTA.nearest_rank([4, 1, 3, 2], 0.5), 2.0)
        self.assertEqual(DELTA.linear([4, 1, 3, 2], 0.5), 2.5)

    def test_extremes(self) -> None:
        self.assertEqual(DELTA.nearest_rank(self.SAMPLES, 0.0), 1.0)
        self.assertEqual(DELTA.nearest_rank(self.SAMPLES, 1.0), 10.0)
        self.assertEqual(DELTA.linear(self.SAMPLES, 1.0), 10.0)

    def test_rejects_empty_and_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            DELTA.percentile([], 0.5, DELTA.NEAREST_RANK)
        with self.assertRaises(ValueError):
            DELTA.percentile([1.0], 1.5, DELTA.LINEAR)


class SegmentDeltaTests(unittest.TestCase):
    BEFORE = {
        "backend": [200, 210, 220, 230, 240, 250],
        "render": [100, 100, 100, 100, 100, 100],
        "end_to_end": [600, 610, 620, 630, 640, 650],
        "thin": [5, 6],
    }
    AFTER = {
        "backend": [180, 190, 200, 210, 220, 230],
        "render": [80, 80, 80, 80, 80, 80],
        "end_to_end": [560, 570, 580, 590, 600, 610],
        "thin": [7, 8],
    }

    def rows(self, **kwargs):
        options = {"p": 0.5, "method": DELTA.NEAREST_RANK, "min_n": 5, "noise": ["backend"]}
        options.update(kwargs)
        return DELTA.segment_rows(self.BEFORE, self.AFTER, **options)

    def test_noise_is_subtracted_from_the_total_segment(self) -> None:
        summary = DELTA.attribute(self.rows(), "end_to_end")
        self.assertEqual(summary["total_delta"], -40.0)
        self.assertEqual(summary["noise_delta"], -20.0)
        self.assertEqual(summary["attributed_delta"], -20.0)
        self.assertEqual(summary["basis"], "segment end_to_end")

    def test_thin_segments_are_flagged_not_dropped(self) -> None:
        by_name = {row["segment"]: row for row in self.rows()}
        self.assertIn("thin", by_name["thin"]["flags"])
        self.assertNotIn("thin", by_name["render"]["flags"])
        self.assertIn("noise", by_name["backend"]["flags"])

    def test_missing_segment_on_one_side_is_flagged(self) -> None:
        after = dict(self.AFTER)
        del after["render"]
        rows = DELTA.segment_rows(self.BEFORE, after, 0.5, DELTA.NEAREST_RANK, 5, [])
        render_row = next(row for row in rows if row["segment"] == "render")
        self.assertEqual(render_row["flags"], ["missing"])
        self.assertIsNone(render_row["delta"])

    def test_total_without_a_named_segment_sums_deltas(self) -> None:
        summary = DELTA.attribute(self.rows(), None)
        self.assertEqual(summary["basis"], "sum of segment deltas")
        # backend -20, render -20, end_to_end -40, thin +2
        self.assertEqual(summary["total_delta"], -78.0)

    def test_missing_total_segment_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            DELTA.attribute(self.rows(), "nope")

    def test_compare_methods_marks_where_formulas_diverge(self) -> None:
        comparison = DELTA.compare_methods(
            {"a": list(range(1, 11))}, {"a": [1, 1, 1]}, 0.9
        )
        self.assertTrue(comparison[0]["differs"])
        self.assertFalse(comparison[1]["differs"])

    def test_cli_json_round_trip(self) -> None:
        document = {"before": self.BEFORE, "after": self.AFTER}
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(document))):
                code = DELTA.main(
                    ["--input", "-", "--total", "end_to_end", "--noise", "backend", "--json"]
                )
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["summary"]["attributed_delta"], -20.0)

    def test_cli_rejects_a_document_without_both_runs(self) -> None:
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps({"before": {"a": [1]}}))):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(DELTA.main(["--input", "-"]), 2)


if __name__ == "__main__":
    unittest.main()
