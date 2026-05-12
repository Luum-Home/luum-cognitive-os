# Tier-Filter Validation Harness

**Date**: 2026-04-30
**Replaces**: manual 30-min human session requirement in `stage2-expansion-baseline.md §4`
**Harness**: `scripts/validate_tier_filter.py`

---

## 1. Why Automated

The original runbook assumes you need live human-driven workflows to observe `skills_failed`
regression. That assumption is wrong for two reasons:

1. `skills_failed` measures **skill tool invocation failures** (tracked in `skill-metrics.jsonl`),
   not rule expansion misses. It is a lagging indicator — it only moves if agents visibly fail
   to invoke the right skill, not if they receive incomplete context.
2. The direct impact of `tier_filter` is **unexpanded_keys** — the count of `[`key`]` markers
   that survive expansion as literal text inside agent prompts. This is fully deterministic and
   measurable offline without any LLM calls.

The automated harness provides statistically meaningful evidence in seconds by running prompts
through both configs and counting unexpanded keys. It also reads the live `session-learnings.jsonl`
for the `skills_failed` rate as a secondary safety gate.

---

## 2. Approach Selected: Synthetic (with Replay Option)

### 2.1 Replay Approach

Parse real session transcripts from `~/.claude/projects/<project>/*.jsonl`, extract user-turn
content that contains `[`key`]` markers, and replay each through both configs.

Limitation: only ~3 of 210 transcripts contain ref-key markers (agents inject them into their
own sub-prompts, not user messages). Replay degrades gracefully to the synthetic path when
fewer than 15 prompts are found.

### 2.2 Synthetic Approach (selected)

Use a fixed seed list of 15 prompts that cover:
- Tier-1-heavy tasks: cross-service refactor, cost/model routing, PR review, context management,
  rollback, confidence gate, agent security, rate limiting, audit trail, schema migration
- Tier-0-only controls: simple edits, unit tests, commit review (these should show zero delta)

Each seed is cycled up to N times, giving a deterministic and reproducible corpus.

**Why synthetic over replay**: 210 sessions available but only 3 contain ref-key markers
(session transcripts capture raw user messages, not expanded agent contexts). Synthetic seeds
provide controlled coverage of all Tier-1 categories and are fully reproducible.

---

## 3. Design

### Configs

| Label | `tier_filter` | Description |
|-------|--------------|-------------|
| Config A | `[0, 1]` | Current production (baseline) |
| Config B | `[0]` | Candidate — saves ~35K tokens/delegation |

### Metrics per trial

- `unexpanded_keys` under each config (from `lib.ref_key_loader.expand`)
- `delta = B.unexpanded_keys - A.unexpanded_keys` (positive = B is worse)

### Aggregate statistics

- Mean delta across N trials
- Regression rate: fraction of trials where B leaves more keys unexpanded
- Wilcoxon signed-rank test on deltas (non-parametric, valid for non-normal distributions)
- Live `skills_failed` rate from `session-learnings.jsonl` (last 7 days)

### Decision gates

| Gate | Pass condition | Consequence |
|------|---------------|-------------|
| Live safety | `skills_failed/session ≤ 0.89` (2× baseline) | KEEP if fail |
| Expansion majority | regression rate < 50% | KEEP if fail |
| Expansion minority | regression rate < 30% | Required for FLIP |
| High delta | mean delta < 3.0 keys | Additional KEEP signal |

### Statistical test

Wilcoxon signed-rank (paired, non-parametric). At N=30 the normal approximation applies:
z-score and p-value reported. p < 0.05 indicates statistically significant difference between
configs.

### Output

Structured JSON at the output path + human-readable `.md` alongside it.

```
{
  "schema_version": "1.0",
  "approach": "synthetic",
  "statistics": {
    "n_trials": 30,
    "mean_unexpanded_keys_a": ...,
    "mean_unexpanded_keys_b": ...,
    "mean_delta_b_minus_a": ...,
    "trials_b_worse": ...,
    "wilcoxon_w": ...,
    "wilcoxon_note": "z=X.XXX p=X.XXXX",
    "observed_skills_failed_rate": ...,
    ...
  },
  "decision": {
    "recommendation": "FLIP | KEEP | NEEDS-MORE-DATA",
    "rationale": "...",
    "auto_flip_eligible": false,
    "auto_flip_env_var": "COS_AUTO_FLIP_TIER_FILTER"
  },
  "trials": [...]
}
```

### Decision automation

- `recommendation == "FLIP"` + `COS_AUTO_FLIP_TIER_FILTER=1` → harness sets `auto_flip_eligible: true`
  (actual YAML mutation is the operator's responsibility)
- `recommendation == "KEEP"` → document which Tier-1 rules caused regressions in trial data
- `cognitive-os.yaml` is never auto-mutated by the harness itself

---

## 4. Sample Size Rationale

N=30 provides:
- Wilcoxon normal approximation valid (requires n ≥ 10 nonzero diffs)
- At δ=1 key, σ≈1.5: power ≈ 0.85 to detect a real difference (Cohen's d ≈ 0.67)
- Covers 2× the 15-seed cycle, exercising all Tier-1 categories twice
- Runs in <1 second (no LLM calls)

---

## 5. Repeatability

Anyone can re-run the harness at any time:

```bash
python3 scripts/validate_tier_filter.py \
  --approach=synthetic \
  --n=30 \
  --output=docs/06-Daily/measurements/tier-filter-validation-$(date +%F).json
```

Or with real session replay (when more ref-key-bearing sessions accumulate):

```bash
python3 scripts/validate_tier_filter.py \
  --approach=replay \
  --n=30 \
  --output=docs/06-Daily/measurements/tier-filter-validation-$(date +%F).json
```

Results accumulate over time; compare runs to track drift in the recommendation.

---

## 6. Limitations

1. **Synthetic seeds are curated**: the 15 seeds deliberately exercise Tier-1 rules. A corpus
   of purely Tier-0 tasks would show zero delta and recommend FLIP. The seed selection reflects
   the risk surface, not the frequency distribution of real tasks.
2. **Replay data sparse**: only prompts with `[`key`]` markers are useful for expansion testing.
   As agents learn to include more ref-key markers in sub-agent prompts, replay will become
   the primary approach.
3. **skills_failed proxy**: the live rate captures skill tool failures, not context-quality
   degradation. An agent running with incomplete Tier-1 context may produce worse output without
   registering a `skills_failed` event.
