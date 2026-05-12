# Codex `.codex/hooks.json` — SessionStart entry to add

If `.codex/hooks.json` exists, locate `hooks.SessionStart` (array) and
APPEND this entry:

```json
{
  "command": ["python3", "scripts/cos-session-start-projector"],
  "description": "ADR-275 session-start projector"
}
```

If `.codex/hooks.json` does not yet exist, create it with:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": ["python3", "scripts/cos-session-start-projector"],
        "description": "ADR-275 session-start projector"
      }
    ]
  }
}
```

Codex resolves commands relative to the project root; no
`$CLAUDE_PROJECT_DIR` substitution needed.
