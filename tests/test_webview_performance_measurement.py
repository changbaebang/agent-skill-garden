import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "core/skills/webview-performance-measurement/scripts/cdp_poll.py"
spec = importlib.util.spec_from_file_location("cdp_poll", PATH)
cdp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdp)


class PureFunctionTests(unittest.TestCase):
    def test_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(cdp.nearest_rank(values, 0.5), 50.0)
        self.assertEqual(cdp.nearest_rank(values, 0.9), 90.0)
        self.assertEqual(cdp.nearest_rank([7], 0.75), 7.0)
        self.assertIsNone(cdp.nearest_rank([], 0.5))
        with self.assertRaises(ValueError):
            cdp.nearest_rank([1], 1.5)

    def test_find_samples_shapes(self):
        rows = [{"a": 1}]
        self.assertEqual(cdp.find_samples(rows), rows)
        self.assertEqual(cdp.find_samples({"meta": 1, "samples": rows}), rows)
        self.assertEqual(cdp.find_samples({"x": {"y": {"samples": rows}}}), rows)
        self.assertIsNone(cdp.find_samples({"x": 1}))
        self.assertIsNone(cdp.parse_samples("not json"))
        self.assertEqual(cdp.parse_samples(json.dumps({"samples": rows})), rows)

    def test_summarize_ignores_bool_and_missing(self):
        samples = [{"a": 10, "b": True}, {"a": 20}, {"a": 30, "c": "x"}]
        self.assertEqual(cdp.numeric_keys(samples, ["a"]), ["a"])
        rows = cdp.summarize(samples, ["a", "b"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["n"], 3)
        self.assertEqual(rows[0]["p50"], 20.0)

    def test_select_target_only_pages(self):
        infos = [
            {"type": "service_worker", "url": "https://h/p"},
            {"type": "page", "url": "https://h/other"},
            {"type": "page", "url": "https://h/p?x=1", "targetId": "T"},
        ]
        self.assertEqual(cdp.select_target(infos, "/p")["targetId"], "T")
        self.assertIsNone(cdp.select_target(infos, "zzz"))

    def test_expressions_are_escaped(self):
        self.assertIn('"a\\"b"', cdp.storage_read_expression('a"b'))
        self.assertIn("f(108)", cdp.call_expression("run", 108))

    def test_poll_never_goes_backwards_and_stops_at_target(self):
        reads = iter([None, [{"a": 1}], [{"a": 1}, {"a": 2}], [{"a": 9}], [{"a": 1}, {"a": 2}, {"a": 3}]])
        clock = [0.0]
        result = cdp.poll(
            lambda: next(reads),
            3,
            timeout_s=100,
            interval_s=1,
            sleep=lambda s: clock.__setitem__(0, clock[0] + s),
            now=lambda: clock[0],
        )
        self.assertEqual(len(result), 3)

    def test_poll_times_out_with_partial(self):
        clock = [0.0]
        result = cdp.poll(
            lambda: [{"a": 1}],
            5,
            timeout_s=3,
            interval_s=1,
            sleep=lambda s: clock.__setitem__(0, clock[0] + s),
            now=lambda: clock[0],
        )
        self.assertEqual(len(result), 1)

    def test_args_require_match_and_key(self):
        with self.assertRaises(SystemExit):
            cdp.parse_args([])
        args = cdp.parse_args(["--match", "/p", "--storage-key", "k"])
        self.assertEqual(args.samples, 100)
        self.assertEqual(cdp.parse_args(["--list-targets"]).list_targets, True)


if __name__ == "__main__":
    unittest.main()
