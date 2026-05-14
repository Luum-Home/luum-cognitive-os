<!-- SCOPE: os-only -->
<!-- TIER: 2 -->
# Reinvention Prevention

## Rule: Check Before Building

Before creating ANY new `lib/`, `hook`, or `skill`, run the reinvention guard:

```python
from lib.reinvention_guard import ReinventionGuard
guard = ReinventionGuard()
results = guard.check("what you're about to build", keywords=["keyword1", "keyword2"])
print(guard.format_report(results))
```

## Check Order (mandatory)

1. **Upstream submodules** — search `.claude/plugins/hermes-agent` and `.claude/plugins/pi-mono` first
2. **Our own `lib/`** — check if we already have a partial implementation
3. **Adoption registry** — `.cognitive-os/adoption-registry.yaml` for prior decisions
4. **Competitive docs** — `docs/08-References/root/competitive-landscape.md` for evaluated tools

## Decision Ladder

| Existing code | Action |
|---|---|
| Exact match | **adopt** — use it directly, add to registry |
| Similar match | **adapt** — port the pattern, document differences |
| Evaluated tool | **reference** — use its architecture, not its code |
| Nothing found | **build** — but document your research |

## Document Every Decision

Add an entry to `.cognitive-os/adoption-registry.yaml`:

```yaml
- id: my-feature-name
  source: hermes-agent          # or pi-mono, cos-lib, docs
  source_file: agent/thing.py
  our_file: lib/thing.py
  adapted: true
  adaptation_notes: "why we adapted rather than copied"
  adopted_date: "YYYY-MM-DD"
```

## Hook

`hooks/reinvention-check.sh` (PreToolUse) fires automatically before agent launches
that mention creating new lib/hook/skill files. Advisory only (exit 0).

## Motivation

137 commits in 5 days → features built without checking Hermes, Pi, or evaluated tools.
The cost: redundant implementations of things like context compressors, file-mutation
queues, and resilience patterns that upstream had already solved.

## Contextual Trigger

- When work relates to Reinvention Prevention.
