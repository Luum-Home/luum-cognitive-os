---
description: Expand a rule from RULES-COMPACT.md — returns full rule body
argument-hint: <rule-key>
---

# Rules Expand: $ARGUMENTS

Load the full body of rule `$ARGUMENTS` from `rules/RULES-COMPACT.md` references.

Steps:
1. Read `rules/RULES-COMPACT.md` and locate the entry matching `$ARGUMENTS`.
2. Follow the reference key (typically `[rule-key]`) to the actual rule file under `rules/*.md`.
3. Display the full rule body, including:
   - Purpose / Rationale
   - Mandatory behaviors
   - Anti-patterns
   - Integration with other rules
   - Contextual trigger

If the key is not found, search related rule files:
```bash
grep -l -i "$ARGUMENTS" rules/*.md
```

**Why this exists**: `RULES-COMPACT.md` is a compressed index loaded at session start. Full rule bodies are ~1-5K tokens each. This command expands on-demand instead of loading all rules every session (ADR-044 context payload slimming).

## Common rule keys

- `adaptive-bypass`, `acceptance-criteria`, `agent-quality`, `adversarial-review`
- `confidence-gate`, `closed-loop-prompts`, `context-management`, `context-optimization`
- `decision-depth-gate`, `definition-of-done`, `dod-check`
- `error-learning`, `engram-organization`
- `model-routing`, `model-directive`
- `phase-aware-agents`, `prompt-quality`
- `resource-governance`, `result-management`, `responsiveness`
- `scope-proportionality`, `startup-protocol`
- `token-economy`, `trust-score`

Coordinate with ADR-043 if that ADR defines additional namespace conventions.
