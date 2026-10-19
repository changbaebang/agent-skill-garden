# destructive-push-guard

A Claude Code `PreToolUse` hook for the `Bash` tool. It denies destructive
`git push` variants while leaving plain `git push` allowed.

## What it blocks

- `--force`, `-f`, `--force-with-lease`, `--force-if-includes`
- `--mirror`
- `--delete`, `-d`
- refspec deletion (a push whose refspec starts with a colon)
- forced refspec (a push whose refspec starts with a plus sign)

It only inspects segments where `git push` is the command actually being run
(start of line or after `;`, `&&`, `||`, `|`, `(`), so text such as a grep for
a force-push string is not flagged. Everything else exits 0 with no output.

## Wiring

Requires `bash`, `jq`, and `grep` with `-E`. Copy the script to
`~/.claude/hooks/`, make it executable, then add this to
`~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$HOME/.claude/hooks/guard-git-push.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

Quick check: pipe `{"tool_input":{"command":"<a push with a force flag>"}}`
into the script and expect a JSON deny; a plain push prints nothing.

## Limits

The match is a text heuristic, not a git parser: aliases, `git -C dir push`,
and commands built inside scripts are not caught. Treat it as a guardrail, not
a security boundary. It is advisory for other hosts: only hosts that support
Claude Code style `PreToolUse` hooks enforce it; elsewhere, use it as a
reference for an equivalent pre-command check.
