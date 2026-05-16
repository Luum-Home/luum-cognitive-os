---
cluster: dev-tools-cli
date: 2026-05-06
phase: shallow
theme: "Non-interactive CLI dev tools (linters, parsers, packagers, fuzzy finders)"
total_repos: 17
adopt: 0
phase2: 4
monitor: 5
reject: 8
---

# Cluster: dev-tools-cli — Shallow Audit (2026-05-06)

## Repos

### 1. DavidAnson/markdownlint-cli2
- URL: https://github.com/DavidAnson/markdownlint-cli2
- License: MIT
- Stars: 786
- Last commit: 2026-05-05
- Primary language: JavaScript
- Purpose: Fast, configuration-based CLI for linting Markdown/CommonMark files.
- Verdict: **monitor**
- Rationale: Already adopted (markdownlint family). Deep-audit only if new feature relevant.

### 2. JuliusBrussee/caveman
- URL: https://github.com/JuliusBrussee/caveman
- License: MIT
- Stars: 54683
- Last commit: 2026-05-01
- Primary language: Python
- Purpose: Token-compression skill for Claude Code (~65% token reduction via caveman speech).
- Verdict: **monitor**
- Rationale: Already integrated as `caveman` skill. Track upstream.

### 3. aimasteracc/tree-sitter-analyzer
- URL: https://github.com/aimasteracc/tree-sitter-analyzer
- License: MIT
- Stars: 31
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: Multi-language code analysis CLI/MCP server built on tree-sitter.
- Verdict: **phase2**
- Rationale: MIT, MCP-shaped, complements existing repomix/forensics. Low stars but recent + active. Worth deep-audit for AST-driven analysis primitives.

### 4. akavel/up
- URL: https://github.com/akavel/up
- License: Apache-2.0
- Stars: 8831
- Last commit: 2024-09-05
- Primary language: Go
- Purpose: Ultimate Plumber — interactive live-preview pipe writer.
- Verdict: **reject**
- Rationale: INTERACTIVE TUI (theme is non-interactive CLI). Stale (>1y). Not aligned.

### 5. github/markdownlint-github
- URL: https://github.com/github/markdownlint-github
- License: MIT
- Stars: 93
- Last commit: 2026-05-05
- Primary language: JavaScript
- Purpose: Opinionated markdownlint rule pack used by GitHub.
- Verdict: **phase2**
- Rationale: MIT, drop-in rule pack for our existing markdownlint-cli2. Cheap audit, possible immediate adoption as docs-quality preset.

### 6. gptscript-ai/gptscript
- URL: https://github.com/gptscript-ai/gptscript
- License: Apache-2.0
- Stars: 3279
- Last commit: 2026-04-10
- Primary language: Go
- Purpose: DSL/runtime for building AI assistants that interact with systems.
- Verdict: **reject**
- Rationale: Not a dev-tools-CLI per cluster theme; agent-runtime overlaps with our own orchestrator. Out of scope.

### 7. junegunn/fzf
- URL: https://github.com/junegunn/fzf
- License: MIT
- Stars: 79999
- Last commit: 2026-05-05
- Primary language: Go
- Purpose: Command-line fuzzy finder.
- Verdict: **monitor**
- Rationale: Foundational tool; almost certainly already on developer machines. Primarily interactive — not a programmatic primitive for agents. Track only.

### 8. koalaman/shellcheck-precommit
- URL: https://github.com/koalaman/shellcheck-precommit
- License: GPL-3.0 (LICENSE file confirmed; GH SPDX = NOASSERTION due to disclaimer prefix)
- Stars: 124
- Last commit: 2025-08-04
- Primary language: Shell
- Purpose: Pre-commit hook wrapper for ShellCheck.
- Verdict: **reject**
- Rationale: GPL-3.0 license. Although hook is mostly YAML/wrapper, policy is to avoid GPL adoption. We already invoke shellcheck directly per ADR-066/§14; replicating the trivial pre-commit YAML in-house avoids the GPL surface.

### 9. littlebearapps/untether
- URL: https://github.com/littlebearapps/untether
- License: MIT
- Stars: 44
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Telegram bridge for Claude Code/Codex/etc — remote control of coding agents.
- Verdict: **reject**
- Rationale: Off-theme (not a CLI dev tool — it's an agent transport). Niche, low adoption. Spawn-task material if remote-control becomes a goal.

### 10. lycheeverse/lychee
- URL: https://github.com/lycheeverse/lychee
- License: Apache-2.0
- Stars: 3563
- Last commit: 2026-05-05
- Primary language: Rust
- Purpose: Fast async link checker for Markdown/HTML/RST/websites.
- Verdict: **monitor**
- Rationale: Already adopted (RULES-COMPACT mentions lychee). Deep-audit only if new feature relevant.

### 11. lycheeverse/lychee-action
- URL: https://github.com/lycheeverse/lychee-action
- License: Apache-2.0
- Stars: 484
- Last commit: 2026-05-04
- Primary language: Shell
- Purpose: GitHub Action wrapper for lychee.
- Verdict: **monitor**
- Rationale: Companion to already-adopted lychee. Adopt-on-need if we wire link checking into CI.

### 12. repowise-dev/repowise
- URL: https://github.com/repowise-dev/repowise
- License: AGPL-3.0 (confirmed in LICENSE; GH SPDX = NOASSERTION)
- Stars: 1395
- Last commit: 2026-05-03
- Primary language: Python
- Purpose: Codebase intelligence (auto-docs, git analytics, dead-code) via MCP.
- Verdict: **reject**
- Rationale: AGPL-3.0 — license-policy BLOCK (RULES-COMPACT §10). Patterns may be studied (clean-room) but no code adoption.

### 13. seaweedfs/seaweedfs
- URL: https://github.com/seaweedfs/seaweedfs
- License: Apache-2.0
- Stars: 32096
- Last commit: 2026-05-06
- Primary language: Go
- Purpose: Distributed object/file/Iceberg storage system.
- Verdict: **reject**
- Rationale: Off-theme (storage system, not dev-tool CLI). No fit for this cluster.

### 14. superset-sh/superset
- URL: https://github.com/superset-sh/superset
- License: Elastic-2.0 (confirmed in LICENSE.md; GH SPDX = NOASSERTION)
- Stars: 10369
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Code editor for orchestrating fleets of Claude Code/Codex agents.
- Verdict: **reject**
- Rationale: ELv2 — license-policy BLOCK (RULES-COMPACT §10 lists BSL; Elastic-2.0 is similarly source-available with hosted-service restriction, not OSI-approved). Watchlist-confirmed reject.

### 15. tree-sitter/tree-sitter
- URL: https://github.com/tree-sitter/tree-sitter
- License: MIT
- Stars: 25192
- Last commit: 2026-05-05
- Primary language: Rust
- Purpose: Incremental parsing system for programming tools.
- Verdict: **phase2**
- Rationale: Foundational MIT primitive. Direct upstream of #3 (tree-sitter-analyzer). Worth deep audit for embedding parsers in agent skills (AST-aware diffs, refactors).

### 16. volcengine/OpenViking
- URL: https://github.com/volcengine/OpenViking
- License: AGPL-3.0
- Stars: 23503
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Filesystem-paradigm context DB for AI agents (memory/resources/skills).
- Verdict: **reject**
- Rationale: AGPL-3.0 — license-policy BLOCK. Watchlist-confirmed reject. Patterns interesting (overlaps with engram), but clean-room only.

### 17. yamadashy/repomix
- URL: https://github.com/yamadashy/repomix
- License: MIT
- Stars: 24376
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Pack a repository into a single AI-friendly file for LLM ingestion.
- Verdict: **phase2**
- Rationale: Already integrated (repomix-integration in RULES-COMPACT) but warrants deep-audit for new packaging modes / token-savings beyond current usage.

## Phase 2 candidates

1. **aimasteracc/tree-sitter-analyzer** — AST-driven multi-language analysis CLI+MCP; complements forensics/repomix.
2. **github/markdownlint-github** — Drop-in rule pack for our markdownlint-cli2; possible immediate adoption.
3. **tree-sitter/tree-sitter** — Foundational MIT parser; upstream of #1; basis for AST-aware agent skills.
4. **yamadashy/repomix** — Already integrated; deep-audit for new packaging modes / advanced flags we may not exploit yet.

## Verdict counts (must sum to total_repos = 17)
- adopt: 0
- phase2: 4 (tree-sitter-analyzer, markdownlint-github, tree-sitter, repomix)
- monitor: 5 (markdownlint-cli2, caveman, fzf, lychee, lychee-action)
- reject: 8 (up [stale+interactive], gptscript [off-theme], shellcheck-precommit [GPL], untether [off-theme], repowise [AGPL], seaweedfs [off-theme], superset [Elastic-2.0], OpenViking [AGPL])
- Sum: 0+4+5+8 = 17 ✓
