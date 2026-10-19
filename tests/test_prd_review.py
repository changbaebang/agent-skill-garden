import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "core/skills/prd-review/scripts/score_requirements.py"
SPEC = importlib.util.spec_from_file_location("score_requirements", MODULE_PATH)
assert SPEC and SPEC.loader
SCORER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCORER
SPEC.loader.exec_module(SCORER)

ALL_SECTIONS = list(SCORER.SECTIONS)


def axes(clarity=4, scope=4, risk=4, dependencies=4, ambiguity=4):
    return {
        "clarity": clarity,
        "scope": scope,
        "risk": risk,
        "dependencies": dependencies,
        "ambiguity": ambiguity,
    }


class DocumentTypeTest(unittest.TestCase):
    def test_all_sections_present_is_complete(self) -> None:
        result = SCORER.classify_document(ALL_SECTIONS, None)
        self.assertEqual(result["document_type"], SCORER.COMPLETE)
        self.assertEqual(result["missing_sections"], [])

    def test_some_sections_present_is_draft_and_lists_missing(self) -> None:
        result = SCORER.classify_document(["background", "acceptance"], None)
        self.assertEqual(result["document_type"], SCORER.DRAFT)
        self.assertEqual(
            result["missing_sections"],
            ["goals", "users", "scenarios", "data", "exceptions", "impact"],
        )

    def test_no_sections_is_not_a_requirements_document(self) -> None:
        result = SCORER.classify_document([], None)
        self.assertEqual(result["document_type"], SCORER.NOT_REQUIREMENTS)

    def test_explicit_reason_overrides_full_checklist(self) -> None:
        # An archived copy can still carry every heading; the reason wins.
        result = SCORER.classify_document(ALL_SECTIONS, "archived copy")
        self.assertEqual(result["document_type"], SCORER.NOT_REQUIREMENTS)

    def test_unknown_section_key_is_rejected(self) -> None:
        with self.assertRaises(SCORER.InputError):
            SCORER.classify_document(["background", "summary"], None)


class AxisBoundsTest(unittest.TestCase):
    def test_missing_axis_is_rejected(self) -> None:
        broken = axes()
        del broken["risk"]
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(broken)

    def test_unknown_axis_is_rejected(self) -> None:
        broken = axes()
        broken["novelty"] = 3
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(broken)

    def test_out_of_range_is_rejected(self) -> None:
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(axes(clarity=0))
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(axes(scope=6))

    def test_boolean_is_not_a_score(self) -> None:
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(axes(risk=True))

    def test_non_integer_is_rejected(self) -> None:
        with self.assertRaises(SCORER.InputError):
            SCORER.validate_axes(axes(ambiguity=3.5))


class ReadinessTest(unittest.TestCase):
    def test_score_is_mean_times_twenty(self) -> None:
        self.assertEqual(SCORER.readiness_score(axes(4, 3, 4, 3, 4)), 72)
        self.assertEqual(SCORER.readiness_score(axes(5, 5, 5, 5, 5)), 100)
        self.assertEqual(SCORER.readiness_score(axes(1, 1, 1, 1, 1)), 20)

    def test_band_boundaries(self) -> None:
        self.assertEqual(SCORER.readiness_band(80), "high")
        self.assertEqual(SCORER.readiness_band(79), "medium")
        self.assertEqual(SCORER.readiness_band(60), "medium")
        self.assertEqual(SCORER.readiness_band(59), "low")

    def test_weakest_axes_reports_ties(self) -> None:
        self.assertEqual(
            SCORER.weakest_axes(axes(3, 5, 3, 4, 4)), ["clarity", "risk"]
        )


class ImplementNowTest(unittest.TestCase):
    def test_eligible_when_complete_high_and_no_weak_axis(self) -> None:
        self.assertTrue(
            SCORER.implement_now_eligible(SCORER.COMPLETE, "high", axes(4, 4, 4, 4, 4))
        )

    def test_one_weak_axis_blocks_even_with_high_mean(self) -> None:
        weak = axes(5, 5, 5, 5, 2)  # mean 88, still blocked
        self.assertEqual(SCORER.readiness_band(SCORER.readiness_score(weak)), "high")
        self.assertFalse(SCORER.implement_now_eligible(SCORER.COMPLETE, "high", weak))

    def test_draft_is_never_eligible(self) -> None:
        self.assertFalse(
            SCORER.implement_now_eligible(SCORER.DRAFT, "high", axes(5, 5, 5, 5, 5))
        )

    def test_medium_band_is_not_eligible(self) -> None:
        self.assertFalse(
            SCORER.implement_now_eligible(SCORER.COMPLETE, "medium", axes(3, 3, 3, 3, 3))
        )


class AlignmentTest(unittest.TestCase):
    def test_partial_counts_half_and_undocumented_is_excluded(self) -> None:
        result = SCORER.alignment_score(
            {"met": 4, "partial": 1, "missing": 2, "undocumented": 1}
        )
        # (4 + 0.5) / 7 = 64.28...
        self.assertEqual(result["alignment_score"], 64)
        self.assertEqual(result["overbuild_count"], 1)

    def test_rounds_half_up(self) -> None:
        # (0 + 0.5) / 4 = 12.5 -> 13, not banker's 12
        result = SCORER.alignment_score({"met": 0, "partial": 1, "missing": 3})
        self.assertEqual(result["alignment_score"], 13)

    def test_overbuild_alone_does_not_raise_coverage(self) -> None:
        with_overbuild = SCORER.alignment_score(
            {"met": 2, "partial": 0, "missing": 2, "undocumented": 5}
        )
        without = SCORER.alignment_score({"met": 2, "partial": 0, "missing": 2})
        self.assertEqual(with_overbuild["alignment_score"], without["alignment_score"])
        self.assertEqual(with_overbuild["alignment_score"], 50)

    def test_no_documented_rows_is_not_computable(self) -> None:
        result = SCORER.alignment_score({"undocumented": 3})
        self.assertIsNone(result["alignment_score"])
        self.assertEqual(result["overbuild_count"], 3)

    def test_negative_or_unknown_status_is_rejected(self) -> None:
        with self.assertRaises(SCORER.InputError):
            SCORER.alignment_score({"met": -1})
        with self.assertRaises(SCORER.InputError):
            SCORER.alignment_score({"done": 2})


class EndToEndTest(unittest.TestCase):
    def run_script(self, payload, *flags):
        return subprocess.run(
            [sys.executable, str(MODULE_PATH), *flags],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_json_output_carries_every_derived_field(self) -> None:
        payload = {
            "sections_present": ALL_SECTIONS,
            "axes": axes(4, 3, 4, 3, 4),
            "alignment": {"met": 4, "partial": 1, "missing": 2, "undocumented": 1},
        }
        completed = self.run_script(payload)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["document_type"], "complete")
        self.assertEqual(result["readiness_score"], 72)
        self.assertEqual(result["readiness_band"], "medium")
        self.assertFalse(result["implement_now_eligible"])
        self.assertEqual(result["alignment_score"], 64)
        self.assertEqual(result["overbuild_count"], 1)

    def test_missing_alignment_is_reported_as_not_supplied(self) -> None:
        payload = {"sections_present": ["background"], "axes": axes(2, 2, 2, 2, 2)}
        completed = self.run_script(payload, "--format", "text")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Document type: draft", completed.stdout)
        self.assertIn("Readiness: 40 (low)", completed.stdout)
        self.assertIn("Alignment: not supplied", completed.stdout)

    def test_bad_input_exits_two_without_a_score(self) -> None:
        completed = self.run_script({"sections_present": [], "axes": axes(clarity=9)})
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("axis clarity", completed.stderr)

    def test_invalid_json_exits_two(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH)],
            input="{not json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("cannot read input", completed.stderr)


if __name__ == "__main__":
    unittest.main()
