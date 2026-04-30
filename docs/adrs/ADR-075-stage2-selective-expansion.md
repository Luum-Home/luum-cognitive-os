# ADR-075: Stage 2 Selective Expansion — Tier-Based Ref-Key Filtering

**Status**: Accepted  
**Date**: 2026-04-30  
**Engram topic**: `cos/stage2-selective-expansion-plan`  
**Precedes**: ADR-027 Phase 2 (ref-key loader), ADR-074 (Tier-0 learning-loop closure)

---

## Context

ADR-027 Phase 2 introduced `expand()` in `lib/ref_key_loader.py` which inlines
`[ref-key]` markers with full rule file content. `hooks/inject-phase-context.sh`
calls `expand(buf, max_depth=1)` on every `PreToolUse[Agent]` event, feeding
`RULES-COMPACT.md` as input.

Measured cost (2026-04-30):

| Mode | Chars | Tokens (est.) |
|------|-------|---------------|
| Input (RULES-COMPACT alone) | 8,561 | ~2,140 |
| Full expansion (no filter) | 428,886 | ~107,221 |
| Tier-0 only (`{0}`) | 63,067 | ~15,766 |
| Tier-0 + Tier-1 default (`{0,1}`) | 408,832 | ~102,208 |

Expanding all 112 rules on every agent call costs ~107K tokens — roughly 50× the
input size. This inflates context cost, hits the 10K-char `additionalContext`
truncation cap in Claude Code, and drowns critical rules in noise.

---

## Decision

Implement **tier-based selective expansion** (Option B from the plan):

### Rule classification

Every `rules/*.md` file carries a `<!-- TIER: N -->` comment on line 1:

- **Tier-0** (always-on, ~9 rules): mandatory for all agents — `acceptance-criteria`,
  `agent-quality`, `agent-escalation`, `closed-loop-prompts`, `definition-of-done`,
  `phase-aware-agents`, `trust-score`, `RULES-COMPACT`, `ROADMAP`.
- **Tier-1** (default, ~95 rules): expanded unless operator opts down to Tier-0 only.
- **Tier-2** (on-demand, ~8 rules): never expanded by default — integrations and
  ecosystem tools (`aguara-integration`, `e2b-integration`, `hcom-integration`,
  `parry-integration`, `repomix-integration`, `tero-integration`, `trailofbits-skills`,
  `context7-auto-trigger`).

Rules without `<!-- TIER: N -->` frontmatter default to Tier-1.

### API changes

`expand()` in `lib/ref_key_loader.py` gains a new `tier_filter: set[int] | None`
parameter. When `None` (default), all rules expand — full backward compatibility.
When a set is provided, only rules whose tier is in the set are expanded; others
keep their `[ref-key]` marker intact.

`_read_tier(rule_path: Path) -> int` reads only line 1 (no whole-file load).

### Hook wiring

`hooks/inject-phase-context.sh` reads `expansion.tier_filter` from
`cognitive-os.yaml` and passes it to `expand()` via inline Python. Default when
key is absent: `[0, 1]`.

### Feature flag

```yaml
# cognitive-os.yaml
expansion:
  tier_filter: [0, 1]   # change to [0] for ~85% token savings
```

---

## Consequences

### Positive

- **Tier-0 only** (`[0]`): ~85% token reduction (107K → 16K tokens) on every
  `PreToolUse[Agent]` call.
- **Default `[0, 1]`**: conservative rollout — same expansion as before minus the
  8 Tier-2 integration rules (5% reduction). Zero behaviour change for typical tasks.
- Backward compatible: `tier_filter=None` restores pre-ADR-075 behaviour.
- Deterministic: tier is a static frontmatter property, not a runtime decision.
- Operator-controllable: change `expansion.tier_filter` in `cognitive-os.yaml` to
  adjust the token budget without touching code.

### Negative

- **Tier-2 false negatives**: agents running with `[0, 1]` will not see
  `aguara-integration`, `e2b-integration`, etc. inline. They keep the marker;
  whether this matters depends on task context.
- **Tier-0-only risk**: reducing to `[0]` withholds ~95 Tier-1 rules from
  context. Agent escalation rate may increase; monitor before enabling in production.
- Classification boundary: 95 rules are Tier-1 — the tier system is coarse. Fine-
  grained per-rule adjustment is possible by editing frontmatter manually.

---

## Migration

Default `tier_filter: [0, 1]` is a safe no-op for current users. To capture
the full 85% savings:

1. Set `expansion.tier_filter: [0]` in `cognitive-os.yaml`.
2. Run a session and observe agent escalation rate and trust scores.
3. If escalation < 5% above baseline, keep `[0]`.
4. If escalation rises, revert to `[0, 1]` and demote specific rules from
   Tier-1 → Tier-0 individually.

---

## 2026-04-30: Tier-1 reclassification

**Before**: 95 of 112 rule files were Tier-1. Default `tier_filter: [0, 1]` excluded
only 8 pre-existing Tier-2 files, saving at most ~5K tokens — negligible.

**After**: Tier-1 shrunk to 38 curated rules. 57 rules demoted to Tier-2.

| Tier | Before | After |
|------|--------|-------|
| 0    | 9      | 9     |
| 1    | 95     | 38    |
| 2    | 8      | 65    |

**Keep-list criteria** (rules retained at Tier-1): rules that govern agent behavior
on every call — safety gates (credential-management, confidentiality-protection,
content-policy, agent-security), naming enforcement (python-naming, bash-naming),
error handling (error-learning, auto-rollback, auto-repair, crash-recovery), cost
controls (token-economy, model-routing, model-directive, decomposition,
rate-limiting, context-management), quality gates (prompt-quality, anti-hallucination,
blast-radius, clarification-gate, confidence-gate), and output/skill lifecycle
(result-management, response-compression, skill-management, audit-trail, responsiveness).

**Demoted to Tier-2** (loaded only when explicitly referenced): contextual/infrequent
rules — squad-protocol, SDD governance, infra health, dry-run, private-mode,
capability-levels, performance-monitoring, observability, pre-commit-gate, etc.

**Token impact**: The 57 demoted files total ~224 KB (~56K tokens). Default
`tier_filter: [0, 1]` now saves ~56K additional tokens per Agent call vs
pre-reclassification. Combined with the Tier-0-only setting (`tier_filter: [0]`),
the original 85% reduction target is now achievable in two steps: step 1 (`[0,1]`)
delivers ~56K savings immediately; step 2 (`[0]`) adds another ~15K for the Tier-1 set.

---

## Related

- ADR-027 Phase 2 — original ref-key loader  
- ADR-074 — Tier-0 learning-loop closure (predecessor)  
- `lib/ref_key_loader.py` — implementation  
- `hooks/inject-phase-context.sh` — hook wiring  
- `.cognitive-os/test-lanes.yaml` — lane registry for tests  
- `tests/unit/test_ref_key_loader.py` — unit tests (23 pass)
