# ADR-050 — Per-Skill Routing Policy

## Status

**Reserved** — stub. Builds on ADR-049 (Qwen primary cascade) + ADR-051
(Qwen agent loop) when both are mature. Not scheduled.

## Context

Today (post-ADR-049 Option B), sub-agents dispatched via `scripts/orchestrator.py`
or `lib/dispatch.py` use the cascade defined by the `--providers` flag or
`cognitive-os.yaml`. The cascade is uniform: **every skill uses the same
provider list**.

This is a coarse policy. In reality, skills have heterogeneous needs:

| Skill | Needs | Current policy | Better policy |
|---|---|---|---|
| `sdd-design` | Frontier reasoning, large context | Qwen first (may flip quality) | Claude primary, no fallback |
| `sdd-archive` | Cheap, mechanical summary | Qwen first | MiniMax (cheapest) |
| `security-audit` | Frontier, high-stakes | Qwen first (dangerous) | Claude only, NO fallback |
| `doc-sync` | Classification | Qwen first | OpenRouter free tier |
| `sdd-apply` (implementation) | Tool use, multi-step | Qwen first | Native Agent() (Claude Max) |

## Decision

**Deferred**. This ADR reserves the design space for per-skill routing
policies. When implemented, skills declare their routing requirements in
frontmatter and the dispatcher honors them.

### Proposed schema (reserved in skill frontmatter)

```yaml
---
name: sdd-design
model: opus                     # legacy Claude tier (still consumed by lib/qwen_provider model hint)
routing:                        # new — ADR-050 reserved schema
  tier: frontier | balanced | cheap
  need_vision: false
  need_long_context: true       # forces qwen3.6-plus OR claude-opus
  providers_preferred: [claude] # optional whitelist
  providers_excluded: [minimax] # optional blacklist
  fallback_on_rate_limit: true  # default true
  fallback_on_any_error: false  # default false — quality-sensitive skills
  budget_max_usd_per_call: 1.00
---
```

### Dispatch integration

`lib/dispatch.py::dispatch(..., skill_requirements={...})` already accepts
the parameter (reserved, ignored today). When ADR-050 lands:

- If `skill_requirements` is provided, the dispatcher overrides the
  default cascade based on preferences/exclusions.
- Budget caps are enforced pre-call.
- "Fallback on any error" policies change advance rules.

## Consequences

### Positive

- Per-skill quality/cost tuning without editing CLI args
- Prevents `sdd-design` from silently degrading to a weaker model
- Makes security-critical skills auditable (explicit provider lock)

### Negative

- More config surface (skill frontmatter grows)
- Routing engine must handle partial/conflicting requirements
- Testing matrix expands

### Neutral

- Skills without `routing:` frontmatter continue using default cascade
  (backward-compatible)

## Verification (when implemented)

- New tests in `tests/unit/test_skill_routing.py`
- `meta.skill_routing_coverage` validator contract — reports what
  percentage of skills declare explicit `routing:` vs use default
- Integration test: dispatch the same prompt under 3 different
  `routing.tier` settings, verify different provider selection

## Dependencies

- ADR-049 (providers cascade) — required
- ADR-051 (Qwen agent loop) — recommended (adds multi-step skill support)

## Related

- ADR-049 — current uniform cascade
- ADR-051 — agent loop (skill context injection → Phase 3)
- ADR-052 — benchmark harness (needed to auto-tune routing)
- ADR-053 — auto-optimizer (consumes routing metrics to re-tune policies)
- `lib/dispatch.py::dispatch(skill_requirements=...)` — reserved parameter
- `rules/llm-dispatch.md` — current uniform policy

## Open questions

1. Should `routing:` be in SKILL.md frontmatter OR in a separate
   `cognitive-os.yaml` `routing.skills.<name>` block? Frontmatter is
   self-contained but harder to override per-project.
2. How does `routing:` interact with `--providers` CLI flag? Flag wins?
   Frontmatter wins? Merge?
3. For budget caps: who decides when exceeded — raise error or fall
   through to cheaper provider? Makes the cascade direction non-obvious.

No scheduled work on this ADR until ADR-051 Phase 3 lands and we have
real per-skill quality data from benchmarks.
