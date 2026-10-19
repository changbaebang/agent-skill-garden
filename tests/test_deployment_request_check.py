import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "core/skills/deployment-request-check/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GATE = load("pr_gate")
REFS = load("change_refs")


def check(name, conclusion, completed=None, started=None, status="COMPLETED"):
    item = {"name": name, "status": status, "conclusion": conclusion}
    if completed:
        item["completedAt"] = completed
    if started:
        item["startedAt"] = started
    return item


def open_change(**overrides):
    base = {
        "url": "https://code.example.test/acme/storefront/pull/482",
        "title": "Add checkout retry",
        "state": "OPEN",
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "author": {"login": "dev-a"},
        "statusCheckRollup": [
            check("unit", "SUCCESS", "2026-02-01T10:00:00Z"),
            check("lint", "SUCCESS", "2026-02-01T10:01:00Z"),
        ],
    }
    base.update(overrides)
    return base


class LatestCheckTests(unittest.TestCase):
    """Only the latest run per check name is judged."""

    def test_rerun_supersedes_older_failure(self) -> None:
        rollup = [
            check("unit", "FAILURE", "2026-02-01T10:00:00Z"),
            check("unit", "SUCCESS", "2026-02-01T11:00:00Z"),
        ]
        result = GATE.evaluate_checks(rollup)
        self.assertEqual(result["failed"], [])
        self.assertEqual(result["superseded"], 1)

    def test_in_progress_rerun_supersedes_completed_failure_by_start_time(self) -> None:
        rollup = [
            check("unit", "FAILURE", "2026-02-01T10:00:00Z"),
            check("unit", None, started="2026-02-01T11:00:00Z", status="IN_PROGRESS"),
        ]
        result = GATE.evaluate_checks(rollup)
        self.assertEqual(result["failed"], [])
        self.assertEqual([GATE.check_name(c) for c in result["pending"]], ["unit"])

    def test_commit_status_uses_context_as_name(self) -> None:
        rollup = [{"context": "deploy-preview", "state": "FAILURE"}]
        result = GATE.evaluate_checks(rollup)
        self.assertEqual([GATE.check_name(c) for c in result["failed"]], ["deploy-preview"])

    def test_exempt_check_moves_failure_out_of_blockers(self) -> None:
        rollup = [check("dependency-scan", "FAILURE", "2026-02-01T10:00:00Z")]
        result = GATE.evaluate_checks(rollup, exempt=["dependency-scan"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(len(result["exempted"]), 1)

    def test_unknown_conclusion_is_not_a_pass(self) -> None:
        self.assertEqual(GATE.check_outcome({"name": "x", "status": "COMPLETED", "conclusion": "WEIRD"}), "failed")
        self.assertEqual(GATE.check_outcome({"name": "x", "status": "QUEUED"}), "pending")
        self.assertEqual(GATE.check_outcome({"name": "x", "conclusion": "SKIPPED"}), "passed")


class ChangeGateTests(unittest.TestCase):
    def test_clean_open_change_is_approvable(self) -> None:
        result = GATE.evaluate_change(open_change())
        self.assertEqual(result["verdict"], GATE.APPROVABLE)
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["checks"]["passed"], 2)

    def test_merged_change_passes_review_axis_without_approval_field(self) -> None:
        result = GATE.evaluate_change(open_change(state="MERGED", mergedAt="2026-02-01T12:00:00Z", reviewDecision=None))
        self.assertEqual(result["verdict"], GATE.APPROVABLE)
        self.assertIn("merged; review axis passes", result["notes"])

    def test_merged_change_with_pending_check_is_a_note_not_a_hold(self) -> None:
        rollup = [check("e2e", None, status="IN_PROGRESS", started="2026-02-01T12:30:00Z")]
        result = GATE.evaluate_change(open_change(state="MERGED", statusCheckRollup=rollup))
        self.assertEqual(result["verdict"], GATE.APPROVABLE)
        self.assertTrue(any("pending checks ignored on a merged change" in note for note in result["notes"]))

    def test_merged_change_with_failing_latest_check_still_holds(self) -> None:
        rollup = [check("unit", "FAILURE", "2026-02-01T10:00:00Z")]
        result = GATE.evaluate_change(open_change(state="MERGED", statusCheckRollup=rollup))
        self.assertEqual([r["code"] for r in result["reasons"]], [GATE.CI_FAILED])

    def test_open_change_with_pending_check_holds(self) -> None:
        rollup = [check("unit", None, status="QUEUED")]
        result = GATE.evaluate_change(open_change(statusCheckRollup=rollup))
        self.assertEqual([r["code"] for r in result["reasons"]], [GATE.CI_PENDING])

    def test_draft_and_changes_requested_both_reported(self) -> None:
        result = GATE.evaluate_change(open_change(isDraft=True, reviewDecision="CHANGES_REQUESTED"))
        self.assertEqual([r["code"] for r in result["reasons"]], [GATE.PR_DRAFT, GATE.PR_NOT_APPROVED])

    def test_conflicting_change_is_not_mergeable(self) -> None:
        result = GATE.evaluate_change(open_change(mergeable="CONFLICTING", mergeStateStatus="DIRTY"))
        self.assertEqual([r["code"] for r in result["reasons"]], [GATE.PR_NOT_MERGEABLE])

    def test_behind_base_is_a_note(self) -> None:
        result = GATE.evaluate_change(open_change(mergeStateStatus="BEHIND"))
        self.assertEqual(result["verdict"], GATE.APPROVABLE)
        self.assertTrue(any("behind the base branch" in note for note in result["notes"]))

    def test_exemption_is_recorded_on_the_change(self) -> None:
        rollup = [check("unit", "SUCCESS", "2026-02-01T10:00:00Z"), check("static-analysis", "FAILURE", "2026-02-01T10:00:00Z")]
        result = GATE.evaluate_change(open_change(statusCheckRollup=rollup), exempt=["static-analysis"])
        self.assertEqual(result["verdict"], GATE.APPROVABLE)
        self.assertEqual(len(result["exemptions"]), 1)
        self.assertIn("static-analysis", result["exemptions"][0])

    def test_fetch_error_is_unverified_not_no_pr(self) -> None:
        result = GATE.evaluate_change({"ref": "acme/storefront#482", "error": "HTTP 404"})
        self.assertEqual([r["code"] for r in result["reasons"]], [GATE.UNVERIFIED])
        self.assertEqual(result["ref"], "acme/storefront#482")


class RequestGateTests(unittest.TestCase):
    def test_one_failing_change_holds_the_request(self) -> None:
        result = GATE.evaluate([open_change(), open_change(url="https://code.example.test/acme/storefront/pull/483", reviewDecision="REVIEW_REQUIRED")])
        self.assertEqual(result["verdict"], GATE.HOLD)
        self.assertEqual([c["verdict"] for c in result["changes"]], [GATE.APPROVABLE, GATE.HOLD])

    def test_empty_input_is_no_pr(self) -> None:
        result = GATE.evaluate([])
        self.assertEqual(result["verdict"], GATE.HOLD)
        self.assertEqual(result["reasons"][0]["code"], GATE.NO_PR)

    def test_single_object_is_accepted(self) -> None:
        self.assertEqual(GATE.evaluate(open_change())["verdict"], GATE.APPROVABLE)

    def test_table_lists_reasons_and_exemptions(self) -> None:
        rollup = [check("scan", "FAILURE", "2026-02-01T10:00:00Z")]
        result = GATE.evaluate([open_change(statusCheckRollup=rollup), {"ref": "acme/storefront#9", "error": "HTTP 401"}], exempt=["scan"])
        table = GATE.render_table(result)
        self.assertIn("| https://code.example.test/acme/storefront/pull/482 | OPEN | APPROVED | 0 passed | MERGEABLE | approvable |", table)
        self.assertIn("not fetched", table)
        self.assertIn("UNVERIFIED (acme/storefront#9)", table)
        self.assertIn("- exemption: scan: FAILURE", table)


class ChangeRefTests(unittest.TestCase):
    def test_links_on_several_hosts_are_found_once(self) -> None:
        text = """
        see https://code.example.test/acme/storefront/pull/482/files and
        https://code.example.test/acme/storefront/pull/482 again,
        https://git.example.test/group/sub/project/-/merge_requests/17 and
        https://bb.example.test/projects/team/repos/app/pull-requests/5/overview
        """
        found = REFS.extract_changes(text)
        self.assertEqual([(f["repository"], f["number"]) for f in found], [
            ("acme/storefront", 482),
            ("group/sub/project", 17),
            ("projects/team/repos/app", 5),
        ])

    def test_escaped_slashes_from_json_exports_are_handled(self) -> None:
        text = json.dumps({"body": "https://code.example.test/acme/storefront/pull/7"}).replace("/", "\\/")
        self.assertEqual(REFS.extract_changes(text)[0]["number"], 7)

    def test_bare_mentions_need_a_default_repository(self) -> None:
        text = "merged PR #482 and #483 today"
        self.assertEqual(REFS.extract_changes(text), [])
        found = REFS.extract_changes(text, default_repo="acme/storefront")
        self.assertEqual([f["number"] for f in found], [482, 483])
        self.assertIsNone(found[0]["url"])
        self.assertEqual(found[0]["repository"], "acme/storefront")

    def test_bare_mention_does_not_duplicate_a_link(self) -> None:
        text = "https://code.example.test/acme/storefront/pull/482 (#482)"
        found = REFS.extract_changes(text, default_repo="acme/storefront")
        self.assertEqual(len(found), 1)

    def test_tracker_keys_keep_digits_in_the_prefix(self) -> None:
        self.assertEqual(REFS.extract_keys("AB1CD-42 blocks AB1CD-42 and ZZ-7"), ["AB1CD-42", "ZZ-7"])

    def test_permalink_root_and_reply(self) -> None:
        root = REFS.parse_permalink("https://chat.example.test/archives/ROOM42/p1700000000123456")
        self.assertEqual(root["channel"], "ROOM42")
        self.assertEqual(root["message_ts"], "1700000000.123456")
        self.assertEqual(root["thread_ts"], "1700000000.123456")
        self.assertFalse(root["is_reply"])
        reply = REFS.parse_permalink(
            "https://chat.example.test/archives/ROOM42/p1700000500999999?thread_ts=1700000000.123456&cid=ROOM42"
        )
        self.assertEqual(reply["thread_ts"], "1700000000.123456")
        self.assertTrue(reply["is_reply"])

    def test_unrecognised_permalink_raises(self) -> None:
        with self.assertRaises(ValueError):
            REFS.parse_permalink("https://chat.example.test/not-a-thread")


def run_main(module, argv):
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
        code = module.main(argv)
    return code, out.getvalue()


class CommandLineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_gate_exit_codes(self) -> None:
        good = self.root / "good.json"
        good.write_text(json.dumps(open_change()), encoding="utf-8")
        self.assertEqual(run_main(GATE, [str(good)])[0], 0)
        bad = self.root / "bad.json"
        bad.write_text(json.dumps(open_change(reviewDecision="REVIEW_REQUIRED")), encoding="utf-8")
        code, out = run_main(GATE, [str(bad), "--markdown"])
        self.assertEqual(code, 2)
        self.assertIn("PR_NOT_APPROVED", out)
        self.assertEqual(run_main(GATE, [str(self.root / "missing.json")])[0], 1)

    def test_refs_commands(self) -> None:
        text = self.root / "thread.txt"
        text.write_text("AB1CD-42 https://code.example.test/acme/storefront/pull/482 #483", encoding="utf-8")
        code, out = run_main(REFS, ["changes", str(text), "--default-repo", "acme/storefront"])
        self.assertEqual(code, 0)
        self.assertEqual([item["number"] for item in json.loads(out)], [482, 483])
        code, out = run_main(REFS, ["keys", str(text)])
        self.assertEqual((code, out.strip()), (0, "AB1CD-42"))
        code, out = run_main(REFS, ["permalink", "https://chat.example.test/archives/ROOM42/p1700000000123456"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["channel"], "ROOM42")
        self.assertEqual(run_main(REFS, ["permalink", "nope"])[0], 1)


if __name__ == "__main__":
    unittest.main()
