# Updating the description

Editing the description is a write. Do it only when the user asks for it, and
only for the metadata sections the repository's template defines for that
purpose, such as references, risk tier, impact analysis, verification, and the
change summary. Everything else stays byte-stable.

## Gather

```bash
gh pr view "$pr" --json title,body,baseRefName,headRefName,files,commits
git fetch origin "$base" "$head" 2>/dev/null || true
git diff "origin/$base...origin/$head" --stat
```

Write the change-summary bullets from the diff and commit messages. Remove
vague or opinion lines; keep facts a reviewer can check.

Save the current description before changing it:

```bash
gh pr view "$pr" --json body --jq .body > body.md
```

## Section rules

- Match sections by heading text. Keep the heading line as it is in the
  description.
- Replace only the content under a matched heading, up to the next heading of
  the same or a higher level.
- Insert a missing section at its place in the template's order, after the
  nearest earlier section that exists.
- Keep template comments that live under the heading; they are the reviewers'
  instructions.
- Drop exact duplicate bullets inside the replaced section. Merge bullets that
  say the same thing in different words by hand, and say so.
- Keep one blank line after the heading and one before the next heading.
- Run twice and expect the same result. If the second run changes anything,
  the input is not idempotent and must be fixed before applying.

## Write the replacement sections

Put each section to change in one markdown file, heading first:

```markdown
### References

- Ticket: full tracker key with link when the base URL is known
- Specification: path or link, or none

### Risk tier

Tier label from the repository's scale
Rationale: one or two sentences specific to this change.

### Verification

- Platforms exercised
- Core scenarios and their outcome
- Not exercised, and the follow-up for it
```

Then build the new body:

```bash
python3 scripts/pr_body_sections.py upsert \
  --body body.md \
  --sections sections.md \
  --order "References" "Risk tier" "Impact" "Verification" "Changes" \
  > body.new.md
diff -u body.md body.new.md
```

The order list is the template's order. The diff is what the user approves.

## Apply once, then read back

```bash
scripts/pr_body_patch.sh "$pr" body.new.md
gh pr view "$pr" --json body --jq .body | diff -u body.new.md -
```

The helper patches through the hosting CLI. If a token environment variable is
set but rejected, it retries with the CLI's stored login and reports which one
was used. It never prints a token.

## Report

```markdown
### Apply result
- applied: yes | no
- sections updated: ...
- authentication used: environment token | stored login | failed
- reason if not applied: ...

### Sections as applied
(the final markdown of the updated sections, in order)
```

Do not report an intended value as applied. Either the read-back matches or the
apply failed.
