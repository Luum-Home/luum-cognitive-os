---
cluster: mcp-extensions
date: 2026-05-06
phase: shallow
total_repos: 10
counts:
  pass: 4
  monitor: 0
  reject: 6
theme: "MCP servers and MCP-related extensions (vault access, code intelligence, security scanning, sandboxing)"
budget_used: ~12
---

# Cluster scout: mcp-extensions (shallow, 2026-05-06)

Counts: 10 total = 4 pass + 0 monitor + 6 reject. (Sums to 10.)

---

## 1. BeehiveInnovations/pal-mcp-server
- URL: https://github.com/BeehiveInnovations/pal-mcp-server
- License: Apache-2.0 (LICENSE file; GitHub reported NOASSERTION)
- Stars: 11,513
- Last commit: 2025-12-15
- Primary language: Python
- Purpose: Multi-model MCP bridge — Claude Code / Gemini CLI / Codex CLI talking to OpenAI/Gemini/OpenRouter/Azure/Grok/Ollama as one.
- Verdict: PASS (Phase 2)
- Rationale: High-traction (11.5k stars), permissive Apache-2.0, directly relevant to ADR-049 LLM dispatch (Qwen primary / Claude Max preserved). Worth deep-diving for cross-provider routing patterns and adapter design.

## 2. aaronsb/obsidian-mcp-plugin
- URL: https://github.com/aaronsb/obsidian-mcp-plugin
- License: MIT
- Stars: 305
- Last commit: 2026-05-04
- Primary language: TypeScript
- Purpose: High-perf MCP server for Obsidian vault access via semantic ops + HTTP transport.
- Verdict: REJECT
- Rationale: Out of scope for COS — Obsidian-specific personal-knowledge integration. No clear delta over engram for our project memory needs. Not a duplicate (different domain), but not on roadmap.

## 3. bitbonsai/mcpvault
- URL: https://github.com/bitbonsai/mcpvault
- License: NONE (no LICENSE file in repo root)
- Stars: 1,202
- Last commit: 2026-05-04
- Primary language: Astro/TypeScript
- Purpose: Lightweight MCP server for safe Obsidian vault access.
- Verdict: REJECT
- Rationale: No license = all rights reserved by default. Cannot adopt code or patterns under license-policy. Also same Obsidian-vault scope as #2, not on roadmap.

## 4. e2b-dev/mcp-server
- URL: https://github.com/e2b-dev/mcp-server
- License: Apache-2.0
- Stars: 395
- Last commit: 2026-04-16 (archived)
- Primary language: JavaScript
- Purpose: Run code via E2B sandboxes through MCP.
- Verdict: REJECT
- Rationale: Archived per cluster constraint. COS already has e2b-integration skill; archived upstream means no future maintenance.

## 5. invariantlabs/mcp-scan (canonical: snyk/agent-scan)
- URL: https://github.com/snyk/agent-scan
- License: Apache-2.0
- Stars: 2,347
- Last commit: 2026-05-05
- Primary language: Python
- Purpose: Security scanner for AI agents, MCP servers, and agent skills (post-Snyk acquisition).
- Verdict: PASS (Phase 2)
- Rationale: Canonical successor per cluster directive (invariantlabs-ai/mcp-scan acquired). Apache-2.0, active, directly aligned with COS security-scanning + pentesting-readiness rules. Strong candidate to integrate into hook security-profiles.

## 6. jgravelle/jcodemunch-mcp
- URL: https://github.com/jgravelle/jcodemunch-mcp
- License: Custom Dual-Use ("free non-commercial + paid commercial $79–$1,999")
- Stars: 1,775
- Last commit: 2026-05-04
- Primary language: Python
- Purpose: Token-efficient MCP server for GitHub source exploration via tree-sitter AST.
- Verdict: REJECT
- Rationale: Commercial-paid license tier — explicit cluster reject criterion. Luum/COS is a for-profit context, would require paid license. Patterns visible but cannot adopt code.

## 7. kuberstar/qartez-mcp
- URL: https://github.com/kuberstar/qartez-mcp
- License: Custom Dual (Qartez Small Team License + Commercial)
- Stars: 46
- Last commit: 2026-04-30
- Primary language: Rust
- Purpose: Semantic code intelligence MCP — project maps, symbol search, impact analysis for Claude Code.
- Verdict: REJECT
- Rationale: Commercial tier required outside small-team eligibility — fails permissive license gate. Functionally overlaps with COS impact-analysis skill anyway.

## 8. msdanyg/smart-connections-mcp
- URL: https://github.com/msdanyg/smart-connections-mcp
- License: MIT
- Stars: 46
- Last commit: 2025-10-13
- Primary language: JavaScript
- Purpose: MCP server for semantic search + knowledge graphs in Obsidian via Smart Connections embeddings.
- Verdict: REJECT
- Rationale: Obsidian-specific again, low stars, stale (~7 months). Not on roadmap.

## 9. sinewaveai/agent-security-scanner-mcp
- URL: https://github.com/sinewaveai/agent-security-scanner-mcp
- License: MIT
- Stars: 98
- Last commit: 2026-05-05
- Primary language: JavaScript
- Purpose: Security scanner MCP — prompt-injection firewall, package-hallucination detection (4.3M packages), 1000+ AST/taint rules, auto-fix.
- Verdict: PASS (Phase 2)
- Rationale: MIT, very active, complements snyk/agent-scan with focus on prompt-injection + package-hallucination — distinct angle. Aligns with COS supply-chain-defense + content-policy. Worth Phase 2 to compare delta vs. Snyk's offering and assess integration feasibility.

## 10. wrale/mcp-server-tree-sitter
- URL: https://github.com/wrale/mcp-server-tree-sitter
- License: MIT
- Stars: 302
- Last commit: 2026-04-15
- Primary language: Python
- Purpose: MCP server exposing Tree-sitter parsing/queries.
- Verdict: PASS (Phase 2)
- Rationale: MIT, Python (matches COS stack), foundational primitive useful for repo-forensics + reverse-engineer skills (AST-based code intelligence without commercial-license entanglement that jcodemunch/qartez carry). Clean alternative.

---

## Phase 2 candidates

1. **BeehiveInnovations/pal-mcp-server** — multi-provider LLM routing patterns for ADR-049 dispatch.
2. **snyk/agent-scan** — agent/MCP/skill security scanning, integrate with hook security-profiles.
3. **sinewaveai/agent-security-scanner-mcp** — prompt-injection firewall + package-hallucination detection; complements Snyk.
4. **wrale/mcp-server-tree-sitter** — permissive AST primitive replacing jcodemunch/qartez (rejected on license).

## Rejected summary

- e2b-dev/mcp-server (archived, per directive)
- bitbonsai/mcpvault (no license)
- aaronsb/obsidian-mcp-plugin, msdanyg/smart-connections-mcp (Obsidian-specific, off-roadmap)
- jgravelle/jcodemunch-mcp, kuberstar/qartez-mcp (commercial-paid license tier, fails license-policy)
