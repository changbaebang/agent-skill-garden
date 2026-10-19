from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "core" / "skills" / "incident-response" / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


INCIDENT_REF = load("incident_ref")
RISK_SCORE = load("risk_score")


class IncidentReferenceTests(unittest.TestCase):
    def test_tracker_key_yields_key_and_channel(self) -> None:
        result = INCIDENT_REF.parse_reference("OPS-17")
        self.assertEqual(result["incident_number"], "17")
        self.assertEqual(result["tracker_key"], "OPS-17")
        self.assertEqual(result["channel_name"], "incident-17")
        self.assertEqual(result["source"], "tracker-key")

    def test_tracker_url_is_read_as_its_key(self) -> None:
        result = INCIDENT_REF.parse_reference("  https://tracker.example/browse/OPS-17 ")
        self.assertEqual(result["tracker_key"], "OPS-17")
        self.assertEqual(result["source"], "tracker-key")

    def test_channel_name_without_project_leaves_key_unknown(self) -> None:
        for text in ("#incident-17", "incident-17", "#Incident-17"):
            with self.subTest(text=text):
                result = INCIDENT_REF.parse_reference(text)
                self.assertEqual(result["incident_number"], "17")
                self.assertIsNone(result["tracker_key"])
                self.assertEqual(result["channel_name"], "incident-17")
                self.assertEqual(result["source"], "channel-name")

    def test_channel_name_with_project_builds_the_key(self) -> None:
        result = INCIDENT_REF.parse_reference("#incident-17", project="OPS")
        self.assertEqual(result["tracker_key"], "OPS-17")

    def test_upper_case_prefix_is_a_tracker_key_not_a_channel(self) -> None:
        # The channel convention is lower case; an upper-case form is the tracker project.
        result = INCIDENT_REF.parse_reference("INCIDENT-17")
        self.assertEqual(result["tracker_key"], "INCIDENT-17")
        self.assertEqual(result["channel_name"], "incident-17")
        self.assertEqual(result["source"], "tracker-key")

    def test_custom_channel_prefix(self) -> None:
        result = INCIDENT_REF.parse_reference("#outage-3", channel_prefix="outage-")
        self.assertEqual(result["channel_name"], "outage-3")
        hashed = INCIDENT_REF.parse_reference("OPS-3", channel_prefix="outage-")
        self.assertEqual(hashed["channel_name"], "outage-3")

    def test_empty_channel_prefix_derives_no_channel(self) -> None:
        result = INCIDENT_REF.parse_reference("OPS-3", channel_prefix="")
        self.assertIsNone(result["channel_name"])

    def test_chat_permalink_yields_channel_id_and_timestamp(self) -> None:
        result = INCIDENT_REF.parse_reference("https://chat.example/archives/C123ABC/p1700000000123456")
        self.assertEqual(result["channel_id"], "C123ABC")
        self.assertEqual(result["message_ts"], "1700000000.123456")
        self.assertIsNone(result["incident_number"])
        self.assertEqual(result["source"], "chat-permalink")

    def test_unrecognized_text_raises(self) -> None:
        for text in ("", "   ", "nothing to see", "#other-channel"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    INCIDENT_REF.parse_reference(text)

    def test_cli_exit_codes(self) -> None:
        ok = subprocess.run(
            [sys.executable, str(SCRIPTS / "incident_ref.py"), "OPS-1"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn('"tracker_key": "OPS-1"', ok.stdout)
        bad = subprocess.run(
            [sys.executable, str(SCRIPTS / "incident_ref.py"), "nothing"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(bad.returncode, 2)
        self.assertIn("ERROR", bad.stderr)


class RiskScoreTests(unittest.TestCase):
    def components(self, **overrides: int) -> dict:
        base = {
            "recurrence": 14,
            "exposure": 15,
            "change": 12,
            "blast_radius": 11,
            "observability": 4,
            "uncertainty": 5,
        }
        base.update(overrides)
        return base

    def test_score_sums_components_and_subtracts_uncertainty(self) -> None:
        result = RISK_SCORE.score(self.components())
        self.assertEqual(result["score"], 51)
        self.assertEqual(result["band"], "high")
        self.assertTrue(result["publish"])

    def test_bands_at_boundaries(self) -> None:
        self.assertEqual(RISK_SCORE.band_for(70), "very-high")
        self.assertEqual(RISK_SCORE.band_for(69), "high")
        self.assertEqual(RISK_SCORE.band_for(50), "high")
        self.assertEqual(RISK_SCORE.band_for(49), "watch")
        self.assertEqual(RISK_SCORE.band_for(25), "watch")
        self.assertEqual(RISK_SCORE.band_for(24), "omit")

    def test_score_is_clamped_to_zero(self) -> None:
        result = RISK_SCORE.score(
            self.components(recurrence=0, exposure=0, change=0, blast_radius=3, observability=0, uncertainty=15)
        )
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["band"], "omit")
        self.assertFalse(result["publish"])

    def test_out_of_range_component_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RISK_SCORE.score(self.components(recurrence=26))
        with self.assertRaises(ValueError):
            RISK_SCORE.score(self.components(uncertainty=-1))

    def test_missing_component_is_rejected(self) -> None:
        components = self.components()
        del components["change"]
        with self.assertRaises(ValueError):
            RISK_SCORE.score(components)

    def test_grade_keeps_undecidable_out_of_the_denominator(self) -> None:
        result = RISK_SCORE.grade(hit=3, partial=2, miss=1, undecidable=4)
        self.assertEqual(result["decidable"], 6)
        self.assertEqual(result["undecidable"], 4)
        self.assertEqual(result["strict_hit_rate"], 0.5)
        self.assertEqual(result["broad_hit_rate"], 0.833)
        self.assertFalse(result["calibrated"])

    def test_grade_with_nothing_decidable_has_no_rates(self) -> None:
        result = RISK_SCORE.grade(hit=0, partial=0, miss=0, undecidable=2)
        self.assertIsNone(result["strict_hit_rate"])
        self.assertIsNone(result["broad_hit_rate"])

    def test_calibration_needs_eight_decidable(self) -> None:
        self.assertTrue(RISK_SCORE.grade(hit=5, partial=2, miss=1, undecidable=0)["calibrated"])
        self.assertFalse(RISK_SCORE.grade(hit=5, partial=1, miss=1, undecidable=9)["calibrated"])

    def test_cli_score_and_grade(self) -> None:
        scored = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "risk_score.py"), "score",
                "--recurrence", "14", "--exposure", "15", "--change", "12",
                "--blast-radius", "11", "--observability", "4", "--uncertainty", "5",
            ],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(scored.returncode, 0, scored.stderr)
        self.assertIn("score=51 band=high", scored.stdout)
        rejected = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "risk_score.py"), "score",
                "--recurrence", "99", "--exposure", "0", "--change", "0",
                "--blast-radius", "0", "--observability", "0", "--uncertainty", "0",
            ],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(rejected.returncode, 2)
        graded = subprocess.run(
            [sys.executable, str(SCRIPTS / "risk_score.py"), "--json", "grade", "--hit", "1", "--miss", "1"],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(graded.returncode, 0, graded.stderr)
        self.assertIn('"strict_hit_rate": 0.5', graded.stdout)


if __name__ == "__main__":
    unittest.main()
