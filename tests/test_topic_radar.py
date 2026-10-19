from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "core"
    / "skills"
    / "topic-radar"
    / "scripts"
    / "backlog_report.py"
)
SPEC = importlib.util.spec_from_file_location("backlog_report", SCRIPT)
assert SPEC and SPEC.loader
BACKLOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BACKLOG)


def write_item(items: Path, name: str, status: str, added: str, area: str, body: str,
               draft_slug: str = "", source: str = "https://example.org/talk") -> Path:
    path = items / name
    path.write_text(
        "---\n"
        "type: learn-item\n"
        f'title: "Example item {name}"\n'
        f'source: "{source}"\n'
        "source_type: talk\n"
        f"area: [{area}]\n"
        f"status: {status}\n"
        f"added: {added}\n"
        f'draft_slug: "{draft_slug}"\n'
        "---\n\n"
        f"# Example item\n\n{body}",
        encoding="utf-8",
    )
    return path


TEMPLATE_BODY = (
    "## Why learn\n- connects to a running series\n\n"
    "## After learning\n- takeaways:\n- apply where:\n- still unclear:\n\n"
    "## Draft angle\n- title candidates:\n- shape: guide | checklist\n- draft_slug:\n"
)

FILLED_BODY = (
    "## Why learn\n- connects to a running series\n\n"
    "## After learning\n- takeaways: Secret takeaway sentence about budgets.\n"
    "- apply where: the review checklist\n- still unclear: nothing\n\n"
    "## Draft angle\n- title candidates: Budgets before dashboards\n"
    "- shape: checklist\n- draft_slug: budgets-before-dashboards\n"
)


class SummaryTests(unittest.TestCase):
    def test_counts_statuses_areas_and_stale_items_without_body_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = root / "items"
            items.mkdir()
            write_item(items, "2026-01-01-old.md", "queued", "2026-01-01", "web-performance", TEMPLATE_BODY)
            write_item(items, "2026-03-01-fresh.md", "queued", "2026-03-01", "web-performance", TEMPLATE_BODY)
            write_item(items, "2026-02-01-learned.md", "done", "2026-02-01", "agent-operations", FILLED_BODY,
                       draft_slug="budgets-before-dashboards")
            write_item(items, "2026-02-02-odd.md", "someday", "2026-02-02", "agent-operations", TEMPLATE_BODY)

            report = BACKLOG.summarize(BACKLOG.load_items(root), date(2026, 3, 10), 30)
            rendered = str(report)

            self.assertEqual(report["item_count"], 4)
            self.assertEqual(report["status_counts"], {"done": 1, "queued": 2, "someday": 1})
            self.assertEqual(report["area_counts"], {"agent-operations": 2, "web-performance": 2})
            self.assertEqual(report["unknown_status"], ["items/2026-02-02-odd.md"])
            self.assertEqual([item["slug"] for item in report["stale_queued"]], ["old"])
            self.assertEqual(report["stale_queued"][0]["age_days"], 68)
            self.assertEqual(report["awaiting_promotion"][0]["draft_slug"], "budgets-before-dashboards")
            self.assertNotIn("Secret takeaway", rendered)

    def test_added_date_falls_back_to_filename_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = root / "items"
            items.mkdir()
            write_item(items, "2026-01-15-no-date.md", "queued", "not-a-date", "web-performance", TEMPLATE_BODY)

            records = BACKLOG.load_items(root)

            self.assertEqual(records[0]["added"], "2026-01-15")
            self.assertEqual(records[0]["slug"], "no-date")


class PromoteCheckTests(unittest.TestCase):
    def test_queued_template_item_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            items = Path(directory)
            path = write_item(items, "2026-01-01-queued.md", "queued", "2026-01-01", "web-performance", TEMPLATE_BODY)

            findings = {f["check"]: f["level"] for f in BACKLOG.promote_findings(path)}

            self.assertEqual(findings["status"], "FAIL")
            self.assertEqual(findings["draft_slug"], "FAIL")
            self.assertEqual(findings["after_learning"], "FAIL")
            self.assertEqual(findings["draft_angle"], "FAIL")
            self.assertEqual(findings["source"], "PASS")

    def test_done_item_with_slug_in_body_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            items = Path(directory)
            path = write_item(items, "2026-01-01-done.md", "done", "2026-01-01", "web-performance", FILLED_BODY)

            findings = BACKLOG.promote_findings(path)

            self.assertFalse(any(f["level"] == "FAIL" for f in findings))
            self.assertIn("budgets-before-dashboards", [f["detail"] for f in findings if f["check"] == "draft_slug"][0])

    def test_non_kebab_slug_and_missing_source_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            items = Path(directory)
            path = write_item(items, "2026-01-01-bad.md", "done", "2026-01-01", "web-performance", FILLED_BODY,
                              draft_slug="Not A Slug", source="")

            findings = {f["check"]: f["level"] for f in BACKLOG.promote_findings(path)}

            self.assertEqual(findings["draft_slug"], "FAIL")
            self.assertEqual(findings["source"], "FAIL")

    def test_cli_exit_code_reflects_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            items = Path(directory)
            ready = write_item(items, "2026-01-01-ready.md", "done", "2026-01-01", "web-performance", FILLED_BODY)
            blocked = write_item(items, "2026-01-02-blocked.md", "queued", "2026-01-02", "web-performance", TEMPLATE_BODY)

            with redirect_stdout(io.StringIO()):
                self.assertEqual(BACKLOG.main(["promote-check", str(ready)]), 0)
                self.assertEqual(BACKLOG.main(["promote-check", str(blocked)]), 1)


class OverlapTests(unittest.TestCase):
    def test_detects_near_duplicate_titles_from_posts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            posts = Path(directory) / "posts"
            posts.mkdir()
            (posts / "2025-12-01-budgets.md").write_text(
                "---\ntitle: Performance budgets before dashboards\n---\n\nbody\n", encoding="utf-8"
            )
            (posts / "2025-11-01-untitled-heading.md").write_text(
                "# Review loops that never merge\n\nbody\n", encoding="utf-8"
            )

            report = BACKLOG.overlap_report(
                ["Performance budgets, before the dashboards", "Caching strategy for edge functions"],
                BACKLOG.published_titles(posts),
                0.5,
            )

            first, second = report["results"]
            self.assertEqual(first["matches"][0]["title"], "Performance budgets before dashboards")
            self.assertGreaterEqual(first["best_score"], 0.5)
            self.assertEqual(second["matches"], [])
            self.assertEqual(report["published_count"], 2)

    def test_reads_one_title_per_line_file_and_ignores_stopwords(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory) / "titles.txt"
            index.write_text("How to measure review latency\n\nThe art of the retro\n", encoding="utf-8")

            titles = BACKLOG.published_titles(index)
            self.assertEqual(titles, ["How to measure review latency", "The art of the retro"])
            self.assertEqual(BACKLOG.tokens("How to measure review latency"), {"measure", "review", "latency"})


if __name__ == "__main__":
    unittest.main()
