# Zero-Touch Engineering (ZTE)

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

## The North Star

ZTE is the end goal: **the codebase ships itself**. Agents detect needs, plan solutions, implement changes, test them, and deploy — with humans reviewing post-facto instead of approving pre-facto.

This is not about removing humans from engineering. It is about shifting humans from **operators** (doing the work) to **governors** (setting constraints and reviewing outcomes).

## Maturity Phases

### Phase 1: Semi-Autonomous (Current State)

```
Human triggers → Agent plans → Agent implements → Agent tests → Human reviews → Human merges
```

**What we have today:**
- Human initiates work via commands (/sdd-new, /sdd-apply, etc.)
- Agents execute SDD phases autonomously
- Agents run tests and report results
- Human reviews output and decides next steps
- Human merges and deploys

**Autonomy level**: Agent executes, human decides.

**Cognitive OS agentic primitives in play:**
- SDD workflow (all 8 phases)
- Sub-agent delegation
- auto-test-on-edit hook
- sdd-verify
- Error learning (reactive)

---

### Phase 2: Event-Driven Autonomy

```
Event occurs → Agent detects → Agent plans + implements → Agent tests + verifies → Auto-merge if passing → Human reviews post-facto
```

**What changes:**
- Triggers shift from human commands to system events (git push, failing test, monitoring alert)
- PITER loop runs without human intervention for each triggered task
- Auto-merge for changes that pass all gates (tests, lint, architecture compliance)
- Human reviews merged PRs asynchronously

**Autonomy level**: Agent decides and executes within guardrails. Human governs guardrails.

**What we need to add:**

| Primitive | Purpose | Effort |
|-----------|---------|--------|
| Event trigger system | Watch git events, CI results, monitoring alerts | Medium |
| PITER loop integration | Closed-loop execution for triggered tasks | Medium |
| Auto-merge policy | Rules for when auto-merge is safe | Low |
| Post-facto review queue | Dashboard of agent-merged changes for human review | Medium |
| Rollback automation | Auto-revert if production metrics degrade after merge | High |

**Cognitive OS agentic primitives that enable this:**
- SRE agent (monitoring + auto-repair)
- Scheduled tasks (cron-based triggers)
- GitHub Actions (CI/CD hooks)
- Constitutional gates (merge safety constraints)
- Closed-loop prompts (self-correcting execution)

---

### Phase 3: Full ZTE

```
Monitoring detects need → Agents plan + implement + test + deploy → Human reviews post-facto (or not at all)
```

**What changes:**
- Agents proactively identify work (not just react to events)
- Dependency updates, security patches, performance optimizations happen automatically
- Agents create their own tickets, plan sprints, allocate resources
- Human sets quarterly goals; agents decompose into tasks and execute
- Human intervention only for novel architectural decisions or business pivots

**Autonomy level**: Agent governs within strategic boundaries. Human sets strategy.

**What we need to add:**

| Primitive | Purpose | Effort |
|-----------|---------|--------|
| Proactive issue detection | Agents scan codebase for tech debt, security issues, optimization opportunities | High |
| Autonomous task creation | Agents create and prioritize their own backlog | High |
| Resource self-allocation | Agents decide model usage, parallelism, budget distribution | Medium |
| Strategic goal decomposition | Break OKRs into executable agent tasks | High |
| Confidence-based deployment | Deploy based on test coverage + confidence score, not human approval | High |

**Cognitive OS agentic primitives that enable this:**
- Squad system (specialized teams with performance targets)
- Agent KPIs (performance measurement + trend detection)
- Resource Governor (budget enforcement)
- Self-improving systems (skill adaptation, model routing optimization)
- Error learning (pattern detection across the system)

---

## Progression Path

```
Phase 1                    Phase 2                    Phase 3
Semi-Autonomous            Event-Driven               Full ZTE
─────────────────────────────────────────────────────────────────
Human triggers             Events trigger             Agents self-trigger
Agent executes             Agent loops (PITER)        Agents plan + execute
Human reviews              Auto-merge + review        Confidence-based deploy
Human decides              Gates decide               Strategy decides
```

## Prerequisites by Phase

### Phase 1 → Phase 2

| Prerequisite | Status | Notes |
|--------------|--------|-------|
| PITER framework | Documented | Needs implementation in workflows |
| Closed-loop prompts | Documented | Needs rule adoption |
| Test coverage > 80% per service | Partial | Varies by service |
| Architecture compliance > 95% | In progress | Reconstruction phase |
| SRE auto-repair success rate > 90% | Tracking | Needs more data |
| Constitutional gates enforced | Implemented | 7 gates active |

### Phase 2 → Phase 3

| Prerequisite | Status | Notes |
|--------------|--------|-------|
| Event-driven autonomy stable for 3+ months | Not started | Phase 2 dependency |
| Zero rollbacks from auto-merged changes | Not started | Phase 2 dependency |
| Agent KPIs consistently above targets | Tracking | Needs trend data |
| Proactive issue detection | Not started | Major capability addition |
| Strategic goal decomposition | Not started | Requires AI planning advances |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Agent ships breaking change | Constitutional gates + test coverage + auto-rollback |
| Infinite refinement loop | Max 3 PITER iterations + token budget cap |
| Cost explosion | Resource Governor + budget alerts + model downgrade chain |
| Security vulnerability introduced | Security scan gate + dependency audit + human review for auth changes |
| Agent creates unnecessary work | Task value scoring + human review queue for new tickets |

## Metrics to Track Progress

| Metric | Phase 1 | Phase 2 Target | Phase 3 Target |
|--------|---------|----------------|----------------|
| Human interventions per feature | 5-10 | 1-2 | 0-1 |
| Time from trigger to deploy | Hours | Minutes | Minutes |
| Auto-merge rate | 0% | >50% | >90% |
| Rollback rate | N/A | <5% | <1% |
| Agent-detected issues | 0 | Some | Most |
| Cost per feature (tokens) | High | Medium | Optimized |
