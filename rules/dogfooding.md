# Dogfooding Rule

## Rule: Use Cognitive OS to Build Cognitive OS

luum-agent-os MUST use its own tools to develop itself. This is "eating our own dog food" — the OS builds the OS.

### Self-Hosting Requirement

The project MUST be self-installed. When Claude Code works on this repo:
- `.claude/rules/` symlinks to `rules/` — all 55 rules are active
- `.claude/settings.json` references `hooks/` — all hooks run on this project
- Skills in `skills/` are available via `/invoke`
- Any substantial change goes through SDD (the pipeline we build IS the pipeline we use)

If you're working on cognitive-os and the rules/hooks aren't loaded, something is broken. Fix it first.

### Pipeline Requirement

Substantial changes follow the complete SDD dependency chain:

```
explore -> propose -> spec -> design -> tasks -> apply -> verify -> archive
```

Each phase produces artifacts stored in Engram (or openspec). The verify-apply retry loop applies: up to 3 retries on CRITICAL failures before escalating to a human.

### What Counts as Substantial

| Change Type | Substantial? | Requires SDD? |
|-------------|-------------|---------------|
| New skill | Yes | Yes |
| New hook | Yes | Yes |
| New infrastructure (squads, backends) | Yes | Yes |
| Modifications to SDD phases | Yes | Yes |
| New integrations (tools, APIs) | Yes | Yes |
| New rule with behavioral enforcement | Yes | Yes |
| Cross-cutting refactors (3+ files) | Yes | Yes |

### Exemptions (no SDD needed)

| Change Type | Why Exempt |
|-------------|-----------|
| Typo fixes | Zero behavioral impact |
| Config tweaks | Single-value changes to existing config |
| Dependency bumps | Version-only changes |
| Test-only changes | No production behavior modified |
| Documentation typos | No behavioral impact |
| Urgent broken-hook fixes | Time-critical; document post-facto |

### Enforcement

- **Phase reconstruction**: WARN if a substantial change skips SDD
- **Phase stabilization**: BLOCK substantial changes without SDD artifacts
- **Phase production**: BLOCK + require human approval for any exception

### Rationale

Every feature built through SDD tests the pipeline itself. Bugs in explore, propose, spec, design, tasks, apply, or verify are caught by the team that owns them — before external users hit them. Improvements compound: a better spec phase produces better specs for the next feature, which produces better implementations.

### Self-Hosting Checklist

The `self-install.sh` hook runs automatically at SessionStart and handles all of this:
- Symlinks ALL `rules/*.md` to `.claude/rules/` (adds new, removes stale)
- Verifies `.claude/settings.json` exists with hook references
- Verifies `cognitive-os.yaml` exists
- Creates `.cognitive-os/sessions/` if missing

The hook only activates inside the luum-agent-os repo itself (detects `hooks/self-install.sh` relative to project root). In other projects where cognitive-os is installed, it silently exits.

If auto-sync reports issues, check the SessionStart output for the status line:
- `Self-hosting: OK (55 rules, 57 hooks synced)` — everything is in order
- `Self-hosting: FIXED (added 2 new rules)` — new rules were auto-linked

### Relationship to Other Rules

- Complements `cognitive-os-changes.md` (plan-first for OS modifications)
- Complements `plan-first.md` (general plan requirement)
- This rule is stricter: mandates full SDD pipeline + self-hosting verification
