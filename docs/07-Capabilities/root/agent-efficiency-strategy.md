# Agent Efficiency Strategy

## Problem

Each sub-agent launched by the orchestrator incurs a "cold start" tax before doing any work:

| Context Source | Tokens |
|---|---|
| System prompt | ~20K |
| CLAUDE.md global rules | ~5K |
| 94 rules in `.claude/rules/` | ~73K |
| Task prompt | ~2-5K |
| **Total** | **~100K tokens** |

At Opus 4.6 pricing ($15 input / $75 output per 1M tokens), a single agent launch costs **$1.50–$7.50 just to load context** before executing a single line of code.

The WISC paper (arxiv 2507.11538) found that loading >150 instructions degrades LLM performance. At 94 rules, we are already in degradation territory. Anthropic's own experiments confirm that detailed frameworks are overhead for Opus 4.6 — the model does not need all of them to perform well.

This document defines a 3-level strategy to cut per-agent cost by 10–20x and reduce session wall-clock time by 3–5x.

---

## Level 1: Model Routing by Default

**Status: Not yet enforced (rules exist, behavior does not)**

**Impact: ~3x faster, ~5x cheaper**

### The Problem

All sub-agents currently inherit the parent session's model (Opus 4.6). Implementation tasks — writing code, running tests, updating docs — do not require Opus-level reasoning. Sonnet handles them with negligible quality difference at 5x lower cost.

### The Change

The orchestrator passes `model: "sonnet"` explicitly when launching implementation agents. Opus is reserved for tasks that genuinely require deep reasoning.

| Task Type | Model | Reason |
|---|---|---|
| Architecture decisions | Opus | Requires broad cross-domain reasoning |
| Root cause analysis | Opus | Requires deep causal inference |
| Complex multi-service debugging | Opus | Requires holding many constraints |
| SDD propose, design | Opus | High-stakes decisions |
| SDD spec, tasks, apply, verify | Sonnet | Structured, bounded execution |
| Documentation, archiving | Haiku | Formatting and prose, no reasoning |
| Test writing | Sonnet | Pattern-following, well-defined |
| Code review (non-adversarial) | Sonnet | Pattern recognition |

### Implementation

`rules/model-routing.md` already defines the routing table. The gap is enforcement: the orchestrator must explicitly pass the model parameter rather than letting it default to the parent's model.

```
# Before (current behavior)
Agent(task="implement X")  # inherits Opus from parent

# After (enforced routing)
Agent(task="implement X", model="sonnet")  # explicit, cheaper
```

The `lib/model_router.py` module already supports `select_model(task_type)`. Orchestrators should call this before every Agent launch.

### Cost Comparison

| Scenario | Opus | Sonnet | Savings |
|---|---|---|---|
| 100K token context load | $1.50 | $0.30 | 80% |
| 50K token implementation output | $3.75 | $0.75 | 80% |
| Full agent (context + output) | ~$5.25 | ~$1.05 | 80% |

---

## Level 2: Context Diet for Sub-Agents

**Status: Partially implemented (lean profile exists), not used by default**

**Impact: ~20x context reduction, ~$0.10–0.30 per agent**

### The Problem

Claude Code automatically loads all files from `.claude/rules/` into every agent's context. A sub-agent implementing a single Go function receives 73K tokens of rules about squad protocols, session concurrency, Singularity mode, and other concerns it will never use.

A focused sub-agent needs at most:

| Content | Tokens |
|---|---|
| Agent preamble (progress markers, output format) | ~500 |
| 2–3 relevant task rules | ~2K |
| Task prompt with acceptance criteria | ~2K |
| **Total** | **~5K tokens** |

This is a 20x reduction from the current ~100K baseline.

### Approaches (in order of feasibility)

**a) Efficiency profiles (available now)**

`scripts/apply-efficiency-profile.sh` supports a `lean` profile that loads only `RULES-COMPACT.md` instead of all 94 rule files. This reduces the rules token load from ~73K to ~1.5K.

Adoption blocker: the lean profile is not the default. It requires manual activation per session.

**b) Prompt-composition approach (medium effort)**

Instead of relying on file-based rule loading, the orchestrator injects only the rules relevant to each task via the `templates/` composition system. This means the sub-agent's `.claude/rules/` directory can be empty or minimal, and all governance comes through the task prompt.

This approach requires changing how the orchestrator constructs agent prompts but does not require changes to Claude Code internals.

**c) Worktree isolation (complex)**

Run sub-agents in git worktrees with a minimal `.claude/rules/` directory containing only what that agent needs. This provides true per-agent context control but adds worktree management complexity.

**d) Capability level 4 (available now, aggressive)**

`rules/capability-levels.md` defines level 4 (autonomous), which auto-disables: `clarification-gate`, `assumption-tracking`, `confidence-gate`, `model-routing`, and `blast-radius`. For Opus 4.6, these checks are redundant — the model handles them internally. Setting `model_capability.level: 4` in `cognitive-os.yaml` removes their overhead.

### Recommended Path

1. Set `model_capability.level: 4` in `cognitive-os.yaml` for Opus 4.6 sessions (immediate)
2. Apply the lean efficiency profile by default for sub-agents (short term)
3. Move governance injection to prompt-composition for sub-agents (medium term)

---

### Level 2 Implementation Plan

**Chosen approach: capability level 4 + lean profile (a + d combined)**

Approaches (a) and (d) are already implemented in infrastructure and require only config changes. They deliver the maximum token reduction for minimum implementation effort.

Approach (b) (prompt-composition) is the right long-term solution but requires orchestrator refactoring. Approach (c) (worktrees) adds management complexity that is not justified at this stage.

#### Step 1: Set capability level 4 in cognitive-os.yaml (immediate, zero code)

```yaml
# cognitive-os.yaml — change this:
model_capability:
  level: 3     # current

# to this:
model_capability:
  level: 4     # autonomous — disables 5 redundant hooks for Opus 4.6
```

**What this disables** (hooks that run on every agent launch):
- `clarification-gate` — Opus 4.6 handles ambiguity internally
- `assumption-tracking` — Opus 4.6 is self-aware about its assumptions
- `confidence-gate` — Trust score enforcement is redundant at this model tier
- `model-routing` — The orchestrator already sets model explicitly
- `blast-radius` — Scope estimation is baked into Opus 4.6 reasoning

**Token savings**: ~5 hook files × ~800 tokens = **~4K tokens per agent launch** saved from context-loading overhead.

#### Step 2: Switch efficiency profile to lean for sub-agents (short term)

```yaml
# cognitive-os.yaml — change this:
efficiency:
  profile: standard     # current: loads 14 core rule files (~11K tokens)

# to this:
efficiency:
  profile: lean         # loads RULES-COMPACT.md only (~1.5K tokens)
```

The `lean` profile is enforced by `hooks/self-install.sh` at session start. It removes all rule symlinks except `RULES-COMPACT.md` from `.claude/rules/cos/`. The compact index gives every agent the rule summaries it needs to load the full rule on demand, without loading all 75 full files upfront.

**Token savings from rules**:
| Profile | Files loaded | Approx tokens |
|---|---|---|
| full (current) | 75 rule files | ~73,000 |
| standard | 14 core rules | ~11,000 |
| lean | 1 compact index | ~1,500 |

**Net per-agent reduction from Step 1 + Step 2**: ~100K → ~27K tokens (~73% reduction).

#### Step 3: Inject task-specific rules via prompt-composition (medium term)

Use `lib/context_diet.py` to select 2–4 rules per task type and inject them into the agent prompt via the `templates/` composition system. This eliminates reliance on file-based loading entirely for sub-agents.

**Task-to-rules mapping:**

| Task Type | Rules Needed | Total rules |
|---|---|---|
| implementation | acceptance-criteria, closed-loop-prompts, trust-score + always-included | 7 |
| review | adversarial-review, trust-score + always-included | 6 |
| debugging | error-learning, closed-loop-prompts + always-included | 6 |
| docs | always-included only | 4 |
| archiving | always-included only | 4 |

**Always-included rules** (governance floor for all agents):
- `RULES-COMPACT.md` — compact rule index for on-demand loading
- `adaptive-bypass.md` — complexity classification gate
- `agent-quality.md` — anti-sycophancy, communication standards
- `credential-management.md` — security baseline

**Token savings from Step 3**: from ~27K (lean profile) → ~5K (diet injection) = **~82% additional reduction**.

#### Expected token savings — real numbers

Current rule file count: 75 `.md` files in `rules/`
Average rule file size: ~6,000 chars = ~1,500 tokens

| Scenario | Context tokens | Estimated cost (Sonnet) |
|---|---|---|
| Current (full load) | ~100,000 | ~$0.30 |
| Step 1 only (cap level 4) | ~96,000 | ~$0.29 |
| Step 2 only (lean profile) | ~28,500 | ~$0.09 |
| Step 1 + Step 2 combined | ~24,500 | ~$0.07 |
| Step 3 (prompt diet) | ~5,000 | ~$0.02 |

At 20 sub-agent launches per session, Step 1 + Step 2 saves **~$4.40/session** vs current.
Full implementation (all three steps) saves **~$5.60/session** — a **19x cost reduction**.

#### Config changes summary

```yaml
# cognitive-os.yaml — two-line change for immediate 73% token reduction

model_capability:
  level: 4      # was: 3

efficiency:
  profile: lean  # was: standard
```

#### Tooling

`lib/context_diet.py` provides:
- `estimate_rules_tokens(rules_dir)` — measure actual token load before/after
- `get_minimal_rules(task_type)` — select 4–7 rules per task
- `format_diet_report(rules_dir)` — print baseline vs optimal comparison

Run anytime to measure current state:
```python
from lib.context_diet import format_diet_report
print(format_diet_report(".claude/rules/cos"))
```

---

## Level 3: Aggressive Parallelization

**Status: Partially implemented (WorkloadScheduler exists), underused**

**Impact: 3–5x throughput increase, same per-agent cost**

### The Problem

The SDD pipeline and most multi-agent tasks run sequentially by default:

```
Agent A (5 min) → Agent B (5 min) → Agent C (5 min) = 15 min wall clock
```

Many phases are independent and can run simultaneously:

```
Agent A + Agent B + Agent C = 5 min wall clock
```

### Dependency Map

Not all phases can be parallelized. The constraints are:

| Phase | Depends On | Can Parallelize With |
|---|---|---|
| explore | nothing | propose (if topic is clear) |
| propose | explore output | — |
| spec | propose output | design |
| design | propose output | spec |
| tasks | spec + design | — |
| apply | tasks output | — (sequential subtasks can parallelize) |
| verify | apply output | — |
| archive | verify output | — |

The SDD fast path (skip spec+design+tasks for small changes) reduces the sequential chain from 8 phases to 5, cutting wall-clock time even before parallelization.

### WorkloadScheduler Integration

`lib/workload_scheduler.py` exists and supports priority-based dispatch with rate limit awareness. The orchestrator currently launches agents ad hoc rather than routing through the scheduler.

The scheduler enables:
- Parallel dispatch of independent agents within rate limits
- Priority queuing (critical tasks run before low-priority tasks)
- Cost-aware batching (cheaper agents fill slots while expensive ones run)

### Apply-Phase Parallelization

Within `sdd-apply`, individual task subtasks are often independent. For example, implementing 5 different use cases can run as 5 parallel agents instead of 5 sequential ones. The orchestrator should detect independent tasks in the task checklist and dispatch them simultaneously.

### Target Concurrency

| Session Type | Current Agents | Target Agents | Speedup |
|---|---|---|---|
| Single feature (SDD) | 1 at a time | 3 simultaneous | 3x |
| Sprint (5 features) | Sequential | 10 simultaneous | 5x |
| Bulk implementation | 1–2 | 5 (rate limit cap) | 3–4x |

---

## Combined Impact

| Metric | Current | Level 1 | Level 2 | Level 3 |
|---|---|---|---|---|
| Avg agent cost | ~$2–5 | ~$0.50–1 | ~$0.10–0.30 | ~$0.10–0.30 |
| Avg agent time | 3–5 min | 1–2 min | 30s–1 min | 30s–1 min |
| Context per agent | ~100K tokens | ~100K (same) | ~5K tokens | ~5K tokens |
| Parallel agents | 1–2 | 1–2 | 1–2 | 3–5 |
| Session throughput | 3–5 tasks/hr | 8–12 tasks/hr | 15–20 tasks/hr | 25–40 tasks/hr |

Levels 1 and 2 each deliver cost reductions independently. Level 3 multiplies throughput on top of the cost savings from Levels 1 and 2. The full combination targets a 10–20x improvement in cost efficiency and a 5–8x improvement in session throughput.

---

## Metrics to Track

Add these to the session summary and `/agent-kpis` output:

| Metric | Source | Target |
|---|---|---|
| Tokens per agent launch (context overhead) | `cost-events.jsonl` | < 10K tokens |
| Wall-clock time per agent | `performance.jsonl` | < 90 seconds |
| Cost per agent (estimated) | `cost-events.jsonl` model x tokens | < $0.30 |
| Parallel utilization | agents simultaneous / total launched | > 50% |

---

## Implementation Order

1. **Week 1**: Enforce model routing — add `model: select_model(task)` to all Agent calls in orchestrator workflows. Zero infrastructure changes needed.
2. **Week 2**: Set `model_capability.level: 4` in `cognitive-os.yaml`. Apply lean efficiency profile as the default for sub-agents.
3. **Week 3–4**: Route multi-agent sessions through `WorkloadScheduler`. Detect independent tasks in `sdd-apply` and dispatch them in parallel.
4. **Month 2**: Evaluate prompt-composition approach for full context diet. Measure actual token reduction vs baseline.

---

## References

- `rules/model-routing.md` — routing table and dynamic multi-provider routing
- `rules/context-optimization.md` — 3-level progressive skill loading, token budget targets
- `rules/capability-levels.md` — auto-disable agentic primitives by model capability
- `rules/workload-scheduling.md` — WorkloadScheduler API and priority levels
- `rules/decomposition.md` — cost thresholds and model selection per sub-task
- `lib/model_router.py` — `select_model(task_type)` implementation
- `lib/workload_scheduler.py` — `WorkloadScheduler.plan(tasks)` implementation
- WISC paper: arxiv 2507.11538 — >150 instructions degrade LLM performance
