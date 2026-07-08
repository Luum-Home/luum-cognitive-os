---
type: concept-synthesis
source: docs/04-Concepts/root/leverage-points.md
status: "10/12 leverage points fully covered, 2 partially covered (tests-as-guardrails needs a PITER auto-fix loop; prompt templates need a centralized library)"
---

## What it is
Maps Cognitive OS components against the 12 "leverage points" from IndyDevDan's "Tactical Agentic Coding" (agenticengineer.com) — 6 in-agent points (individual agent quality) and 6 through-agent points (system of agents).

## Key mechanics
In-agent (1-6): (1) Standard Output Types — Full (SDD Result Contract: status/executive_summary/artifacts/next_recommended/risks; JSONL skill metrics; error-learning JSONL; active-task JSON); (2) Tests as Guardrails — Partial (auto-test-on-edit hook, error-learning, Constitutional Gate 3, but no auto-fix loop — see `piter-framework.md`); (3) Architecture as Context — Full (go-architecture, architecture, constitutional-gates, phase-aware-agents rules); (4) Context Engineering — Full (progressive loading, RULES-COMPACT.md, pre-compaction flush, Engram recovery; gap: no consolidated 12-technique catalog); (5) Prompt Templates — Partial (SKILL.md files + sub-agent launch pattern + SDD phase prompts, but no centralized `templates/` library); (6) Skill Libraries — Full (project/global skills, CATALOG.md, Skill Registry Protocol, auto-generation/self-improvement).
Through-agent (7-12): (7) Multi-Agent Orchestration — Full (Agent Teams Orchestrator, delegate-first rule, sub-agent context protocol, active-task tracking); (8) Agent Specialization/Squads — Full (Squad Protocol, organization.yaml, squad manager; gap: auto-reconfig needs human approval); (9) Feedback Loops — Full (error learning, skill adaptation at 3+ failures, skill feedback tracker, agent KPIs; gap: loops not fully closed, needs PITER); (10) Workflow Automation/ADWs — Full (`.cognitive-os/workflows/` 5 pipelines, SDD 8-phase, scheduled tasks, GitHub Actions; gap: not explicitly named ADW, see `adw-patterns.md`); (11) Self-Improving Systems — Full but reactive-only (auto-skill generation, skill rewrite at 3+ failures, model routing optimizer, error pattern detection); (12) Resource Governance — Full (Resource Governor, cost tracking, model routing table, context optimization).

## Relations & where used
References `piter-framework.md` for closing refinement/feedback loops, and `adw-patterns.md` for formalizing workflow automation naming.

## Status / caveats
Overall: 10/12 fully covered, 2 partial. The primary gap across the doc is closing the refinement loop (PITER) and building a centralized prompt template library.
