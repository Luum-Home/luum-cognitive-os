---
cluster: memory-vector
date: 2026-05-06
phase: shallow
total_repos: 11
adopt: 0
poc: 2
monitor: 5
reject: 4
counts_sum_check: 11
---

# Cluster: memory-vector — Shallow Audit (2026-05-06)

Theme: agent memory / vector stores / context compression. COS already runs Engram (Gentleman-Programming/engram) as primary memory; duplicates of that primitive default to `monitor`. ADR-134 propose-only flag applies: any repo where the agent self-modifies its own memory without operator gate is flagged.

---

## Repos

### 1. MemPalace/mempalace
- URL: https://github.com/MemPalace/mempalace
- License: MIT
- Stars: 51,256
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Open-source AI memory system, self-described as best-benchmarked.
- Verdict: **poc**
- Rationale: MIT, very actively developed, large community signal. Duplicates Engram primitive but the benchmark-leading claim warrants a Phase 2 deep-dive to compare retrieval quality vs Engram and harvest scoring/eviction patterns.

### 2. Mibayy/token-savior
- URL: https://github.com/Mibayy/token-savior
- License: MIT
- Stars: 799
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: MCP server combining structural code navigation with persistent memory; claims -77% tokens on Claude Opus 4.7.
- Verdict: **poc**
- Rationale: MIT, MCP-native, claims align with COS token-economy goals (rule §4). Different angle than Engram (code-structure-aware). Worth Phase 2 to validate benchmark claims and evaluate MCP-server design for adoption as a sidecar.

### 3. Mirix-AI/MIRIX
- URL: https://github.com/Mirix-AI/MIRIX
- License: Apache-2.0
- Stars: 3,533
- Last commit: 2026-04-28
- Primary language: Python
- Purpose: Multi-agent personal assistant that watches screen activity and consolidates it into structured memory.
- Verdict: **monitor**
- Rationale: Apache-2.0 OK, but the screen-capture/personal-assistant scope is orthogonal to COS. ADR-134 concern: agent self-consolidates memory autonomously — would need propose-only gate to fit COS. Track for memory-consolidation patterns only.

### 4. basicmachines-co/basic-memory
- URL: https://github.com/basicmachines-co/basic-memory
- License: AGPL-3.0
- Stars: 2,981
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Persistent conversation memory for AI assistants.
- Verdict: **reject**
- Rationale: AGPL-3.0 blocked by license-policy (rule §10). Patterns may be studied clean-room only; no code adoption.

### 5. egdev6/engram-monitor
- URL: https://github.com/egdev6/engram-monitor
- License: NONE (no LICENSE file)
- Stars: 36
- Last commit: 2026-04-25
- Primary language: TypeScript
- Purpose: Dashboard to monitor Engram events.
- Verdict: **monitor**
- Rationale: Directly complements COS Engram. Unlicensed — cannot adopt code. Worth tracking for UI ideas; reach out to author to add a permissive license. If licensed, could become an `adopt`.

### 6. letta-ai/letta
- URL: https://github.com/letta-ai/letta
- License: Apache-2.0
- Stars: 22,449
- Last commit: 2026-04-12
- Primary language: Python
- Purpose: Platform for stateful agents with advanced memory and self-improvement.
- Verdict: **monitor**
- Rationale: Apache-2.0 OK and category-leading, but full agent platform overlaps with COS scope, not just memory. ADR-134 concern: self-improvement loop requires operator gate. Track patterns (memory blocks, archival memory schema) for inspiration; do not adopt as a dependency.

### 7. lhr-present/tokenshrink
- URL: https://github.com/lhr-present/tokenshrink
- License: NONE (no LICENSE file)
- Stars: 3
- Last commit: 2026-04-06
- Primary language: JavaScript
- Purpose: Local prompt compression CLI / MCP / browser extension, claims 30-60% reduction.
- Verdict: **reject**
- Rationale: Unlicensed → cannot legally adopt or fork code. Tiny user base, no signal of durability. Caveman-compress skill already exists in COS for this niche.

### 8. memvid/memvid
- URL: https://github.com/memvid/memvid
- License: Apache-2.0
- Stars: 15,349
- Last commit: 2026-03-16
- Primary language: Rust
- Purpose: Serverless single-file memory layer to replace RAG pipelines.
- Verdict: **monitor**
- Rationale: Apache-2.0 OK, strong stars, Rust implementation. Duplicates Engram primitive; "no delta" today. Track for the single-file portable memory format — possibly relevant to ADR-141 (Engram Cloud replication transport). Slowing commit cadence (last push >6 weeks).

### 9. rohitg00/agentmemory
- URL: https://github.com/rohitg00/agentmemory
- License: Apache-2.0
- Stars: 2,215
- Last commit: 2026-04-29
- Primary language: TypeScript
- Purpose: Persistent memory for AI coding agents, benchmark-driven.
- Verdict: **monitor**
- Rationale: Apache-2.0 OK, active. Direct overlap with Engram in the coding-agent niche — duplicates engram primitive, no clear delta vs current COS setup. Track benchmark methodology for Engram self-eval.

### 10. thedotmack/claude-mem
- URL: https://github.com/thedotmack/claude-mem
- License: AGPL-3.0
- Stars: 72,605
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Claude Code plugin that auto-captures sessions, compresses with agent-sdk, injects context next session.
- Verdict: **reject**
- Rationale: AGPL-3.0 blocked by license-policy. Note: input list pointed at sethlford/claude-mem (404); canonical project is thedotmack/claude-mem, confirmed AGPL via LICENSE file. Cannot fork or adopt code. ADR-134 concern: agent auto-modifies its own memory store, would require propose-only gate even if licensable.

### 11. syntax-syndicate/engram-agent-memory
- URL: https://github.com/syntax-syndicate/engram-agent-memory
- License: MIT
- Stars: 0
- Last commit: 2026-03-10
- Primary language: Go
- Purpose: Go binary memory system with SQLite+FTS5, MCP server, HTTP API, CLI, TUI.
- Verdict: **reject**
- Rationale: Zero stars, last commit 2 months ago, name-collides with the canonical Gentleman-Programming/engram already in use. No external signal of durability. MIT is fine but adoption value is near zero given the Engram we already run.

---

## Phase 2 Candidates

1. **MemPalace/mempalace** — benchmark-led memory system (MIT). Deep-read scoring/eviction strategy and benchmark harness; compare to Engram retrieval quality.
2. **Mibayy/token-savior** — MCP token-savings claims (MIT). Validate -77% claim, reverse-engineer structural code-nav + memory hybrid; potential sidecar.

Both are MIT, both align with COS rules (token-economy §4, license-policy §10) and offer a non-overlapping angle vs current Engram baseline.

---

## Counts (verified)
- adopt: 0
- poc: 2 (MemPalace/mempalace, Mibayy/token-savior)
- monitor: 5 (Mirix-AI/MIRIX, egdev6/engram-monitor, letta-ai/letta, memvid/memvid, rohitg00/agentmemory)
- reject: 4 (basicmachines-co/basic-memory [AGPL], lhr-present/tokenshrink [unlicensed], thedotmack/claude-mem [AGPL], syntax-syndicate/engram-agent-memory [no signal])
- TOTAL: 11 ✓
