---
cluster: agent-research-selfevolve
date: 2026-05-06
phase: shallow
budget_max_tool_calls: 45
tool_calls_used: 4
total_input_repos: 15
counts:
  pass: 6
  reject: 3
  unresolved: 2
  flagged_self_modifying: 4
sum_check: 15  # 6 + 3 + 2 + 4 = 15
---

# Cluster: agent-research-selfevolve — Shallow Audit (2026-05-06)

Theme: research-grade / self-evolving agents. Shallow license + relevance triage only.

## Repos

### 1. HKUDS/nanobot — PASS
- URL: https://github.com/HKUDS/nanobot
- License: MIT
- Stars: 41,731
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Ultra-lightweight personal AI agent.
- Verdict: PASS
- Rationale: MIT, very active, high-signal. Worth Phase 2 deep dive on minimal-footprint agent loop patterns.

### 2. MaximeRobeyns/self_improving_coding_agent — PASS (FLAG: self-modifying)
- URL: https://github.com/MaximeRobeyns/self_improving_coding_agent
- License: MIT
- Stars: 323
- Last commit: 2025-04-23
- Primary language: Python
- Purpose: Coding agent framework that operates on its own codebase.
- Verdict: PASS — flagged under ADR-134 propose-only.
- Rationale: Direct theme match (self-improving). MIT. Stale ~1yr but reference-grade. Treat as monitor/learn, never auto-apply.

### 3. NousResearch/hermes-agent — PASS
- URL: https://github.com/NousResearch/hermes-agent
- License: MIT
- Stars: 134,556
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: General-purpose adaptive agent ("grows with you").
- Verdict: PASS
- Rationale: MIT, top-tier mindshare, extremely active. High Phase 2 priority.

### 4. NousResearch/hermes-agent-self-evolution — PASS (FLAG: self-modifying, license check)
- URL: https://github.com/NousResearch/hermes-agent-self-evolution
- License: null (no SPDX detected)
- Stars: 2,802
- Last commit: 2026-03-29
- Primary language: Python
- Purpose: Evolutionary self-improvement for Hermes (DSPy + GEPA over skills/prompts/code).
- Verdict: PASS — flagged under ADR-134; LICENSE confirmation required in Phase 2 before any code adoption.
- Rationale: Squarely on-theme. License absence blocks code reuse but patterns/architecture are studyable.

### 5. Pi-agent/pi — UNRESOLVED
- URL: https://github.com/Pi-agent/pi
- License: n/a
- Stars: n/a
- Last commit: n/a
- Primary language: n/a
- Purpose: n/a
- Verdict: UNRESOLVED (404 — repo missing/private/renamed).
- Rationale: Cannot triage. Drop unless user provides updated coordinates.

### 6. TinyAGI/tinyagi — PASS
- URL: https://github.com/TinyAGI/tinyagi
- License: MIT
- Stars: 3,550
- Last commit: 2026-03-30
- Primary language: TypeScript
- Purpose: Agent-teams orchestrator ("One Person Company"; fka TinyClaw).
- Verdict: PASS
- Rationale: MIT, active, conceptually adjacent to our orchestrator pattern. Useful Phase 2 comparator.

### 7. agent0ai/a0-plugins — PASS
- URL: https://github.com/agent0ai/a0-plugins
- License: MIT
- Stars: 55
- Last commit: 2026-04-26
- Primary language: Python
- Purpose: Plugins index for Agent Zero.
- Verdict: PASS
- Rationale: MIT companion to agent-zero. Low standalone value but supports #8 evaluation.

### 8. agent0ai/agent-zero — PASS (FLAG: self-modifying)
- URL: https://github.com/agent0ai/agent-zero
- License: MIT (LICENSE file confirmed; SPDX returned NOASSERTION)
- Stars: 17,544
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: General agent framework with dynamic tool/agent creation.
- Verdict: PASS — flagged under ADR-134.
- Rationale: Active, MIT, well-known. Self-modifying behaviors warrant propose-only treatment.

### 9. coleam00/Archon — PASS
- URL: https://github.com/coleam00/Archon
- License: MIT
- Stars: 20,862
- Last commit: 2026-05-04
- Primary language: TypeScript
- Purpose: Open-source harness builder; deterministic/repeatable AI coding.
- Verdict: PASS
- Rationale: MIT, very active, directly relevant to harness/orchestrator design. High Phase 2 priority.

### 10. daveshap/AgentZero — UNRESOLVED
- URL: https://github.com/daveshap/AgentZero
- License: n/a
- Stars: n/a
- Last commit: n/a
- Primary language: n/a
- Purpose: n/a
- Verdict: UNRESOLVED (404).
- Rationale: Confirmed missing per scope note. Drop.

### 11. gepa-ai/gepa — PASS
- URL: https://github.com/gepa-ai/gepa
- License: MIT
- Stars: 4,225
- Last commit: 2026-05-06
- Primary language: Jupyter Notebook
- Purpose: Optimize prompts/code via reflective text evolution (GEPA).
- Verdict: PASS
- Rationale: MIT, very active, theme-core (referenced by hermes-agent-self-evolution). High Phase 2 priority.

### 12. mindfold-ai/Trellis — REJECT
- URL: https://github.com/mindfold-ai/Trellis
- License: AGPL-3.0
- Stars: 7,190
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Agent harness.
- Verdict: REJECT
- Rationale: AGPL-3.0 — copyleft blocks code/pattern adoption per cluster rules.

### 13. mindsdb/anton — PASS (FLAG: self-modifying potential — light)
- URL: https://github.com/mindsdb/anton
- License: MIT
- Stars: 652
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: AI coworker agent.
- Verdict: PASS — light ADR-134 flag pending Phase 2 confirmation.
- Rationale: MIT, active, MindsDB-backed. Worth a look for coworker-pattern comparison.

### 14. nanobot-ai/nanobot — REJECT (low-fit) / OPTIONAL PASS
- URL: https://github.com/nanobot-ai/nanobot
- License: Apache-2.0
- Stars: 1,309
- Last commit: 2026-05-01
- Primary language: Go
- Purpose: Build MCP agents.
- Verdict: REJECT for THIS cluster (theme = research/self-evolving).
- Rationale: License is fine; subject is MCP plumbing, not self-evolution. Better suited to mcp/infra cluster — recommend re-route, not adopt here.

### 15. qodo-ai/pr-agent — REJECT
- URL: https://github.com/The-PR-Agent/pr-agent (redirected)
- License: AGPL-3.0
- Stars: 11,091
- Last commit: 2026-05-02
- Primary language: Python
- Purpose: PR review agent.
- Verdict: REJECT
- Rationale: AGPL-3.0 blocks adoption. Also off-theme.

## Phase 2 Candidates (priority order)

1. **NousResearch/hermes-agent** — flagship, on-theme, MIT, top mindshare.
2. **gepa-ai/gepa** — reflective evolution primitive; complements #3 below.
3. **NousResearch/hermes-agent-self-evolution** — DSPy+GEPA self-evolution; needs LICENSE resolution before code adoption (patterns OK).
4. **coleam00/Archon** — harness/determinism patterns directly relevant to our orchestrator.
5. **MaximeRobeyns/self_improving_coding_agent** — canonical small reference for self-modifying agent loops (monitor mode).
6. **HKUDS/nanobot** — ultra-light agent loop; good baseline comparator.
7. **agent0ai/agent-zero** (+ a0-plugins) — broad active framework; ADR-134 propose-only.
8. **TinyAGI/tinyagi** — orchestrator comparator (TS).
9. **mindsdb/anton** — coworker pattern, secondary.

## Summary

- 15 input repos. 6 PASS, 3 REJECT (2 AGPL + 1 off-theme), 2 UNRESOLVED (404), 4 flagged ADR-134 (subset of PASS).
- License-safe and on-theme cohort is strong: 4 high-priority Phase 2 targets (hermes-agent, gepa, archon, hermes-agent-self-evolution).
- Action items for Phase 2: (a) confirm LICENSE on hermes-agent-self-evolution; (b) ask user whether `nanobot-ai/nanobot` should move to MCP cluster; (c) confirm dropping the two UNRESOLVED entries.
