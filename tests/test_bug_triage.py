import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/bug-triage/scripts/measurement_report.py"
SPEC = importlib.util.spec_from_file_location("measurement_report", MODULE_PATH)
assert SPEC and SPEC.loader
REPORT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPORT
SPEC.loader.exec_module(REPORT)


def profile(key: str, *, computed: str = "59px", inline=None, padding: str = "59px", error=None) -> dict:
    return {
        "key": key,
        "label": key,
        "error": error,
        "found": True,
        "cssVariables": {"--safe-area-inset-top": {"computed": computed, "inline": inline}},
        "attributes": {"body[data-client]": "embedded"},
        "style": {"paddingTop": padding},
        "rect": {"top": 0, "height": 103, "width": 390},
    }


class FlattenFieldsTest(unittest.TestCase):
    def test_every_measured_group_becomes_a_field(self) -> None:
        fields = REPORT.flatten(profile("web", inline="0px"))
        self.assertEqual(fields["--safe-area-inset-top computed"], "59px")
        self.assertEqual(fields["--safe-area-inset-top inline"], "0px")
        self.assertEqual(fields["attr body[data-client]"], "embedded")
        self.assertEqual(fields["style.paddingTop"], "59px")
        self.assertEqual(fields["rect.height"], "103")
        self.assertEqual(fields["found"], "yes")

    def test_missing_element_is_reported_not_crashed(self) -> None:
        fields = REPORT.flatten({"key": "web", "found": False})
        self.assertEqual(fields, {"found": "no"})


class DivergenceTest(unittest.TestCase):
    """A clean profile is a signal to compare values, so the report must name it."""

    def test_identical_profiles_do_not_diverge(self) -> None:
        results = [profile("web"), profile("ios"), profile("android")]
        self.assertEqual(REPORT.divergent_fields(results), [])

    def test_single_masked_profile_is_named(self) -> None:
        # The polyfill wrote the variable inline on one platform; the computed
        # value and the padding followed it. Three fields differ, and in each
        # case exactly one profile is the odd one out.
        results = [
            profile("web"),
            profile("ios"),
            profile("android", computed="0px", inline="0px", padding="0px"),
        ]
        divergent = REPORT.divergent_fields(results)
        names = {entry["field"]: entry for entry in divergent}
        self.assertEqual(
            set(names),
            {"--safe-area-inset-top computed", "--safe-area-inset-top inline", "style.paddingTop"},
        )
        for entry in divergent:
            self.assertEqual(entry["single_profile"], "android", entry)

    def test_two_profiles_cannot_single_out_one(self) -> None:
        results = [profile("web"), profile("ios", padding="0px")]
        divergent = REPORT.divergent_fields(results)
        self.assertEqual([entry["field"] for entry in divergent], ["style.paddingTop"])
        self.assertIsNone(divergent[0]["single_profile"])

    def test_three_distinct_values_single_out_nobody(self) -> None:
        results = [profile("a", padding="1px"), profile("b", padding="2px"), profile("c", padding="3px")]
        divergent = REPORT.divergent_fields(results)
        self.assertEqual(len(divergent), 1)
        self.assertIsNone(divergent[0]["single_profile"])

    def test_failed_loads_are_excluded_from_comparison(self) -> None:
        results = [profile("web"), profile("ios"), profile("android", padding="0px", error="net::ERR_FAILED")]
        self.assertEqual(REPORT.divergent_fields(results), [])
        self.assertEqual(REPORT.divergent_fields([profile("web"), profile("ios", error="timeout")]), [])


class RenderTest(unittest.TestCase):
    def test_table_has_fields_as_rows_and_marks_differences(self) -> None:
        data = {
            "url": "https://example.test/page",
            "selector": "header",
            "results": [profile("web"), profile("ios"), profile("android", padding="0px")],
        }
        table = REPORT.render_table(data)
        self.assertIn("| Field | web | ios | android | Differs |", table)
        self.assertIn("| style.paddingTop | 59px | 59px | 0px | yes |", table)
        self.assertIn("| found | yes | yes | yes |  |", table)

    def test_report_names_the_lone_profile_and_the_errors(self) -> None:
        data = {
            "url": "https://example.test/page",
            "selector": "header",
            "results": [
                profile("web"),
                profile("ios"),
                profile("android", padding="0px"),
                profile("broken", error="Timeout 60000ms exceeded"),
            ],
        }
        report = REPORT.render_report(data)
        self.assertIn("only android differs: confirm fixed versus masked", report)
        self.assertIn("- broken: Timeout 60000ms exceeded", report)

    def test_report_states_agreement_when_nothing_differs(self) -> None:
        data = {"url": "u", "selector": "s", "results": [profile("web"), profile("ios")]}
        self.assertIn("All usable profiles agree on every field.", REPORT.render_report(data))


class CliTest(unittest.TestCase):
    def test_main_reads_a_file_and_emits_json(self) -> None:
        data = {"url": "u", "selector": "s", "results": [profile("web"), profile("ios", padding="0px")]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "measurements.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = REPORT.main([str(path), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload[0]["field"], "style.paddingTop")

    def test_main_reports_unreadable_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            self.assertEqual(REPORT.main([str(missing)]), 2)


if __name__ == "__main__":
    unittest.main()
