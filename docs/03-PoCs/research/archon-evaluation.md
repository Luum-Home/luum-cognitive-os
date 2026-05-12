# Archon Evaluation — Workflow Execution Engine

## Summary

Archon (coleam00/Archon) is a TypeScript/Bun workflow engine for AI coding agents. MIT license, 15K+ stars, v0.3.5. Evaluated 2026-04-10.

## Verdict: DO NOT ADOPT as dependency. ADOPT patterns via clean-room.

## What Archon Does

8-package monorepo: `core`, `workflows`, `isolation`, `git`, `adapters`, `server`, `web`, `cli`. YAML-defined DAG workflows with 7 node types (agent, tool, loop, conditional, parallel, approval, output). Each node runs in an isolated git worktree with configurable MCP tools per-node. Supports multi-platform adapters (Claude, OpenAI, local models) and a React 19 web UI for workflow creation and monitoring.

Key primitives:
- **Agent node**: LLM call with configurable model, prompt, tools
- **Loop node**: repeat until condition satisfied (max_iterations guard)
- **Conditional node**: branch on output pattern match
- **Parallel node**: fan-out multiple nodes simultaneously
- **Approval node**: human-in-the-loop gate
- **Output node**: pipe node output as input to downstream nodes
- **Tool node**: direct tool invocation without LLM overhead

## Feature Comparison

| Feature | Archon | COS | Winner |
|---------|--------|-----|--------|
| YAML workflow definition | Yes (native) | No (Python DAG only) | Archon |
| Conditional branching (when/if) | Yes (conditional node) | No | Archon |
| Loop node primitive | Yes (built-in) | No | Archon |
| Output piping between nodes | Yes ($node_id.output) | No | Archon |
| Git worktree isolation | Yes (per-node) | No | Archon |
| Multi-platform adapters | Yes (Claude, OpenAI, local) | No (Claude only) | Archon |
| Web UI for workflows | Yes (React 19) | No | Archon |
| Adversarial dev workflow | Yes (GAN-inspired template) | Via sdd-verify | Archon |
| Per-node MCP tool config | Yes | No | Archon |
| Error classification (FATAL/TRANSIENT) | Yes | Partial (auto-repair) | Archon |
| Quality governance (gates) | No | Yes (12+ gates) | COS |
| Cost intelligence | No | Yes (full tracking) | COS |
| Self-improvement loop | No | Yes (consequence system) | COS |
| Security scanning | No | Yes (semgrep, aguara, parry) | COS |
| Persistent memory (Engram) | No | Yes (cross-session) | COS |
| Phase-aware behavior | No | Yes (4 phases) | COS |
| Skill/rule library | No | Yes (60+ skills, 55+ rules) | COS |
| Adversarial review (mandatory findings) | No | Yes (forced finding) | COS |
| Crash recovery | No | Yes (git stash WAL) | COS |
| Observability (Langfuse) | No | Yes | COS |
| Trust score system | No | Yes | COS |
| Agent escalation protocol | No | Yes | COS |
| Broken window policy | No | Yes | COS |
| Squad/team governance | No | Yes | COS |
| Token economy | No | Yes | COS |
| Blast radius estimation | No | Yes | COS |
| Acceptance criteria enforcement | No | Yes | COS |

## What Archon Does Better

1. **YAML workflow definition** — human-readable, VCS-friendly, no Python boilerplate
2. **Loop node primitive** — `max_iterations` guard, condition-based exit, built into the DAG
3. **Conditional branching** — `when` field on nodes, pattern-match on previous output
4. **Output piping** — `$node_id.output` substitution syntax, clean data flow between nodes
5. **Git worktree isolation** — each node gets its own worktree, parallel nodes truly isolated
6. **Multi-platform adapters** — Claude, OpenAI, local models, same workflow definition
7. **Web UI** — visual workflow builder and monitor, first-class citizen not an afterthought
8. **GAN-inspired adversarial dev** — built-in workflow template for generator/critic pattern
9. **Per-node MCP configuration** — each node declares exactly which tools it needs
10. **Error classification** — FATAL/TRANSIENT/UNKNOWN taxonomy drives retry strategy

## What COS Does Better

1. **Quality governance** — 12+ hook-enforced gates (clarification, blast radius, DoD, trust score, adversarial review)
2. **Cost intelligence** — full tracking, prediction, model routing, budget enforcement, consequence system
3. **Self-improvement loop** — skill archive, consequence engine, auto-rewrite on 3 failures, OKR-driven KPIs
4. **Security depth** — semgrep SAST, aguara 189-rule scanner, parry ML injection, secret detection, content policy
5. **Persistent memory** — Engram cross-session memory with prefix organization and sidecar pattern
6. **Phase-aware behavior** — reconstruction/stabilization/production/maintenance phases change enforcement
7. **Skill/rule library** — 60+ skills, 55+ rules, skill routing, auto-generation, consequence feedback
8. **Agent rules** — closed-loop prompts, split-and-resume clarification, escalation protocol, broken window
9. **Crash recovery** — 5-minute git stash checkpoints, session state persistence
10. **Observability** — Langfuse tracing, agent KPI dashboard, performance monitoring, audit trail

## Patterns to Steal (Clean-Room)

| Priority | Pattern | Implementation |
|----------|---------|----------------|
| HIGH | Conditional execution (`when` field) | Add `when: str` to `TaskDAG.add_task()` — evaluates against previous node output before launching |
| HIGH | Loop node primitive | Add `loop: {condition, max_iterations}` to TaskDAG — node re-enqueues itself until condition met |
| HIGH | Output piping (`$node_id.output`) | Add `inputs: dict` to TaskDAG tasks — orchestrator substitutes `$id.output` references before launch |
| MEDIUM | YAML workflow format | Add `lib/yaml_workflow.py` — parse YAML into TaskDAG instances, export TaskDAG to YAML |
| MEDIUM | Error classification (FATAL/TRANSIENT/UNKNOWN) | Extend `auto-repair` error taxonomy to use Archon's three-class system for retry decisions |
| MEDIUM | Adversarial dev template | Add `templates/adversarial-dev.yaml` — generator agent + critic agent workflow for SDD verify |
| LOW | Approval node | Extend TaskDAG with `requires_approval: bool` — orchestrator pauses and asks user before launching |
| LOW | Per-node MCP tool config | Add `tools: list[str]` to TaskDAG tasks — restricts which MCP tools a node can use |
| LOW | Platform adapters | Add `adapter: str` field to TaskDAG tasks — routes to different model providers per node |
| LOW | Web UI | Dashboard concept is useful; defer until COS has a proper TUI/web layer |

## Why NOT Adopt as Dependency

- **Language boundary**: TypeScript/Bun vs Python — every COS component is Python; adding TS runtime adds significant complexity
- **Architectural mismatch**: Archon requires its own DB (SQLite/Postgres), HTTP server (Hono), and auth layer — COS is a CLI overlay with no server
- **Heavy dependency tree**: React 19, Hono, claude-agent-sdk, zod, dagre — none of these exist in COS's stack
- **Subprocess viability**: low — Archon needs to run as a server, not as a CLI subprocess
- **Governance gap**: Archon has zero quality governance; adopting it means maintaining two parallel orchestration systems
- **Version coupling**: we would inherit Archon's release cycle and breaking changes

## Architecture Relationship

```
Archon = Workflow Execution Runtime
  - DAG scheduling
  - Node isolation (worktrees)
  - Output streaming
  - Platform adapters

COS = Governance/Quality Framework
  - Quality gates (hooks)
  - Security mesh
  - Memory (Engram)
  - Cost governance
  - Self-improvement
  - Phase-aware enforcement
```

These are complementary, not competing. Archon solves workflow execution mechanics; COS solves governance and quality. A future integration could use Archon as the execution substrate with COS hooks wrapping each node — but this is a multi-month project, not a drop-in adoption.

## Next Steps

1. Enhance `lib/task_dag.py` with conditional execution (`when` field on tasks)
2. Add loop node primitive to `TaskDAG` (condition + max_iterations guard)
3. Add output piping (`$node_id.output` substitution in task prompts)
4. Consider `lib/yaml_workflow.py` for YAML-defined workflow import/export
5. Re-evaluate Archon if it adds governance/quality features in a future version
