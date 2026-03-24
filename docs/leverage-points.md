# 12 Leverage Points for Agentic Engineering

> Source: "Tactical Agentic Coding" by IndyDevDan (agenticengineer.com)

## Overview

Leverage points are places where small investments in agent infrastructure yield outsized returns. They divide into two categories: **in-agent** (improving individual agent quality) and **through-agent** (improving the system of agents).

---

## In-Agent Leverage (Points 1-6)

These improve how individual agents perform their work.

### 1. Standard Output Types

**Concept**: Agents produce structured, predictable outputs (JSON, DTOs, typed responses) instead of free-form text. Downstream consumers can parse and act on results without ambiguity.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| SDD Result Contract | Every phase returns `status`, `executive_summary`, `artifacts`, `next_recommended`, `risks` |
| Skill metrics | Structured JSONL with `skill`, `duration`, `tokens`, `cost`, `model` |
| Error learning | Structured JSONL with `type`, `service`, `fingerprint`, `context` |
| Active tasks | JSON with `id`, `status`, `expectedOutputs`, `checkCommand` |

**Gap**: None significant. Output contracts are well-defined.

---

### 2. Tests as Guardrails

**Concept**: Automated tests serve as safety rails that prevent agents from shipping broken code. The agent runs tests after every change and uses results to self-correct.

**Cognitive OS Status**: Partially Implemented

| Component | How It Maps |
|-----------|-------------|
| auto-test-on-edit hook | Runs tests automatically when files change |
| error-learning | Captures test failures for pattern detection |
| Constitutional Gate 3 | "Test Before Merge" — all new code must have tests |

**Gap**: Tests run but are not yet integrated into a PITER refinement loop. Agent reports test failures but does not auto-fix. See `piter-framework.md`.

---

### 3. Architecture as Context

**Concept**: Architecture documentation loaded into agent context guides agents to follow project patterns instead of inventing new ones.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| go-architecture rule | Go patterns (ginext, clean arch layers, naming) |
| architecture rule | project platform communication layers |
| constitutional-gates | Immutable architectural principles |
| phase-aware-agents | Architecture enforcement varies by project phase |

**Gap**: None. Architecture is deeply encoded in rules and gates.

---

### 4. Context Engineering

**Concept**: Techniques for managing the agent's context window efficiently — loading only what's needed, compressing what's loaded, recovering what's lost.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Progressive loading | 3-level system (CATALOG.md, on-demand SKILL.md, references) |
| RULES-COMPACT.md | Compressed rules (~50 words each) |
| Pre-compaction flush | Save to Engram before context loss |
| Engram recovery | mem_context + mem_search for cross-session memory |

**Gap**: Some advanced techniques not yet formalized. Key techniques are spread across `rules/context-optimization.md` (progressive loading) and `rules/context-management.md` (window management). A consolidated 12-technique catalog has not been written yet.

---

### 5. Prompt Templates

**Concept**: Reusable, tested prompt structures that produce consistent agent behavior. Instead of ad-hoc prompts, use battle-tested templates.

**Cognitive OS Status**: Partially Implemented

| Component | How It Maps |
|-----------|-------------|
| SKILL.md files | Each skill is a prompt template with instructions, steps, output format |
| Sub-agent launch pattern | Standardized prompt structure (identity, context, skill, instructions) |
| SDD phase prompts | Each phase has a defined prompt pattern |

**Gap**: No centralized template library. Templates are embedded in skills and orchestrator logic. Could benefit from a `templates/` directory with reusable prompt fragments.

---

### 6. Skill Libraries

**Concept**: Curated collections of reusable agent capabilities, discoverable and version-controlled.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| `.cognitive-os/skills/` | Project-specific skills |
| `~/.claude/skills/` | Global cross-project skills |
| CATALOG.md | Skill index for discovery |
| Skill Registry Protocol | Version tracking, auto-detection, refresh |
| Auto-skill generation | Complex tasks auto-generate reusable skills |
| Skill adaptation | Skills self-improve based on feedback |

**Gap**: None significant. Skill system is mature with auto-generation and self-improvement.

---

## Through-Agent Leverage (Points 7-12)

These improve the system of agents working together.

### 7. Multi-Agent Orchestration

**Concept**: A coordinator agent delegates work to specialized sub-agents, managing dependencies and synthesizing results.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Agent Teams Orchestrator | Coordinator delegates all execution to sub-agents |
| Delegate-first rule | Always prefer async delegation |
| Sub-agent context protocol | Controlled context access, skill pre-loading |
| Active tasks tracking | Task lifecycle management across agents |

**Gap**: None. Orchestration is a core design principle.

---

### 8. Agent Specialization (Squads)

**Concept**: Agents are organized into specialized teams with domain expertise, governance, and performance tracking.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Squad Protocol | Squad YAML definitions with skills, governance, metrics |
| organization.yaml | Org-level governance across squads |
| Squad manager | ManagerAgent evaluates squad performance |
| Repo-to-squad mapping | Files mapped to owning squads |

**Gap**: Squad auto-reconfiguration is proposed but not automatically applied. Requires human approval for most changes.

---

### 9. Feedback Loops

**Concept**: Agent outputs feed back into the system to improve future performance. Failures become learning opportunities.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Error learning | Captures all test/lint/build failures, detects patterns |
| Skill adaptation | Failures trigger skill updates after 3+ occurrences |
| Skill feedback tracker | Records user corrections |
| Agent KPIs | Performance metrics drive optimization suggestions |

**Gap**: Feedback loops exist but are not fully closed — they suggest improvements but often require human action. See PITER for closing the loop.

---

### 10. Workflow Automation (ADWs)

**Concept**: AI Developer Workflows combine deterministic pipeline steps with non-deterministic agent execution. Repeatable, measurable, optimizable.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| `.cognitive-os/workflows/` | 5 pipeline definitions |
| SDD workflow | 8-phase structured development process |
| Scheduled tasks | Cron-based automated workflow triggers |
| GitHub Actions | CI/CD pipeline integration |

**Gap**: ADW concept is implemented but not explicitly named as such. See `adw-patterns.md` for formalization.

---

### 11. Self-Improving Systems

**Concept**: The agent system gets better over time without manual intervention. Failures lead to better skills, better routing, better resource allocation.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Auto-skill generation | Complex tasks produce reusable skills |
| Skill adaptation | 3+ failures trigger skill rewrite |
| Model routing optimizer | Metrics drive model selection updates |
| Error pattern detection | Repeated errors inject warnings |
| Agent KPIs | Performance trends drive optimization |

**Gap**: Self-improvement happens but is reactive (triggered by failures). Proactive optimization (e.g., periodic skill review regardless of failures) is not yet automated.

---

### 12. Resource Governance

**Concept**: Budget limits, token tracking, model selection, and infrastructure scaling managed as first-class concerns.

**Cognitive OS Status**: Implemented

| Component | How It Maps |
|-----------|-------------|
| Resource Governor | Budget enforcement, model downgrade chain |
| Cost tracking | Per-agent cost awareness, budget alerts |
| Model routing table | Recommended models per skill with cost reference |
| Context optimization | Token savings through progressive loading |

**Gap**: None significant. Resource governance is comprehensive.

---

## Summary: Cognitive OS Coverage

| Leverage Point | Status | Key Gap |
|----------------|--------|---------|
| 1. Standard output types | Full | — |
| 2. Tests as guardrails | Partial | No auto-fix loop (needs PITER) |
| 3. Architecture as context | Full | — |
| 4. Context engineering | Full | Document advanced techniques |
| 5. Prompt templates | Partial | No centralized template library |
| 6. Skill libraries | Full | — |
| 7. Multi-agent orchestration | Full | — |
| 8. Agent specialization | Full | Auto-reconfig needs approval |
| 9. Feedback loops | Full | Not fully closed (needs PITER) |
| 10. Workflow automation | Full | Formalize as ADW |
| 11. Self-improving systems | Full | Reactive only, not proactive |
| 12. Resource governance | Full | — |

**Overall**: 10/12 fully covered, 2 partially covered. Primary gap is closing the refinement loop (PITER) and formalizing prompt templates.
