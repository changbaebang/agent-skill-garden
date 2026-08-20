# Promotion contract

A candidate is ready only when:

- every part is classified as core workflow, integration recipe, environment
  profile value, or private extension;
- mixed candidates are split instead of embedding local values in skill bodies;
- the workflow is useful outside its original organization or repository;
- examples are synthetic and preserve the decision, not the private nouns;
- canonical frontmatter contains only portable keys;
- tool paths and invocation syntax are isolated in adapters;
- write authority remains explicit;
- deterministic scripts have been executed successfully;
- public-safety and structure validation pass;
- both supported hosts can discover the skill.

The classification result should answer:

| Question | Destination |
| --- | --- |
| Is this a reusable decision or safety boundary? | `core` |
| Is this reusable behavior for a service or engine? | `integrations` |
| Is this an actual path, repository, branch, URL, workspace, or alias? | local profile |
| Does it require organization-only policy or vocabulary? | private extension |
