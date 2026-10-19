#!/usr/bin/env python3
"""Create a private skill under an opaque random directory and expose it via an alias symlink."""
import argparse
import os
import re
import secrets
import sys


def normalize_alias(raw):
    alias = re.sub(r"[ _/]", "-", raw.lower())
    alias = re.sub(r"[^a-z0-9-]", "", alias)
    return alias.strip("-")


TEMPLATE = """---
name: {alias}
description: Private skill. Replace this line with the trigger phrases and an explicit not-for exclusion.
---

# {alias}

## Instructions

- This skill is private. Keep it out of any repository that is synced or published.
"""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("alias")
    p.add_argument("--private-root", default=os.environ.get("PRIVATE_SKILLS_ROOT"))
    p.add_argument("--skills-root", default=os.environ.get("SKILLS_ROOT"))
    a = p.parse_args(argv)
    if not a.private_root or not a.skills_root:
        print("private root and skills root are required (flags or environment profile values)", file=sys.stderr)
        return 2
    alias = normalize_alias(a.alias)
    if not alias:
        print("invalid alias: %r" % a.alias, file=sys.stderr)
        return 1
    private_root = os.path.expanduser(a.private_root)
    skills_root = os.path.expanduser(a.skills_root)
    link = os.path.join(skills_root, alias)
    if os.path.lexists(link) and not os.path.islink(link):
        print("path exists and is not a symlink: %s" % link, file=sys.stderr)
        return 1
    if os.path.islink(link) and os.path.realpath(link).startswith(os.path.realpath(private_root) + os.sep):
        print("alias already points at a private skill: %s" % link, file=sys.stderr)
        return 1
    target = os.path.join(private_root, secrets.token_hex(16))
    os.makedirs(target)
    os.makedirs(skills_root, exist_ok=True)
    with open(os.path.join(target, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(alias=alias))
    if os.path.islink(link):
        os.unlink(link)
    os.symlink(target, link)
    print("alias : %s\ntarget: %s\nlink  : %s" % (alias, target, link))
    return 0


if __name__ == "__main__":
    sys.exit(main())
