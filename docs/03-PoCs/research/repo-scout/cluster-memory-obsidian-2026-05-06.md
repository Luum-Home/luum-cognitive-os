---
cluster: memory-obsidian
date: 2026-05-06
phase: shallow
theme: Obsidian-related memory / RAG / wiki integrations
adr_context: ADR-172 (Obsidian as candidate UI surface — bridges between Obsidian vaults and memory/RAG layers have higher relevance)
totals:
  input: 8
  evaluated: 8
  pass: 5
  reject: 3
  phase2_candidates: 4
license_policy:
  allow: [MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC]
  reject: [AGPL, SSPL, BSL, FSL, Elastic-2.0, source-available-field-restricted]
---

# Cluster: memory-obsidian (shallow scout)

Eight Obsidian-adjacent memory/RAG/wiki repositories evaluated for fit with ADR-172 (Obsidian as candidate UI surface for COS memory). Triage prioritizes repos that bridge Obsidian vaults to a structured memory layer (RAG, knowledge graph, or MCP) with permissive licenses.

## Per-repo verdicts

### 1. Ar9av/obsidian-wiki — PASS
- URL: https://github.com/Ar9av/obsidian-wiki
- License: MIT
- Stars: 973
- Last commit: 2026-05-06
- Primary language: Python
- Purpose: Framework for AI agents to build and maintain an Obsidian wiki using Karpathy's LLM Wiki pattern.
- Verdict: PASS — Phase 2 candidate
- Rationale: Active, MIT, directly bridges agent output -> Obsidian vault. Strong fit for ADR-172: a reference for "agents writing to Obsidian as memory surface". Karpathy LLM-Wiki pattern is reusable for COS session digests.

### 2. Pratiyush/llm-wiki — PASS
- URL: https://github.com/Pratiyush/llm-wiki
- License: MIT
- Stars: 226
- Last commit: 2026-04-30
- Primary language: Python
- Purpose: LLM-powered knowledge base built from Claude Code / Codex / Cursor / Gemini sessions (Karpathy's LLM-Wiki).
- Verdict: PASS — Phase 2 candidate (high relevance)
- Rationale: Highest direct overlap with COS use case — turns coding-agent transcripts into a wiki. MIT, recent activity. Even if not Obsidian-native, the session->wiki pipeline is exactly what ADR-172 contemplates layering on Obsidian.

### 3. Vasallo94/ObsidianRAG — PASS
- URL: https://github.com/Vasallo94/ObsidianRAG
- License: MIT
- Stars: 66
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: RAG over Obsidian notes with LangGraph and local Ollama LLMs.
- Verdict: PASS — Phase 2 candidate
- Rationale: Local-first RAG against an Obsidian vault — aligns with COS air-gapped/local stance (ADR-142). Small but recent; useful as a reference implementation for vault-as-corpus retrieval.

### 4. brianpetro/obsidian-smart-connections — REJECT
- URL: https://github.com/brianpetro/obsidian-smart-connections
- License: "Smart Plugins License Agreement" (custom, field-restricted; GitHub reports NOASSERTION/Other)
- Stars: 4944
- Last commit: 2026-05-05
- Primary language: JavaScript
- Purpose: Obsidian plugin for chat-with-notes and AI-embedding link discovery.
- Verdict: REJECT
- Rationale: Custom source-available license forbids use as a "substantial component" of any general-purpose product that interoperates with Obsidian and competes with the licensor. This is a field-of-use restriction in the same family as BSL/FSL/Elastic-2.0 (rejected by policy). High-quality codebase, but unsafe to adopt code or patterns into a product offering.

### 5. drewburchfield/obsidian-graph — PASS
- URL: https://github.com/drewburchfield/obsidian-graph
- License: MIT
- Stars: 10
- Last commit: 2026-04-03
- Primary language: Python
- Purpose: Semantic knowledge graph navigation for Obsidian/markdown vaults using vector embeddings + PostgreSQL/pgvector.
- Verdict: PASS — Phase 2 candidate (low priority)
- Rationale: MIT and pgvector-backed (matches existing Engram infra). Tiny audience but architecturally close to memory-graph cluster. Worth a deep look only if Phase 2 capacity remains after the higher-signal candidates.

### 6. Epistates/turbovault — PASS
- URL: https://github.com/epistates/turbovault
- License: MIT
- Stars: 119
- Last commit: 2026-05-01
- Primary language: Rust
- Purpose: Markdown/OFM SDK plus MCP server that turns an Obsidian vault into an addressable knowledge system.
- Verdict: PASS — Phase 2 candidate (high relevance)
- Rationale: MCP-native bridge between Obsidian and LLM tooling — directly relevant to ADR-172 surface design and to the cluster-mcp-extensions theme. Rust SDK is reusable. Strongest "Obsidian + memory + agent toolchain" fit in the cluster.

### 7. garrytan/gbrain — REJECT
- URL: https://github.com/garrytan/gbrain
- License: MIT
- Stars: 13305
- Last commit: 2026-05-06
- Primary language: TypeScript
- Purpose: Personal opinionated agent "brain" wrapping OpenClaw/Hermes (not Obsidian-specific).
- Verdict: REJECT (off-theme)
- Rationale: License OK and very active, but the repo is a personal agent stack with no Obsidian integration in scope — belongs in agent-orchestration / agent-wrappers clusters, not memory-obsidian. Star count likely reflects author profile, not memory-bridge utility.

### 8. gnekt/My-Brain-Is-Full-Crew — REJECT
- URL: https://github.com/gnekt/My-Brain-Is-Full-Crew
- License: MIT (confirmed via LICENSE file; classifier reported NOASSERTION/Other)
- Stars: 3001
- Last commit: 2026-04-12
- Primary language: Shell
- Purpose: Personal "second brain" CrewAI setup spanning knowledge / nutrition / mental wellness.
- Verdict: REJECT (off-theme)
- Rationale: Personal life-management crew, not an Obsidian/memory bridge. Shell-driven CrewAI scaffolding offers no reusable pattern for COS memory or ADR-172. License is fine; relevance is not.

## Phase 2 candidates (priority order)
1. **Pratiyush/llm-wiki** — session-transcript -> wiki pipeline (closest to COS use case).
2. **Epistates/turbovault** — MCP + Obsidian + Rust SDK (ADR-172 surface, MCP cluster overlap).
3. **Ar9av/obsidian-wiki** — agent-maintained Obsidian wiki reference.
4. **Vasallo94/ObsidianRAG** — local-first RAG over vaults (ADR-142 air-gapped fit).
5. (optional) **drewburchfield/obsidian-graph** — pgvector graph; only if Phase 2 budget remains.

## Notes
- One license edge case: `brianpetro/obsidian-smart-connections` ships a custom "Smart Plugins License" with a competition/field-of-use clause. Treated as policy-equivalent to BSL/FSL and rejected.
- Two repos showed `NOASSERTION` from the GitHub classifier; LICENSE files were inspected directly. `My-Brain-Is-Full-Crew` is plain MIT; `obsidian-smart-connections` is the restricted custom license above.
- No archived repos in the cluster.
