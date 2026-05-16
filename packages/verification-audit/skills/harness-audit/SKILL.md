---
name: harness-audit
description: 'Evaluate harness agentic primitives (hooks, rules, skills) for continued
  relevance. Identify candidates for simplification or retirement as models improve.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-26
license: MIT
metadata:
  author: luum
audience: os-dev
summary_line: Evaluate harness agentic primitives (hooks, rules, skills) for continued
  relevance.
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bharness[- ]?audit\b
  confidence: 0.95
- pattern: \baudit\s+harness\b
  confidence: 0.85
routing_intents:
- "audit harness agentic primitives for relevance"
- "review hooks rules and skills for simplification"
- "identify obsolete harness primitives for possible removal"
- "evaluate whether OS primitives should be retired"
- "assess harness complexity as models improve"

triggers:
- harness-audit
- /harness-audit
- Evaluate harness agentic primitives (hooks, rules, skills) for continued relevance
---
<!-- SCOPE: os-only -->
## Purpose

Periodic self-assessment of the Cognitive OS harness. The question is: "Which guardrails are still earning their keep?"

This skill does NOT auto-remove anything. It produces recommendations for human review.

## Invocation

`/harness-audit [--period=30d] [--focus=hooks|rules|skills|all]`

## What to Do

### Step 1: Collect Activity Data

Read metrics files to understand agentic primitive activity:

```
Sources:
├── .cognitive-os/metrics/error-learning.jsonl     → hook trigger history
├── .cognitive-os/metrics/repair-outcomes.jsonl     → repair attempts and outcomes
├── .cognitive-os/metrics/skill-metrics.jsonl       → skill usage and success rates
├── hooks/                                          → hook inventory (list files)
├── rules/                                          → rules inventory (list files)
├── skills/                                         → skills inventory (list dirs)
├── cognitive-os.yaml                               → current phase config
└── .cognitive-os/metrics/remediation-registry.jsonl → known fix patterns
```

Parse the `--period` flag (default 30 days). Filter metrics to that window.

### Step 2: Analyze Hook Activity

For each hook script in `hooks/`:

```
FOR EACH hook:
├── Count triggers in period (from error-learning.jsonl + repair-outcomes.jsonl)
├── Count blocks/repairs vs pass-throughs
├── Calculate value_ratio = (blocks + repairs) / total_triggers
├── Classify:
│   ├── ACTIVE      → value_ratio > 5% AND triggers > 0
│   ├── LOW-VALUE   → value_ratio <= 5% AND triggers > 10 (fires often, rarely blocks)
│   └── DORMANT     → triggers == 0 in analysis period
└── Note: hooks in _lib/ are libraries, not standalone — skip them
```

### Step 3: Analyze Rule Activity

For each rule file in `rules/`:

```
FOR EACH rule:
├── Check if any hook references it (grep rule filename in hooks/)
├── Check if error-learning.jsonl logs violations related to rule keywords
├── Classify:
│   ├── ACTIVE     → referenced by hooks AND has violation history
│   ├── PASSIVE    → referenced by hooks but no violations (may be preventing issues)
│   └── ORPHANED   → not referenced by any hook (candidate for review)
└── Note: constitutional/security rules are NEVER candidates for retirement
```

### Step 4: Analyze Skill Metrics

For each skill directory in `skills/`:

```
FOR EACH skill:
├── Check usage count in period (from skill-metrics.jsonl)
├── Check success rate (if tracked)
├── Classify:
│   ├── ACTIVE           → usage > 0 AND success_rate >= 50%
│   ├── UNDERPERFORMING  → usage > 0 AND success_rate < 50%
│   └── UNUSED           → usage == 0 in analysis period
└── Note: auto-triggered skills may not appear in invocation metrics
```

### Step 5: Phase Graduation Assessment

Compare current metrics against phase transition criteria from `cognitive-os.yaml`:

```
Assess readiness for next phase:
├── Error rate trend (declining = positive signal)
├── Auto-repair frequency (declining in later phases = expected)
├── Repair success rate (> 80% = stable)
├── Manual intervention frequency (declining = positive signal)
└── Verdict: READY / NOT READY / INSUFFICIENT DATA
```

### Step 6: Generate Report

```markdown
## Harness Audit Report

**Period**: {start_date} to {end_date}
**Current Phase**: {phase from cognitive-os.yaml}

### Summary
| Category | Total | Active | Low-Value | Dormant/Orphaned/Unused |
|----------|-------|--------|-----------|------------------------|
| Hooks    | {N}   | {N}    | {N}       | {N}                    |
| Rules    | {N}   | {N}    | {N} (passive) | {N} (orphaned)     |
| Skills   | {N}   | {N}    | {N} (underperforming) | {N} (unused) |

### Candidates for Review

#### Dormant Hooks (0 triggers in {period})
| Hook | Last Known Trigger | Recommendation |
|------|-------------------|----------------|
| {name} | {date or "Never"} | Review: still needed? |

#### Low-Value Hooks (>95% pass-through)
| Hook | Triggers | Blocks | Value Ratio | Recommendation |
|------|----------|--------|-------------|----------------|
| {name} | {N} | {N} | {N}% | Consider simplifying |

#### Orphaned Rules (no hook references)
| Rule | Content Summary | Recommendation |
|------|----------------|----------------|
| {name} | {1-line summary} | Review: integrate or archive |

#### Unused Skills (0 invocations in {period})
| Skill | Last Used | Recommendation |
|-------|-----------|----------------|
| {name} | {date or "Never"} | Review: still relevant? |

#### Underperforming Skills (<50% success)
| Skill | Uses | Success Rate | Recommendation |
|-------|------|-------------|----------------|
| {name} | {N} | {N}% | Investigate failures, consider rewrite |

### Phase Graduation
**Current**: {phase}
**Next**: {next phase}
**Assessment**: {READY / NOT READY / INSUFFICIENT DATA}
**Rationale**: {why}

### Important Caveats
- DORMANT does not mean USELESS. A hook may be dormant because it successfully prevents errors that no longer occur. Removing it could reintroduce those errors.
- ORPHANED rules may be enforced through CLAUDE.md instructions, not hooks.
- UNUSED skills may be triggered by auto-loader rules, not direct invocation.
- These are RECOMMENDATIONS, not directives. Always validate before removing any agentic primitive.
```

### Step 7: Persist Report

```
mem_save(
  title: "Harness audit report {date}",
  topic_key: "harness/audit-report",
  type: "discovery",
  project: "{project}",
  content: "{full report markdown}"
)
```

## Rules

- NEVER recommend removing security, constitutional, or license rules
- NEVER auto-remove any agentic primitive — recommendations only
- Always include the "Important Caveats" section
- If metrics files don't exist, report "No data available" rather than failing
- Compare against at least 2 analysis periods if data allows (trend detection)
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
