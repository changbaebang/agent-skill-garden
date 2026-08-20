#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


SECRET_KEY = re.compile(
    r"(?:^|[_-])(token|password|secret|cookie|api[_-]?key|private[_-]?key|credentials?)(?:$|[_-])",
    re.IGNORECASE,
)
VISIBILITIES = {"local", "private-repository", "team"}
VERIFY_CHECKS = {"page", "sitemap", "home"}


@dataclass
class Check:
    level: str
    subject: str
    message: str


def add(checks: list[Check], level: str, subject: str, message: str) -> None:
    checks.append(Check(level, subject, message))


def resolve_profile(explicit: Optional[Path], root: Path, home: Path) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    elif os.environ.get("AGENT_GARDEN_PROFILE"):
        candidates.append(Path(os.environ["AGENT_GARDEN_PROFILE"]))
    else:
        candidates.extend(
            [root / ".agent-garden" / "profile.ini", home / ".agent-garden" / "profile.ini"]
        )
    for candidate in candidates:
        path = Path(os.path.expandvars(str(candidate.expanduser())))
        if path.is_file():
            return path.resolve()
    return None


def expanded_path(value: str, profile: Path) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute():
        expanded = profile.parent / expanded
    return expanded.resolve()


def git_visibility(profile: Path, visibility: str, checks: list[Check]) -> None:
    result = subprocess.run(
        ["git", "-C", str(profile.parent), "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        add(checks, "PASS", "profile.visibility", "profile is outside a Git worktree")
        return

    root = Path(result.stdout.strip())
    relative = profile.relative_to(root)
    ignored = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", str(relative)],
        check=False,
    ).returncode == 0
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", str(relative)],
        check=False,
        capture_output=True,
    ).returncode == 0

    if visibility == "local":
        if ignored and not tracked:
            add(checks, "PASS", "profile.visibility", "local profile is ignored by Git")
        else:
            add(
                checks,
                "FAIL",
                "profile.visibility",
                "local profile is inside Git but is not safely ignored",
            )
    elif visibility == "private-repository":
        add(
            checks,
            "WARN",
            "profile.visibility",
            "profile may be tracked; confirm the remote repository is private",
        )
    else:
        add(
            checks,
            "WARN",
            "profile.visibility",
            "team profile is shareable only after personal-value review",
        )


def validate_jekyll(
    section: configparser.SectionProxy, profile: Path, checks: list[Check]
) -> None:
    required = ("repository", "drafts", "content_root", "branch", "base_url")
    missing = [key for key in required if not section.get(key, "").strip()]
    if missing:
        add(checks, "FAIL", "integration.blog", f"missing fields: {', '.join(missing)}")
        return

    repository = expanded_path(section["repository"], profile)
    drafts = expanded_path(section["drafts"], profile)
    content_root = Path(section["content_root"])

    if repository.is_dir() and (repository / ".git").exists():
        add(checks, "PASS", "integration.blog.repository", str(repository))
    else:
        add(checks, "FAIL", "integration.blog.repository", f"not a Git repository: {repository}")
    if drafts.is_dir():
        add(checks, "PASS", "integration.blog.drafts", str(drafts))
    else:
        add(checks, "FAIL", "integration.blog.drafts", f"directory not found: {drafts}")
    if content_root.is_absolute() or ".." in content_root.parts:
        add(checks, "FAIL", "integration.blog.content_root", "must be a safe relative path")
    elif (repository / content_root).is_dir():
        add(checks, "PASS", "integration.blog.content_root", str(content_root))
    else:
        add(
            checks,
            "FAIL",
            "integration.blog.content_root",
            f"directory not found under repository: {content_root}",
        )

    parsed = urlparse(section["base_url"])
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        add(checks, "PASS", "integration.blog.base_url", section["base_url"])
    else:
        add(checks, "FAIL", "integration.blog.base_url", "must be an HTTP or HTTPS URL")

    requested = {item.strip() for item in section.get("verify", "").split(",") if item.strip()}
    unknown = sorted(requested - VERIFY_CHECKS)
    if unknown:
        add(checks, "FAIL", "integration.blog.verify", f"unknown checks: {', '.join(unknown)}")
    else:
        add(checks, "PASS", "integration.blog.verify", ", ".join(sorted(requested)) or "none")


def validate_slack(section: configparser.SectionProxy, checks: list[Check]) -> None:
    workspace = section.get("workspace", "").strip()
    if workspace:
        add(checks, "PASS", "integration.slack.workspace", workspace)
    else:
        add(checks, "FAIL", "integration.slack.workspace", "workspace alias is required")
    add(
        checks,
        "WARN",
        "integration.slack.runtime",
        "connector visibility and authentication require an active host session",
    )


def validate(profile: Path) -> list[Check]:
    checks: list[Check] = []
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with profile.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error) as error:
        return [Check("FAIL", "profile", f"cannot parse profile: {error}")]

    for section_name in parser.sections():
        for key in parser[section_name]:
            if SECRET_KEY.search(key):
                add(checks, "FAIL", f"{section_name}.{key}", "secret-bearing keys are forbidden")

    if not parser.has_section("profile"):
        add(checks, "FAIL", "profile", "missing [profile] section")
        return checks
    profile_section = parser["profile"]
    if profile_section.get("schema_version", "").strip() == "1":
        add(checks, "PASS", "profile.schema_version", "1")
    else:
        add(checks, "FAIL", "profile.schema_version", "must equal 1")
    name = profile_section.get("name", "").strip()
    add(checks, "PASS" if name else "FAIL", "profile.name", name or "name is required")
    visibility = profile_section.get("visibility", "local").strip()
    if visibility not in VISIBILITIES:
        add(checks, "FAIL", "profile.visibility", f"unknown value: {visibility}")
    else:
        git_visibility(profile, visibility, checks)

    integrations = [name for name in parser.sections() if name.startswith("integration.")]
    if not integrations:
        add(checks, "FAIL", "integrations", "at least one integration section is required")
    for section_name in integrations:
        section = parser[section_name]
        try:
            enabled = section.getboolean("enabled", fallback=True)
        except ValueError:
            add(checks, "FAIL", section_name, "enabled must be true or false")
            continue
        if not enabled:
            add(checks, "PASS", section_name, "disabled")
            continue
        driver = section.get("driver", "").strip()
        if not driver:
            add(checks, "FAIL", section_name, "driver is required")
        elif driver == "jekyll-git":
            validate_jekyll(section, profile, checks)
        elif driver == "slack-host-connector":
            validate_slack(section, checks)
        else:
            add(checks, "WARN", section_name, f"no static doctor for driver: {driver}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Agent Skill Garden environment profile")
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    profile = resolve_profile(args.profile, args.root.expanduser().resolve(), args.home.expanduser().resolve())
    if profile is None:
        print("ERROR: no environment profile found", file=sys.stderr)
        return 1
    checks = validate(profile)
    counts = {level: sum(check.level == level for check in checks) for level in ("PASS", "WARN", "FAIL")}
    if args.json:
        print(json.dumps({"profile": str(profile), "checks": [asdict(check) for check in checks], "summary": counts}, indent=2))
    else:
        print(f"Profile: {profile}")
        for check in checks:
            print(f"{check.level:4} {check.subject}: {check.message}")
        print("Summary: " + " ".join(f"{level.lower()}={counts[level]}" for level in ("PASS", "WARN", "FAIL")))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
