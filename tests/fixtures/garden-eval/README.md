These synthetic run records were captured with the unmodified `skill_eval.py`
from commits `8483c0f` and `4f37789`, respectively, using `/usr/bin/python3 -c`
as a scripted runner. No model or private input was used. The capture files,
including their original hashes, are retained verbatim to exercise legacy
read/assessment compatibility independently of the current writer.

The intentionally reversed case order exercises the version 1 execution order.
The first record predates `selected_suite_sha256`; the second includes it.
