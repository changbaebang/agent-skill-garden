# Evidence rules

| Evidence | What it supports | Limitation |
| --- | --- | --- |
| installed `SKILL.md` | skill existed at inspection time | may not have existed during the request |
| explicit skill event | direct invocation | host-specific and may be absent |
| same-turn `SKILL.md` read | workflow was likely loaded | compacted logs can hide it |
| tool call before skill load | routing was late | some host actions may be omitted |
| repeated request samples | demand and trigger vocabulary | pasted text can create false demand |
| distinct invocation days | habit formation | small samples remain uncertain |

Report observation gaps separately from negative results.
