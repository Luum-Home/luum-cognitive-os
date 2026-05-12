---
cluster: agent-swe
date: 2026-05-06
phase: shallow
theme: SWE-bench agents (swe-agent, agentless, augment-swebench, superpowers, rover, goose)
total_repos: 6
passed_license: 6
rejected_license: 0
phase2_candidates: 4
budget_used_tool_calls: 3
counts_check: 6 = 6 + 0
---

# Cluster: agent-swe — Shallow Audit (2026-05-06)

Six repositories from the SWE-bench / coding-agent ecosystem. All pass license gate (MIT or Apache-2.0). Note: `block/goose` resolves to `aaif-goose/goose` via GitHub's transfer redirect — treated as a single canonical repo (counted once below; `block/goose` listed as alias).

## Per-repo triage

### 1. OpenAutoCoder/Agentless
- **URL**: https://github.com/OpenAutoCoder/Agentless
- **License**: MIT (PASS)
- **Stars**: 2,042
- **Last commit**: 2024-12-22
- **Primary language**: Python
- **Purpose**: Two-phase localize-then-repair pipeline that solves SWE-bench issues without an agent loop.
- **Triage verdict**: PHASE 2 CANDIDATE
- **Rationale**: Strong patterns relevance — "agentless" decomposition (file-level → element-level → patch generation) is the canonical baseline COS already references for skill-driven repair. Stale (~16mo no commits) but methodology, not code, is the value. Patterns-only adoption.

### 2. SWE-agent/SWE-agent
- **URL**: https://github.com/SWE-agent/SWE-agent
- **License**: MIT (PASS)
- **Stars**: 19,142
- **Last commit**: 2026-04-27
- **Primary language**: Python
- **Purpose**: NeurIPS 2024 agent that fixes GitHub issues via LM-driven Agent-Computer Interface; also used for cybersec/CTF.
- **Triage verdict**: PHASE 2 CANDIDATE
- **Rationale**: Active, high-signal reference for ACI design (bash tool surface, file viewer, edit semantics). Direct comparison target for COS agent harness. Patterns + selective code (MIT permissive). Worth deep dive on tool definitions and trajectory format.

### 3. block/goose (alias of aaif-goose/goose)
- **URL**: https://github.com/block/goose
- **License**: Apache-2.0 (PASS)
- **Stars**: 43,872
- **Last commit**: 2026-05-06
- **Primary language**: Rust
- **Purpose**: Open, extensible AI coding agent with install/execute/edit/test loop, multi-LLM.
- **Triage verdict**: PHASE 2 CANDIDATE
- **Rationale**: Very active, large community, Rust core (different impl substrate than COS Python+Go). Useful for harness comparison, MCP integration patterns, recipe/extension model. Apache-2.0 enables code reuse if needed.

### 4. aaif-goose/goose
- **URL**: https://github.com/aaif-goose/goose
- **License**: Apache-2.0 (PASS)
- **Stars**: 43,872 (same repo via redirect)
- **Last commit**: 2026-05-06
- **Primary language**: Rust
- **Purpose**: Same as block/goose (GitHub redirect / transferred owner).
- **Triage verdict**: SKIP (alias)
- **Rationale**: Redirects to `block/goose`. No independent value; do not double-count in Phase 2.

### 5. endorhq/rover
- **URL**: https://github.com/endorhq/rover
- **License**: Apache-2.0 (PASS)
- **Stars**: 262
- **Last commit**: 2026-03-27
- **Primary language**: TypeScript
- **Purpose**: Manager/orchestrator for multiple AI coding agents (Claude Code, Cursor, Gemini, Codex, Qwen).
- **Triage verdict**: PHASE 2 CANDIDATE
- **Rationale**: Direct overlap with COS multi-harness orchestration (ADR-049 LLM dispatch, harness adapter). Small but recent. Patterns for cross-agent dispatch + worktree mgmt likely reusable. Apache-2.0 friendly.

### 6. obra/superpowers
- **URL**: https://github.com/obra/superpowers
- **License**: MIT (PASS)
- **Stars**: 179,656
- **Last commit**: 2026-05-06
- **Primary language**: Shell
- **Purpose**: Agentic skills framework + software development methodology for Claude Code-style agents.
- **Triage verdict**: PHASE 2 CANDIDATE
- **Rationale**: Direct competitor/peer to COS skills system. High star count signals strong community validation. Shell-first means low porting cost. MIT permissive. Compare skill schema, trigger conditions, methodology vs COS rules/skills. Top priority.

## Phase 2 candidates (recommended for deep dive, ranked)

1. **obra/superpowers** — direct peer to COS skills/methodology; highest learn rate.
2. **SWE-agent/SWE-agent** — canonical SWE-bench agent; ACI patterns.
3. **OpenAutoCoder/Agentless** — agentless decomposition methodology baseline.
4. **block/goose** — extensibility / MCP / recipes patterns at scale.
5. **endorhq/rover** — multi-agent orchestrator overlap with COS dispatch.

`aaif-goose/goose` excluded (alias of block/goose).
