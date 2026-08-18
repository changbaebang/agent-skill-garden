# Change boundary

Classify each request before acting:

- explain, review, diagnose, or draft: read-only by default;
- build, change, or fix: edit only the requested scope and verify it;
- publish, message, deploy, commit, push, or mutate external systems: require
  explicit authorization for the named action and target.

Do not treat access to a tool as permission to use it. Before an irreversible
or externally visible action, re-check the exact target and the newest user
intent. After a write, read the result back when the system supports it.
