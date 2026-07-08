---
type: concept-synthesis
source: docs/04-Concepts/architecture/project-consumption-patterns.md
---

## What it is
Describes three tiers of external project consumption models for COS — Minimal, Standard, Full Pipeline — and documents `reference-project` as a mature Full Pipeline consumer example, plus the TAC (Tactical Agentic Coding) four-layer workflow framework COS should provide as scaffolding.

## Key mechanics
- **Minimal**: `cos init --minimal` -> AGENTS.md + basic rules. Works with any tool that reads AGENTS.md (14+ tools). No automation/memory/gates.
- **Standard**: `cos init --standard` -> rules + 15 hooks + skills + Engram. Full support in Claude Code; Cursor/Devin via adapters. No external pipeline/CI.
- **Full Pipeline**: `cos init --full` -> everything + pipeline-runner + workflow templates. End-to-end automated SDLC (plan -> build -> test -> review -> document -> ship). Requires Python + a CLI tool.
- `reference-project` directory shape: `.claude/` (settings.json, 4 Opus subagents, 17 commands, 11 rules, 114 sub-rules, 19 skills), `ai/` (~213 plan files, ~125 evaluation reports, web-workflow state), `ai-workflows/` (Python orchestrators: `web_feature_pipeline.py` 11-phase, `web_chore_pipeline.py`, `web_bug_pipeline.py`, `web_design_system_pipeline.py` 13-phase; `lib/agent.py`, `shared_phases.py`, `web_state.py` Pydantic state).
- Pipeline data flow: ClickUp Task -> Fetch&Branch -> Plan (`/plan-feature`) -> Evaluate (`evaluate-plan` skill, 50-point score, never blocks) -> Apply (`/apply-evaluation`) -> Implement (`/implement-approved-plan`) -> Build (`npm run build`) -> Test (`npm test`) -> Commit -> PR (`gh pr create`) -> Notify (Telegram).
- 5 key design decisions: evaluate-but-never-block (score enables trend analysis, avoids human bottleneck); per-agent `MEMORY.md` + Engram cross-agent search; Python wraps Claude CLI (each phase is a fresh invocation, no context degradation); slash commands are the swappable Python-to-AI API boundary; state lives in `workflow_state.json` with resume/start-from support, survives crashes.
- TAC four-layer architecture: Layer4 Justfile (human entry, e.g. `just build-feature 42`) -> Layer3 Commands (`.md`, orchestration) -> Layer2 Subagents (`.md`, parallel workers) -> Layer1 Skills (`.md`, raw capabilities); each layer delegates downward, entry at any layer.
- ADW evolution table TAC-1..TAC-8: `claude -p` -> slash commands -> plan-then-implement -> full ADW orchestration -> composable pipelines -> complete SDLC (+review/document/patch-retry) -> isolation + Zero Touch Execution (git worktrees) -> agent primitives (raw prompt/SDK/slash command as 3 primitives).
- 12 Leverage Points: In-Agent (Context, Model, Prompt, Tools); Through-Agent (Standard Output, Types, Docs, Tests, Architecture, Plans, Templates, AI Developer Workflows).
- COS-provides vs project-builds table: COS supplies quality governance, error learning, Engram memory framework, common skills, 93-hook framework, pipeline-runner framework, generic agent templates, 94-rule framework, config schema; projects build their own domain skills, per-agent MEMORY.md, pipeline variants, domain-specialized agents, project-specific rules/config.
- `ai/` directory convention for consumers: `plans/{features,bugs,chores,custom}/`, `evaluations/`, `reviews/`, `docs/`, `workflow/{id}/state.json`; file naming `{date}-{type}-{slug}.md`.

## Relations & where used
`reference-project` (Next.js e-commerce example), IndyDevDan's Tactical Agentic Coding (TAC) course, Engram, `cognitive-os.yaml`, the hook framework, the rules framework.

## Status / caveats
Descriptive/reference document; no explicit implementation status given.
