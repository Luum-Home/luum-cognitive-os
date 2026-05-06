---
cluster: agent-codegen
date: 2026-05-06
phase: shallow
theme: IDE-like coding agents (cursor, opencode×2, qwen-code, aider, cline, continue, codex, claude-code, roo-code, crush, kiro)
input_file: .cognitive-os/runtime/repo-scout-batch-2026-05-06/cluster-agent-codegen.txt
input_count: 13
unique_repos: 12
counts:
  total: 12
  passes_to_deep: 4
  monitor: 6
  reject: 2
notes:
  - Input contained duplicate (Aider-AI/aider == aider-ai/aider) collapsed to one entry.
  - anthropics/claude-code skipped per scope (harness host).
  - QwenLM/qwen-code already integrated (ADR-049 llm-dispatch primary) → monitor.
  - cursor/cursor is issues-only repo with no license → reject.
  - opencode-ai/opencode archived 2025-09-18 → reject.
  - Most entries are direct competitors to claude-code; verdict gates on extractable primitive, not on competition.
---

# Cluster: agent-codegen — Shallow Audit

Theme: IDE-like coding agents — terminal/IDE harnesses competing with or complementing claude-code. Filter is brutal: competitor surface alone is not enough; we only pass to deep if a specific extractable primitive (MCP integration, hook pattern, routing logic, edit/diff primitive) is visible at surface level.

## Repos

### 1. Aider-AI/aider
- URL: https://github.com/Aider-AI/aider
- License: Apache-2.0
- Stars: 44,382
- Last commit: 2026-04-25
- Primary language: Python
- One-line purpose: AI pair-programmer in the terminal with git-aware edit/commit loop.
- Triage verdict: **passes-to-deep**
- Rationale: Mature, well-engineered Python codebase with novel primitives that map directly to our concerns: repo-map context selection, search/replace edit blocks, git-aware autocommit. Apache-2.0 makes both code and patterns adoptable. Worth a deep pass to harvest edit-block format + repo-map heuristic for our agent edit primitives.

### 2. QwenLM/qwen-code
- URL: https://github.com/QwenLM/qwen-code
- License: Apache-2.0
- Stars: 24,185
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: Open-source AI coding agent for the terminal (Qwen-Coder fork of Gemini CLI).
- Triage verdict: **monitor**
- Rationale: Already integrated as ADR-049 llm-dispatch primary provider. Continued monitoring for upstream changes (auth flows, model bundle updates) is sufficient — no new extraction needed at this time.

### 3. RooCodeInc/Roo-Code
- URL: https://github.com/RooCodeInc/Roo-Code
- License: Apache-2.0
- Stars: 23,880
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: VS Code extension providing a multi-agent dev team in the editor.
- Triage verdict: **monitor**
- Rationale: Direct IDE-extension competitor (Cline fork lineage). Multi-agent coordination is interesting but our orchestration model is already more sophisticated. Monitor for novel mode/role definitions; no immediate extractable primitive at shallow depth.

### 4. affaan-m/everything-claude-code
- URL: https://github.com/affaan-m/everything-claude-code
- License: MIT
- Stars: 174,106
- Last commit: 2026-05-03
- Primary language: JavaScript
- One-line purpose: Harness performance optimization system (skills, instincts, memory, security, research-first) for Claude Code/Codex/Opencode/Cursor.
- Triage verdict: **passes-to-deep**
- Rationale: Directly overlapping problem space (harness optimization, skills, memory, research-first development). MIT-licensed, very high signal star count, claims cross-harness portability. Deep pass should compare their skills/instincts model against our skill registry and rules-compact, and their cross-harness abstraction against ADR-033 harness adapter.

### 5. anomalyco/opencode
- URL: https://github.com/anomalyco/opencode
- License: MIT
- Stars: 155,389
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: Active fork/successor of the archived opencode-ai project — open-source coding agent.
- Triage verdict: **monitor**
- Rationale: Active fork after upstream archive; competitor surface. High star count suggests momentum but TypeScript rewrite vs original Go means architectural drift. No specific primitive identified at shallow depth — monitor for MCP/tool patterns.

### 6. cline/cline
- URL: https://github.com/cline/cline
- License: Apache-2.0
- Stars: 61,399
- Last commit: 2026-05-06
- Primary language: TypeScript
- One-line purpose: Autonomous IDE coding agent with file/command/browser tool use, gated by per-step user permission.
- Triage verdict: **monitor**
- Rationale: Per-step permission gating is interesting and similar to our hook-enforced gates, but it is a UX pattern more than an extractable primitive. Direct competitor to claude-code; monitor for novel tool-permission primitives.

### 7. continuedev/continue
- URL: https://github.com/continuedev/continue
- License: Apache-2.0
- Stars: 32,990
- Last commit: 2026-05-05
- Primary language: TypeScript
- One-line purpose: Source-controlled AI checks, enforceable in CI; powered by the open-source Continue CLI.
- Triage verdict: **passes-to-deep**
- Rationale: The pivot to "AI checks enforceable in CI" is a genuinely novel primitive that maps to our quality gates and CI-enforced rules (ADR-066, language quality gates). Apache-2.0. Deep pass should examine how AI checks are defined, versioned, and gated in CI — directly relevant to our pre-commit-gate and Trust Report contracts.

### 8. cursor/cursor
- URL: https://github.com/cursor/cursor
- License: (none declared)
- Stars: 32,824
- Last commit: 2026-04-29
- Primary language: (n/a)
- One-line purpose: Public issues tracker for the proprietary Cursor IDE — no source code.
- Triage verdict: **reject**
- Rationale: Issues-only repo, no license, no extractable code. Per scout constraints, reject.

### 9. musistudio/claude-code-router
- URL: https://github.com/musistudio/claude-code-router
- License: MIT
- Stars: 33,483
- Last commit: 2026-03-04
- Primary language: TypeScript
- One-line purpose: Routing layer that lets claude-code talk to alternative model providers.
- Triage verdict: **passes-to-deep**
- Rationale: Directly relevant to ADR-049 llm-dispatch — provider routing for the same harness we run. MIT. Deep pass should compare their request transformation/auth handling against `lib/dispatch.py` and the provider bundles in `scripts/orchestrator.py`. Two-month-stale commit is a yellow flag but the surface is small enough to harvest patterns.

### 10. openai/codex
- URL: https://github.com/openai/codex
- License: Apache-2.0
- Stars: 80,221
- Last commit: 2026-05-06
- Primary language: Rust
- One-line purpose: Lightweight terminal coding agent from OpenAI.
- Triage verdict: **monitor**
- Rationale: Direct competitor harness; Rust implementation makes patterns less directly portable to our Python/Go core. Apache-2.0 means primitives are extractable in principle, but at shallow depth no specific primitive jumps out beyond generic agent loop. Monitor for novel sandbox/exec patterns Rust gives them cheaply.

### 11. opencode-ai/opencode
- URL: https://github.com/opencode-ai/opencode
- License: MIT
- Stars: 12,366
- Last commit: 2025-09-18 (**archived**)
- Primary language: Go
- One-line purpose: Original opencode terminal coding agent (now archived; superseded by anomalyco/opencode TS rewrite).
- Triage verdict: **reject**
- Rationale: Archived since 2025-09. Active successor (anomalyco/opencode) already in this batch. Reject — go to the live fork if needed.

### 12. shanraisshan/claude-code-best-practice
- URL: https://github.com/shanraisshan/claude-code-best-practice
- License: MIT
- Stars: 51,232
- Last commit: 2026-05-05
- Primary language: HTML
- One-line purpose: Practice/notes site for "vibe coding to agentic engineering" with claude-code.
- Triage verdict: **monitor**
- Rationale: HTML-only suggests docs/exercises, not source primitives. Star count is high enough to warrant occasional monitoring for emerging community patterns, but no extractable code primitive at shallow depth.

## Phase 2 Candidates

Three repos pass to deep:

1. **Aider-AI/aider** — extract: edit-block diff format, repo-map context-selection heuristic, git-aware autocommit loop. Compare against any existing edit primitives in `lib/`.
2. **affaan-m/everything-claude-code** — extract: skills/instincts/memory model, cross-harness abstraction. Compare against our skill registry, RULES-COMPACT, and ADR-033 harness adapter.
3. **continuedev/continue** — extract: AI-checks-as-CI primitive, definition format, CI integration shape. Map to our pre-commit-gate, Trust Report, and ADR-066 language quality gates.
4. **musistudio/claude-code-router** — extract: provider routing transforms and auth handling. Compare against `lib/dispatch.py` and `scripts/orchestrator.py` provider bundles for ADR-049.

(Four candidates flagged; operator may trim before Phase 2 launch.)
