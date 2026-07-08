---
type: capability-synthesis
source: docs/07-Capabilities/root/agent-efficiency-strategy.md
provenance: "Strategy document proposing a 3-level plan to cut per-sub-agent token cost and wall-clock time, written to justify and sequence specific cognitive-os.yaml and orchestrator changes."
---

## What it is
A cost/latency strategy document defining a 3-level plan (model routing, context diet, parallelization) to reduce per-sub-agent "cold start" overhead by 10-20x and session throughput time by 3-5x.

## Key mechanics
- Problem framing: each sub-agent launch loads ~100K tokens of context (system prompt ~20K, CLAUDE.md ~5K, 94 rules ~73K, task prompt 2-5K), costing $1.50-$7.50 per launch at Opus 4.6 pricing; cites the WISC paper (arXiv 2507.11538) that >150 instructions degrade LLM performance.
- **Level 1 — Model Routing by Default** (status: rules exist, not enforced): orchestrator should explicitly pass `model: "sonnet"` for implementation-class tasks rather than inheriting Opus from the parent; reserves Opus for architecture/root-cause/multi-service debugging/SDD propose-design. Cites `rules/model-routing.md` and `lib/model_router.py` (`select_model(task_type)`). Claims ~80% cost reduction per scenario table.
- **Level 2 — Context Diet for Sub-Agents** (status: lean profile exists, not default): four approaches ranked by feasibility — (a) `scripts/apply-efficiency-profile.sh` lean profile (loads only `RULES-COMPACT.md`, ~1.5K tokens vs ~73K full), (b) prompt-composition injection via `templates/`, (c) worktree isolation with minimal `.claude/rules/`, (d) `model_capability.level: 4` in `cognitive-os.yaml` (auto-disables `clarification-gate`, `assumption-tracking`, `confidence-gate`, `model-routing`, `blast-radius` hooks). Recommends combining (a)+(d) first, then (b). Gives a 3-step implementation plan with concrete YAML diffs and per-step token-savings tables (~100K -> ~24.5K combining steps 1+2, -> ~5K with step 3 prompt-diet via `lib/context_diet.py`).
- **Level 3 — Aggressive Parallelization** (status: WorkloadScheduler exists, underused): documents SDD phase dependency map (which phases can run in parallel: propose||nothing, spec||design, etc.), notes the SDD fast path already cuts 8 phases to 5, and recommends routing multi-agent dispatch through `lib/workload_scheduler.py` for rate-limit-aware parallel dispatch, priority queuing, and cost-aware batching, including apply-phase parallelization of independent SDD subtasks.
- Combined-impact table projects: avg agent cost ~$2-5 -> ~$0.10-0.30, avg agent time 3-5min -> 30s-1min, context per agent ~100K -> ~5K, session throughput 3-5 tasks/hr -> 25-40 tasks/hr across all three levels.
- Proposes new tracked metrics (tokens per agent launch, wall-clock per agent, cost per agent, parallel utilization) and a 4-phase rollout order (Week 1 model routing, Week 2 capability level 4 + lean profile, Weeks 3-4 WorkloadScheduler routing, Month 2 prompt-composition evaluation).

## Relations & where used
Cross-references `rules/model-routing.md`, `rules/context-optimization.md`, `rules/capability-levels.md`, `rules/workload-scheduling.md`, `rules/decomposition.md`, `lib/model_router.py`, `lib/workload_scheduler.py`, `lib/context_diet.py`, and the WISC paper (arXiv 2507.11538).

## Status / caveats
This is a proposal/strategy document, not a completed-implementation report — it explicitly marks Level 1 as "not yet enforced (rules exist, behavior does not)" and Level 2/3 as "partially implemented... not used by default" / "underused." All cost and throughput figures (e.g. "$4.40/session," "19x cost reduction," "25-40 tasks/hr") are estimates/targets from the strategy's own model, not measured production results.
