# Release-blocking inclusion gate

Include:

- irreversible or broad data corruption;
- deterministic crash or outage on a critical path;
- authorization or authentication bypass;
- exploitable secret or personal-data exposure;
- non-terminating work that exhausts resources;
- a primary business flow becoming unusable without a safe fallback.

Exclude unless impact evidence raises severity:

- style, naming, formatting, and preference;
- theoretical races with no reachable trigger;
- localized degraded UX with a working fallback;
- pre-existing behavior unchanged by the diff;
- missing tests without an identified regression.
