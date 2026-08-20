# Blog workflow guide

[English](blog-workflow.md) | [한국어](blog-workflow.ko.md)

`blog-writing-workflow` lets each user teach an agent how their own blog works
without publishing that blog's content or voice profile into this repository.
The reusable skill is public; the generated profile stays with the user.

## 1. Install the skill

Preview a project-scoped installation:

```bash
./scripts/install.sh \
  --target all \
  --scope project \
  --root path/to/blog \
  --skill blog-writing-workflow
```

Review the plan, then repeat it with `--apply`. Restart or open a fresh agent
session so the host can discover the new skill.

## 2. Initialize the blog once

Ask naturally:

> Initialize this blog's metadata, writing style, and publication profile. Keep
> the generated profile local and show me uncertain inferences before using it.

The workflow will:

1. inventory Markdown structure without storing article body text;
2. inspect a bounded set of recent and structurally varied posts;
3. distinguish measured patterns from inferred style and stated preferences;
4. write `.agent-blog/blog-profile.md` for the author to review.

The profile is not a permanent personality model. Update it when the site
format, audience, or author's preferences change materially.

## 3. Use the profile for daily writing

Example requests:

> Draft a post from these notes using my confirmed blog profile. Do not publish.

> Polish this draft without changing my argument or level of certainty.

> Run the publication check and tell me only what still blocks publication.

> Publish the checked draft using this blog's configured mechanism, then verify
> the resulting public page.

Drafting and checking never authorize publishing. Publishing requires an
explicit request and must preserve the source draft until the result is read
back successfully.

## 4. Decide what to share

Keep `.agent-blog/` untracked for a personal profile. A team or publication may
choose to commit a reviewed profile when it contains only shared editorial
rules. Never include credentials, private source conversations, internal URLs,
or copied article bodies.

The profile captures tendencies and decisions. It should help an agent remain
consistent without turning every author into the same generic voice or copying
distinctive phrases from earlier posts.
