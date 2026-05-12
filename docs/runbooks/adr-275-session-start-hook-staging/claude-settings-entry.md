# Claude Code `.claude/settings.json` — SessionStart entry to add

Locate the existing `hooks.SessionStart[0].hooks[]` array in
`.claude/settings.json` and APPEND this entry:

```json
{
  "type": "command",
  "command": "python3 \"$CLAUDE_PROJECT_DIR/scripts/cos-session-start-projector\""
}
```

Place it AFTER the existing `session-init.sh` entry so the projection
surfaces after the project state has finished loading.

The projector exits 0 always and writes to stderr — it is non-blocking
and cannot fail the SessionStart chain.

To disable temporarily:
```bash
export COS_PROJECTOR_DISABLED=1
```
(The script honors this env if you wrap the command in a check.)

Roll back: remove the appended entry.
