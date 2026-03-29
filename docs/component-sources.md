# Component Sources

> Last updated: 2026-03-29

All external sources of skills, rules, hooks, tools, research, and infrastructure components referenced or integrated into luum-agent-os (Cognitive OS).

## Skills (External)

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Trail of Bits Security Skills | [trailofbits/skills](https://github.com/trailofbits/skills) | CC-BY-SA-4.0 | 62 security audit skills (static analysis, variant analysis, insecure defaults, supply chain, smart contracts, agentic actions) | OPTIONAL -- installed via `scripts/install-tob-skills.sh` as git submodule to `.claude/plugins/trailofbits-skills/` |
| Antigravity Awesome Skills | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | MIT | 1,331+ agentic skills for Claude Code/Cursor/Codex CLI/Gemini CLI | EVALUATED -- see evaluation below |

## Security Tools

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Aguara | [garagon/aguara](https://github.com/garagon/aguara) | Apache-2.0 | Deterministic security scanner (189 rules, 14 threat categories) | OPTIONAL -- `hooks/aguara-scan.sh`, `packages/aguara-security/` |
| mcp-aguara | [garagon/mcp-aguara](https://github.com/garagon/mcp-aguara) | MIT | MCP server for aguara (5 tools: scan, validate, list rules, explain, discover) | OPTIONAL -- MCP server config |
| Semgrep | [semgrep/semgrep](https://github.com/semgrep/semgrep) | OSS | SAST scanner + `p/ai-best-practices` ruleset (58 AI rules) | OPTIONAL -- `hooks/semgrep-scan.sh` |
| Parry Guard | [vaporif/parry](https://github.com/vaporif/parry) | OSS | ML-based prompt injection detection (DeBERTa transformers, Rust) | OPTIONAL -- `hooks/parry-scan.sh` |
| Garak | [NVIDIA/garak](https://github.com/NVIDIA/garak) | Apache-2.0 | LLM vulnerability scanner (179 probes: hallucination, data leakage, injection, toxicity) | OPTIONAL -- `skills/vulnerability-scan/` |
| Promptfoo | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) | MIT | LLM red team testing for agent prompts | PLANNED -- `skills/red-team/` |
| MCP-Scan | [invariantlabs/mcp-scan](https://github.com/invariantlabs/mcp-scan) | OSS | MCP server configuration scanner (tool poisoning, injection) | PLANNED -- `hooks/mcp-scan.sh` |
| NeMo Guardrails | [NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) | Apache-2.0 | PII detection, content filtering runtime service | OPTIONAL -- Docker container |

## Testing Tools

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Tero | [garagon/tero](https://github.com/garagon/tero) | Apache-2.0 | HTTP testing with chaos engineering (fault injection, latency, connection drops) | WATCH -- `packages/tero-testing/` |
| Mantis | [garagon/mantis](https://github.com/garagon/mantis) | Apache-2.0 | HTTP security scanning (OWASP, headers, TLS) | WATCH -- `packages/mantis-security/` |
| DeepEval | [confident-ai/deepeval](https://github.com/confident-ai/deepeval) | Apache-2.0 | LLM evaluation framework | Listed in NOTICE, used for testing |
| RAGAS | [explodinggradients/ragas](https://github.com/explodinggradients/ragas) | Apache-2.0 | RAG evaluation framework | Listed in NOTICE |
| testcontainers-python | [testcontainers/testcontainers-python](https://github.com/testcontainers/testcontainers-python) | Apache-2.0 | Containerized test infrastructure | Listed in NOTICE |

## Infrastructure Services (Docker)

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Langfuse | [langfuse/langfuse](https://github.com/langfuse/langfuse) | MIT (core) | LLM observability, tracing, metrics | ACTIVE -- `docker-compose.cognitive-os.yml` |
| LiteLLM | [BerriAI/litellm](https://github.com/BerriAI/litellm) | MIT | LLM proxy and model routing | ACTIVE -- Docker container |
| Paperclip | N/A | N/A | Governance and compliance dashboard | ACTIVE -- Docker container |
| ClickHouse | [ClickHouse/ClickHouse](https://github.com/ClickHouse/ClickHouse) | Apache-2.0 | Analytics database (Langfuse backend) | ACTIVE -- Docker dependency |
| SeaweedFS | [seaweedfs/seaweedfs](https://github.com/seaweedfs/seaweedfs) | Apache-2.0 | Object storage (Langfuse backend) | ACTIVE -- Docker dependency |
| Opik | [comet-ml/opik](https://github.com/comet-ml/opik) | Apache-2.0 | LLM tracing backend (observability profile) | OPTIONAL -- Docker profile `observability` |
| Cognee | [topoteretes/cognee](https://github.com/topoteretes/cognee) | Apache-2.0 | Knowledge graph and RAG engine | OPTIONAL -- Docker profile `memory` |
| Crawl4AI | [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | Apache-2.0 | Web crawling for AI | Listed in NOTICE |

## Communication/Coordination Tools

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Hcom | N/A | N/A | Cross-terminal agent communication (SQLite + TCP) | OPTIONAL -- `packages/ecosystem-tools/rules/hcom-integration.md` |
| Repomix | [yamadashy/repomix](https://github.com/yamadashy/repomix) | MIT | Repository context packing with tree-sitter compression | OPTIONAL -- `packages/ecosystem-tools/rules/repomix-integration.md` |

## Under Evaluation

| Source | URL | License | What | Status |
|--------|-----|---------|------|--------|
| LlamaFirewall | [meta-llama/PurpleLlama](https://github.com/meta-llama/PurpleLlama) | MIT | Multi-layer AI security framework (PromptGuard, CodeShield, Llama Guard) | EVALUATE |
| AgentGateway | [agentgateway/agentgateway](https://github.com/agentgateway/agentgateway) | Apache-2.0 | AI-native proxy for MCP/A2A with RBAC | EVALUATE |
| OneCLI | [onecli/onecli](https://github.com/onecli/onecli) | OSS (Rust) | Agent credential vault (AES-256-GCM, per-agent scoping) | EVALUATE |
| Agentic Radar (SPLX AI) | N/A | N/A | Agent workflow visualizer and risk analyzer | WATCH |
| skill-scanner (Cisco AI Defense) | N/A | N/A | AI agent skill security scanner | WATCH |

## Research and Design Influences

| Source | Reference | What We Adopted |
|--------|-----------|-----------------|
| Tactical Agentic Coding (IndyDevDan) | [agenticengineer.com](https://agenticengineer.com) | Closed-loop prompts (success criteria + verification + fallback), Agent Experts pattern (Act/Learn/Reuse) |
| BMAD Method v6 | Competitive landscape reference | 9 patterns adopted: adversarial review, step files, agent sidecars, implementation readiness gate, dual-search, agent customization, prompt composition |
| OpenClaw | Gateway architecture reference | Fault tolerance model (4-tier resilience: connection, LLM call, context, agent) |
| WISC Framework (Cole Medin) | [coleam00/context-engineering-intro](https://github.com/coleam00/context-engineering-intro) | Context management thresholds, cognitive load monitoring |
| arxiv 2507.11538 | LLM instruction following limits | >150 instructions degrade performance; drives capability levels and context optimization |
| arxiv 2602.11988 (ETH Zurich) | Evaluating AGENTS.md | Context files reduce task success rates; validates adaptive bypass |
| awesome-claude-code | Ecosystem reference | 114+ tools surveyed for package manager design |

## Awesome Lists and Curated Collections

| Source | Reference | How Used |
|--------|-----------|----------|
| awesome-claude-code | Referenced in `docs/package-manager-design.md` | Surveyed 114+ tools to inform cos package manager design |
| Antigravity Awesome Skills | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) | Evaluated as potential skill source (see evaluation below) |

---

## Evaluation: Antigravity Awesome Skills

**Repository**: [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)

### Overview

| Metric | Value |
|--------|-------|
| Stars | 28,344 |
| Forks | 4,755 |
| License | MIT |
| Language | Python (installer), Markdown (skills) |
| Last pushed | 2026-03-29 (actively maintained) |
| Created | 2026-01-14 |
| Skill count | 1,331+ (1,000+ in skills/ directory) |
| Description | Installable library of agentic skills for Claude Code, Cursor, Codex CLI, Gemini CLI |

### What It Contains

- 1,331+ SKILL.md playbooks organized by category
- NPM-based CLI installer (`antigravity-awesome-skills`)
- Role-based bundles (Essentials, Web Wizard, Security Engineer)
- Web app for browsing/searching the catalog
- Skills index (CATALOG.md, skills_index.json)

### Sample Skill Categories

Development: brainstorming, architecture, test-driven-development, debugging-strategies, api-design-principles, frontend-design, android-jetpack-compose, 3d-web-experience

Security: security-auditor, active-directory-attacks, agentic-actions-auditor

AI/Agent: agent-orchestration, agent-memory-systems, agent-evaluation, ai-agent-development, ai-engineering-toolkit

Product/Marketing: ai-seo, ad-creative, ab-test-setup, analytics-tracking, affiliate-marketing

Infrastructure: airflow-dag-patterns, algolia-search, airtable-automation, activecampaign-automation

### License Compatibility

MIT -- fully compatible with Cognitive OS. No copyleft concerns.

### Quality Assessment

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Maintenance | HIGH | Updated daily, 28K+ stars, active community |
| Breadth | HIGH | 1,331+ skills across many domains |
| Depth | VARIABLE | Community-contributed; quality varies per skill |
| COS overlap | MODERATE | Several skills overlap with our existing capabilities (TDD, debugging, security audit, architecture) |
| Format compatibility | HIGH | Uses SKILL.md format compatible with Claude Code |

### Useful Skills for COS (Not Currently Covered)

| Skill | Why Useful |
|-------|-----------|
| `agent-memory-systems` | Could complement our Engram patterns |
| `agent-orchestration` | Cross-reference with our orchestrator rules |
| `agentic-actions-auditor` | Overlaps with Trail of Bits but from a different angle |
| `api-design-principles` | We lack an API design skill |
| `SPDD` | Spec-driven development -- compare with our SDD |
| `rehabilitation-analyzer` | Domain-specific skill example |

### Integration Recommendation

**Status: WATCH -- selective adoption**

Do NOT bulk-install. Reasons:
1. 1,331 skills would overwhelm our progressive loading system (max 5 active skills)
2. Variable quality requires individual review
3. Many skills are domain-specific (marketing, SEO, crypto) with no COS relevance
4. Our existing skills are deeply integrated with COS hooks, rules, and Engram

**Recommended approach**:
1. Cherry-pick 5-10 high-quality skills that fill gaps in our catalog
2. Install as a cos package under `packages/antigravity-skills/` with only selected skills
3. Adapt selected skills to use our quality gates, trust scoring, and Engram integration
4. Reference as a skill discovery source in `packages/ecosystem-tools/skills/tool-discovery/`

### How to Install (if desired)

```bash
# Cherry-pick individual skills
npx antigravity-awesome-skills install --claude --skills api-design-principles,agent-memory-systems

# Or clone and copy specific skills manually
git clone https://github.com/sickn33/antigravity-awesome-skills.git /tmp/antigravity
cp /tmp/antigravity/skills/api-design-principles/SKILL.md .claude/skills/api-design-principles/SKILL.md
```
