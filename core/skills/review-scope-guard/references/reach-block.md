# The reach block

The block is what a reviewer sees when opening the pull request. It carries the
counted reach, the dependent packages, and one row per scope question. A row
that does not apply stays in the table and says "not applicable"; a blank row
and a checked row are different things, and only the second one tells the next
reader that the question was asked.

## Template

```markdown
### Change reach

`path/to/shared/File.tsx` - what kind of shared surface (base style, default, global)
- consumers **N** - dependent packages M (names)
- which consumers are actually affected, and why the rest are not

| Question | Answer |
| --- | --- |
| Q1 how many places | N consumers, K affected; list read |
| Q2 scope fit | ticket scope vs diff scope; why the shared layer, or moved to the consumer |
| Q3 predicate name | old predicate -> new predicate, or not applicable |
| Q4 fix or mask | fix / mask; what an override removal would reveal; before and after values per platform |
| Q5 migration list | migrated / kept list with reasons, or not applicable (no new predicate) |
```

## Synthetic example

```markdown
### Change reach

`packages/layout/src/AppHeader.tsx` - shared base style
- consumers **13** - dependent packages 4 (account, catalog, checkout, storefront)
- 6 consumers render the header inside the embedded client and receive the inset;
  7 hide the header there and are unaffected

| Question | Answer |
| --- | --- |
| Q1 how many places | 13 consumers, 6 affected; list read, none should be excluded |
| Q2 scope fit | ticket names one screen, change is shared: mismatch. Kept shared because every embedded screen needs the same inset; stated in the description |
| Q3 predicate name | `isEmbeddedClient` replaced with `isFullscreenEmbed`, the condition the ticket title states; existing helper reused |
| Q4 fix or mask | fix; no override added |
| Q5 migration list | not applicable (no new predicate) |
```

## Recording it

Posting is an external write: present the block first and post only when the
user asks. Write the block to a file so the same text goes to the request and
to the chat.

**As a comment** (safe: nothing existing is replaced), with the hosting CLI
(`gh` shown; use the equivalent for another host):

```bash
gh pr comment "$pr" --body-file reach.md
```

**Appended to the description.** A description edit replaces the whole body.
Read the current body first, append, then write the combined text:

```bash
gh pr view "$pr" --json body --jq .body > body.md
printf '\n' >> body.md
cat reach.md >> body.md
gh pr edit "$pr" --body-file body.md
gh pr view "$pr" --json body --jq .body | diff -u body.md -
```

The read-back diff is the proof that nothing else in the description changed.

**No pull request yet.** Keep `reach.md` next to the work and say that it goes
into the description when the request is created. The skill is not finished
until the block is either posted or kept for that moment; a reach reported only
in chat is unrecorded.

## Keeping the block honest

- Quote the script's number, then the number of consumers actually affected,
  and say how the second was obtained (a list that was read, not a guess).
- If the counted number was inflated by a common symbol name, say so and give
  the corrected count with the sample paths that justified it.
- A Q4 row that reads "fix" must be able to name the cause that was removed. If
  the cause is unknown, write "mask" and name what the override hides.
- A Q5 row with kept call sites lists each one with its reason. "Kept, out of
  scope" is a reason only when the follow-up is named.
