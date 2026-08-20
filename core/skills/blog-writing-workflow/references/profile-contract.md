# Blog profile contract

The profile is a local, reviewable writing contract. It records how this blog
works without embedding article bodies, credentials, private conversations, or
organization-specific data.

## Recommended location

```text
.agent-blog/
  blog-inventory.json
  blog-profile.md
```

Add the directory to the consuming project's ignore rules when the profile is
personal. Commit a profile only when its owner intentionally wants to share the
editorial contract.

## Required sections

### Source and confidence

- source kind: local repository or public site;
- sample size and selection boundary;
- profile revision date or source revision;
- evidence labels: `measured`, `inferred`, or `author-confirmed`;
- gaps that could not be observed.

### Site contract

- content root and draft destination;
- publication platform or repository convention;
- filename and date rules;
- required frontmatter fields and their value shapes;
- excerpt, tag, category, image, and canonical URL conventions;
- available validation and preview commands.

Keep paths relative to the blog root where possible. Never record secrets or
credential locations.

### Audience and purpose

- primary readers and assumed knowledge;
- recurring subject areas;
- what a useful post should let the reader understand or do;
- topics or details that should remain private.

### Voice

Record tendencies, not copied phrases:

- language, formality, and point of view;
- sentence and paragraph density;
- directness, humor, uncertainty, and emotional range;
- preferred technical depth and explanation style;
- how claims, examples, caveats, and opinions are separated;
- expressions or tones the author wants to avoid.

### Structure

- title tendencies;
- opening pattern;
- heading depth and typical section rhythm;
- use of lists, quotations, code, images, and links;
- conclusion pattern and call-to-action policy.

### Safety and publication

- anonymization and disclosure rules;
- facts that require a source or fresh verification;
- publication mechanism and explicit approval boundary;
- post-publication verification and draft cleanup rule.

## Initialization result

End the profile with:

- confirmed rules;
- uncertain inferences awaiting review;
- a short checklist the agent can apply to every draft.

The author can override every inferred rule. Refresh the profile when the blog's
format or voice changes materially; do not rebuild it for every post.
