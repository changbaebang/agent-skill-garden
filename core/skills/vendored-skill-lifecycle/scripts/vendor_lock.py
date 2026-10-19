#!/usr/bin/env python3
"""Per-ticket vendored skill plugins: lock file, thin wrapper, teardown.

Layout under --root, the host's personal skills root:

  vendor/<repository>/<plugin-path>/   the clone, read in place, never auto-loaded
  vendor-lock.json                     the only record of active installs
  skills/<plugin>-vendor/SKILL.md      thin wrapper, present only while the ticket is open

The script performs no network access and never deletes a clone. Clone first,
then install. Exit codes: 0 done, 1 refused, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

LOCK_FILE = "vendor-lock.json"
VENDOR_DIR = "vendor"
SKILLS_DIR = "skills"
WRAPPER_SUFFIX = "-vendor"
MARKER = "Managed by vendored-skill-lifecycle. Do not edit by hand; run the teardown instead."
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TICKET_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SKIP_DIRS = {"node_modules", "__pycache__", "dist", "build"}
DOCUMENT_DEPTH = 3


class LifecycleError(Exception):
    """A refused operation. The message is written for the user."""


# ---- paths -------------------------------------------------------------------


def expand(text: str) -> Path:
    return Path(os.path.expandvars(text)).expanduser()


def shorten_home(path: Path) -> str:
    """Store paths relative to the home directory so a lock survives a machine move."""
    try:
        return "~/" + path.relative_to(Path.home()).as_posix()
    except ValueError:
        return path.as_posix()


def repository_name(source: str) -> str:
    tail = source.rstrip("/").rsplit("/", 1)[-1]
    tail = tail.rsplit(":", 1)[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    if not tail:
        raise LifecycleError(f"cannot derive a repository name from source {source!r}")
    return tail


def nearest_existing(path: Path) -> Path:
    current = path
    while not current.exists() and current.parent != current:
        current = current.parent
    return current if current.is_dir() else current.parent


# ---- git (optional: a missing git means "unknown", never a failure) -----------


def run_git(cwd: Path, *args: str) -> Optional[str]:
    if shutil.which("git") is None:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_revision(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.is_dir():
        return None
    return run_git(path, "rev-parse", "HEAD")


def tracking_warnings(paths: List[Path]) -> List[str]:
    """One warning per path that an enclosing Git work tree would track."""
    warnings: List[str] = []
    for path in paths:
        anchor = nearest_existing(path)
        toplevel = run_git(anchor, "rev-parse", "--show-toplevel")
        if toplevel is None:
            continue
        if run_git(anchor, "check-ignore", "-q", str(path)) is None:
            warnings.append(
                f"{shorten_home(path)} is inside the Git work tree {toplevel} and is not "
                "ignored; if that is a project repository, stop and choose another root"
            )
    return warnings


# ---- lock --------------------------------------------------------------------


def lock_path(root: Path) -> Path:
    return root / LOCK_FILE


def read_lock(root: Path) -> Dict[str, Any]:
    path = lock_path(root)
    if not path.exists():
        return {"installs": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LifecycleError(f"cannot read {path}: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("installs"), list):
        raise LifecycleError(f"{path} must be an object with an 'installs' array")
    return data


def write_lock(root: Path, lock: Dict[str, Any]) -> None:
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---- wrapper -----------------------------------------------------------------


def plugin_documents(plugin_dir: Path) -> List[Path]:
    """Markdown files up to three levels deep, skipping hidden and build directories."""
    documents: List[Path] = []
    base_depth = len(plugin_dir.parts)
    for current, dirnames, filenames in os.walk(plugin_dir):
        depth = len(Path(current).parts) - base_depth
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".") and depth + 1 < DOCUMENT_DEPTH
        )
        for name in filenames:
            if name.lower().endswith(".md"):
                documents.append((Path(current) / name).relative_to(plugin_dir))
    return sorted(documents, key=lambda item: item.as_posix())


def render_wrapper(entry: Dict[str, Any], documents: List[Path]) -> str:
    plugin = entry["plugin"]
    ticket = entry["ticket"]
    vendor_dir = entry["vendor_dir"]
    revision = entry.get("revision") or "unknown"
    rows = "\n".join(
        f"| `{document.as_posix()}` | `{vendor_dir}/{document.as_posix()}` |" for document in documents
    ) or "| (no markdown documents found) | |"
    return (
        "---\n"
        f"name: {entry['wrapper_skill']}\n"
        "description: >-\n"
        f"  Thin wrapper for the vendored plugin {plugin} while ticket {ticket} is open.\n"
        "  Read its procedures from the vendor path listed inside; nothing is copied\n"
        f"  here. Use for {plugin} steps, {plugin} procedure, or {ticket} plugin. Tear\n"
        "  down with vendored-skill-lifecycle when the ticket closes.\n"
        "---\n"
        "\n"
        f"# {plugin} (vendored for {ticket})\n"
        "\n"
        f"{MARKER}\n"
        "\n"
        "| Field | Value |\n"
        "| --- | --- |\n"
        f"| Source | `{entry['source']}` |\n"
        f"| Plugin path | `{entry['plugin_path'] or '.'}` |\n"
        f"| Revision | `{revision}` |\n"
        f"| Installed | {entry['installed_at']} |\n"
        f"| Read in place | `{vendor_dir}` |\n"
        "\n"
        "## Follow the plugin\n"
        "\n"
        "1. When the plugin names a slash command, open the matching document below\n"
        "   and follow it. Do not infer behavior from the command name.\n"
        "2. The specification the ticket links to outranks the plugin when they\n"
        "   disagree.\n"
        "3. Nothing under the vendor directory is copied into a project repository.\n"
        "\n"
        "## Documents\n"
        "\n"
        "| Document | Path |\n"
        "| --- | --- |\n"
        f"{rows}\n"
        "\n"
        "## When the ticket closes\n"
        "\n"
        f"Run the vendored-skill-lifecycle teardown for `{ticket}`. It removes this\n"
        "wrapper and the lock entry and leaves the clone for you to remove after\n"
        "confirmation.\n"
    )


def wrapper_dir(root: Path, wrapper: str) -> Path:
    return root / SKILLS_DIR / wrapper


def is_managed(wrapper_path: Path) -> bool:
    try:
        return MARKER in (wrapper_path / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        return False


# ---- validation --------------------------------------------------------------


def validate_name(value: str, what: str) -> str:
    if not NAME_PATTERN.match(value) or len(value) > 64:
        raise LifecycleError(f"{what} must be lowercase hyphen-case, at most 64 characters (got {value!r})")
    return value


def validate_ticket(value: str) -> str:
    if not TICKET_PATTERN.match(value):
        raise LifecycleError(f"ticket must be a short identifier without spaces (got {value!r})")
    return value


def age_days(installed_at: Optional[str], now: datetime) -> Optional[int]:
    if not installed_at:
        return None
    try:
        then = datetime.fromisoformat(installed_at)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.astimezone()
    return max(0, (now - then).days)


# ---- commands ----------------------------------------------------------------


def command_install(args: argparse.Namespace) -> int:
    root = expand(args.root).resolve()
    plugin = validate_name(args.plugin, "plugin")
    ticket = validate_ticket(args.ticket)
    wrapper = validate_name(args.wrapper or f"{plugin}{WRAPPER_SUFFIX}", "wrapper")
    plugin_path = (args.plugin_path or "").strip("/")
    if args.vendor_dir:
        vendor_dir = expand(args.vendor_dir).resolve()
    else:
        vendor_dir = (root / VENDOR_DIR / repository_name(args.source) / plugin_path).resolve()
    if not vendor_dir.is_dir():
        raise LifecycleError(
            f"plugin directory not found: {vendor_dir}\n"
            "clone the source into the vendor area first; this script performs no network access"
        )

    lock = read_lock(root)
    for existing in lock["installs"]:
        if existing.get("plugin") == plugin or existing.get("wrapper_skill") == wrapper:
            raise LifecycleError(
                f"{plugin} is already installed for ticket {existing.get('ticket')} "
                f"(wrapper {existing.get('wrapper_skill')}); tear it down first"
            )
    target = wrapper_dir(root, wrapper)
    if target.exists() or target.is_symlink():
        reason = (
            "an orphaned managed wrapper; run teardown --plugin to remove it"
            if is_managed(target)
            else "it was not written by this script"
        )
        raise LifecycleError(f"refusing to overwrite {target}: {reason}")

    entry = {
        "plugin": plugin,
        "source": args.source,
        "plugin_path": plugin_path,
        "vendor_dir": shorten_home(vendor_dir),
        "revision": git_revision(vendor_dir),
        "ticket": ticket,
        "wrapper_skill": wrapper,
        "installed_at": args.installed_at or datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    documents = plugin_documents(vendor_dir)
    warnings = tracking_warnings([root / VENDOR_DIR, lock_path(root), target])

    if not args.dry_run:
        lock["installs"].append(entry)
        write_lock(root, lock)
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text(render_wrapper(entry, documents), encoding="utf-8")

    print(f"install: plugin={plugin} ticket={ticket}")
    print(f"  clone     : {entry['vendor_dir']}")
    print(f"  revision  : {entry['revision'] or 'unknown (not a Git checkout)'}")
    print(f"  wrapper   : {shorten_home(target)}")
    print(f"  documents : {len(documents)}")
    print(f"  lock      : {shorten_home(lock_path(root))}")
    for warning in warnings:
        print(f"WARN {warning}")
    if args.dry_run:
        print("dry run: nothing written")
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = expand(args.root).resolve()
    lock = read_lock(root)
    now = datetime.now().astimezone()
    rows: List[Dict[str, Any]] = []
    for entry in lock["installs"]:
        vendor_dir = expand(entry["vendor_dir"]).resolve() if entry.get("vendor_dir") else None
        wrapper = wrapper_dir(root, entry.get("wrapper_skill", ""))
        current = git_revision(vendor_dir)
        problems: List[str] = []
        if vendor_dir is None or not vendor_dir.is_dir():
            problems.append("clone missing")
        if not wrapper.exists():
            problems.append("wrapper missing")
        elif not is_managed(wrapper):
            problems.append("wrapper not managed by this script")
        recorded = entry.get("revision")
        if recorded and current and recorded != current:
            problems.append("clone moved off the recorded revision")
        rows.append(
            {
                "plugin": entry.get("plugin"),
                "ticket": entry.get("ticket"),
                "wrapper_skill": entry.get("wrapper_skill"),
                "vendor_dir": entry.get("vendor_dir"),
                "revision": recorded,
                "installed_at": entry.get("installed_at"),
                "age_days": age_days(entry.get("installed_at"), now),
                "problems": problems,
            }
        )

    if args.json:
        print(json.dumps({"lock": shorten_home(lock_path(root)), "installs": rows}, indent=2))
        return 0
    if not rows:
        print(f"no active vendored installs ({shorten_home(lock_path(root))})")
        return 0
    for row in rows:
        age = "unknown age" if row["age_days"] is None else f"{row['age_days']}d"
        state = ", ".join(row["problems"]) or "ok"
        print(f"{row['plugin']}  ticket={row['ticket']}  wrapper={row['wrapper_skill']}  {age}  {state}")
        print(f"  clone: {row['vendor_dir']}  revision: {row['revision'] or 'unknown'}")
    print(f"lock: {shorten_home(lock_path(root))}")
    return 0


def command_teardown(args: argparse.Namespace) -> int:
    root = expand(args.root).resolve()
    lock = read_lock(root)
    selected = [
        entry
        for entry in lock["installs"]
        if (args.ticket and entry.get("ticket") == args.ticket)
        or (args.plugin and entry.get("plugin") == args.plugin)
    ]
    if not selected:
        wanted = args.ticket or args.plugin
        raise LifecycleError(f"no active install matches {wanted!r}; run status to see the lock")
    remaining = [entry for entry in lock["installs"] if entry not in selected]

    for entry in selected:
        wrapper = wrapper_dir(root, entry["wrapper_skill"])
        if (wrapper.exists() or wrapper.is_symlink()) and not is_managed(wrapper):
            raise LifecycleError(
                f"refusing to delete {wrapper}: it was not written by this script (marker missing)"
            )

    if not args.dry_run:
        for entry in selected:
            wrapper = wrapper_dir(root, entry["wrapper_skill"])
            if wrapper.is_symlink():
                wrapper.unlink()
            elif wrapper.is_dir():
                shutil.rmtree(wrapper)
        lock["installs"] = remaining
        write_lock(root, lock)

    verb = "would remove" if args.dry_run else "removed"
    for entry in selected:
        wrapper = wrapper_dir(root, entry["wrapper_skill"])
        print(f"{verb} wrapper {shorten_home(wrapper)} and the lock entry for {entry['ticket']}")
        repository = repository_name(entry["source"])
        users = [other for other in remaining if repository_name(other["source"]) == repository]
        if users:
            print(f"  clone kept: {entry['vendor_dir']} (still used by {len(users)} other install(s))")
        else:
            print(f"  clone kept: {entry['vendor_dir']} (no remaining install uses it; remove after the user confirms)")
    if args.dry_run:
        print("dry run: nothing written")
    return 0


# ---- entry point -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install, inspect, and tear down per-ticket vendored skill plugins."
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root",
        required=True,
        help="the host's personal skills root; vendor/, vendor-lock.json and skills/ live under it",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", parents=[common], help="record a lock entry and write the thin wrapper")
    install.add_argument("--plugin", required=True, help="plugin name, lowercase hyphen-case")
    install.add_argument("--source", required=True, help="repository URL or path the plugin was cloned from")
    install.add_argument("--ticket", required=True, help="the ticket this install belongs to")
    install.add_argument("--plugin-path", default="", help="path of the plugin inside the clone")
    install.add_argument("--vendor-dir", help="explicit plugin directory; defaults to root/vendor/<repository>/<plugin-path>")
    install.add_argument("--wrapper", help="wrapper skill name; defaults to <plugin>-vendor")
    install.add_argument("--installed-at", help="ISO timestamp to record instead of now")
    install.add_argument("--dry-run", action="store_true")
    install.set_defaults(handler=command_install)

    status = subparsers.add_parser("status", parents=[common], help="list active installs and drift")
    status.add_argument("--json", action="store_true")
    status.set_defaults(handler=command_status)

    teardown = subparsers.add_parser("teardown", parents=[common], help="remove the wrapper and lock entry; keep the clone")
    selector = teardown.add_mutually_exclusive_group(required=True)
    selector.add_argument("--ticket")
    selector.add_argument("--plugin")
    teardown.add_argument("--dry-run", action="store_true")
    teardown.set_defaults(handler=command_teardown)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except LifecycleError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
