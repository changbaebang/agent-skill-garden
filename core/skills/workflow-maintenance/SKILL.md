---
name: workflow-maintenance
description: >-
  Promotes reusable improvements from private or tool-specific workflows into
  this public canonical repository without copying and sanitizing an entire
  configuration tree. Use for update the public workflows, promote this skill,
  sync shared Claude and Codex skills, 공개판 반영, 공통 스킬 반영, or 워크플로
  동기화. Analyze candidates first; commit and push only when explicitly requested.
---

# Workflow maintenance

Treat private configurations as evidence, not as a publish source.

1. Identify the reusable decision, trap, procedure, or output shape.
2. Compare the relevant candidate with the canonical skill using
   `scripts/candidate_report.py`; do not bulk-copy a private tree.
3. Separate common behavior from host-specific invocation, paths, tools, and metadata.
4. Rewrite the common behavior directly in `core/skills` or `core/policies`.
5. Put genuinely host-specific guidance in the appropriate adapter.
6. Run the repository validator and a temporary project installation.
7. Test explicit and natural-language discovery in both supported hosts.
8. Commit or publish only when the user asks for those actions.

Do not preserve private identifiers as comments or examples. Do not rely on a
replacement script to make copied private content safe.

Read [references/promotion-contract.md](references/promotion-contract.md).
