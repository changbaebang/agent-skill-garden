---
name: blog-writing-workflow
description: >-
  Initializes a reusable blog profile from an existing blog, then writes,
  polishes, publication-checks, and explicitly publishes posts while preserving
  the author's observed voice and privacy boundaries. Use for initialize my
  blog, learn this blog's writing style, write a blog draft, polish this post,
  publish-check, 블로그 정보 초기화, 문체 분석, 블로그 초안, 글 다듬기, or
  블로그 발행. Drafting never authorizes publication.
---

# Blog writing workflow

Choose one mode: `initialize`, `draft`, `polish`, `publish-check`, or `publish`.
Do not silently advance from one mode to the next.

## Initialize

1. Confirm the blog source and the local profile destination. Prefer a local
   source repository because it exposes frontmatter, templates, and publication
   paths. A public URL can establish visible style only.
2. For a local Markdown source, run:

   ```bash
   python3 scripts/blog_inventory.py BLOG_SOURCE \
     --output .agent-blog/blog-inventory.json \
     --sample-size 12
   ```

3. Inspect the site configuration, templates, inventory, and a bounded sample
   containing both recent and structurally varied posts. Do not treat one post
   as the author's complete voice.
4. Create `.agent-blog/blog-profile.md` using
   [references/profile-contract.md](references/profile-contract.md). Separate
   measured observations, semantic inferences, and explicit author preferences.
5. Show the profile summary and uncertain inferences to the user. Apply their
   corrections before using it as a writing contract.

The inventory emits statistics and relative sample paths, never article body
text. Keep the generated profile and inventory local by default. Do not commit
them unless the user deliberately wants to share that profile.

## Draft or polish

1. Load the confirmed profile. If none exists, either initialize it or state
   which voice assumptions will remain unverified.
2. Gather the topic, intended audience, source material, factual claims, and
   disclosure boundary. Distinguish public facts from private context and
   personal interpretation.
3. Draft in the blog's configured format. Match stable tendencies such as
   sentence density, section rhythm, use of examples, and conclusion style;
   do not copy distinctive phrases from source posts.
4. Add the configured metadata, including an informative excerpt when the
   platform supports one. The excerpt should describe the article's value, not
   lead with a disclaimer.
5. For polishing, preserve the author's argument and level of certainty. Fix
   awkward wording, repetition, typos, broken structure, and unsupported leaps
   without flattening the voice into generic prose.
6. Write a local draft only when the user asked for a draft or file change.
   Return the path and a concise change summary. Do not publish.

## Publication check

Read [references/publication-check.md](references/publication-check.md), inspect
the final artifact, and return `READY` or `BLOCKED` with concrete evidence.
When a check cannot run, report it as unverified instead of treating it as a
pass.

## Publish

Publication is an external side effect and requires an explicit request in the
current conversation.

1. Re-read the final draft, profile, destination, and current repository state.
2. Preview the exact file, metadata, branch, commit, command, or API action that
   will publish the post.
3. Execute only the configured publication mechanism. Do not infer credentials,
   replace unrelated files, or broaden the requested change.
4. Read back the resulting repository or platform state and verify the public
   URL when one is available.
5. Keep the source draft until the published artifact is verified. On failure,
   stop with the draft intact and report the recovery point.
