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

## Agent Frameworks

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Agent Zero | [agent0ai/agent-zero](https://github.com/agent0ai/agent-zero) | Custom (see repo) | AI agent framework: plugin system, plugin marketplace (GitHub index repo), self-updater, plugin scanner, agent teams, Telegram integration | EVALUATE -- patterns analyzed, see `docs/ecosystem-comparison.md` |

### Agent Zero Analysis

**Repository**: [agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)

| Metric | Value |
|--------|-------|
| Stars | 16,494 |
| Language | Python |
| License | Custom (NOASSERTION in GitHub API -- check repo directly) |
| Last pushed | 2026-03-29 (actively maintained) |
| Plugin index | [agent0ai/a0-plugins](https://github.com/agent0ai/a0-plugins) (MIT, 43 stars) |
| Website | [agent-zero.ai](https://agent-zero.ai) |

**Patterns adopted into COS**:

| Pattern | Agent Zero Implementation | COS Implementation |
|---------|--------------------------|---------------------|
| Plugin marketplace | GitHub index repo (`a0-plugins`) with YAML manifests, community PRs | `cos` package manager with `cos-index` repo, YAML manifests, quality scoring |
| Plugin/skill creation | `create-plugin` skill generates plugin scaffolding | `skill-creator` skill + `cos init` generates cos-package.yaml scaffolding |
| Plugin security scanning | Built-in plugin scanner checks for malicious patterns | Aguara (189 rules), content-policy hook, secret-detector, Parry (ML-based) |
| Self-update mechanism | Dashboard UI for updating framework | `post-merge` hook + `self-install.sh` for auto-sync |
| Agent teams | Built-in UI for multi-agent collaboration | Claude Code Agent Teams integration with COS quality gates |

**License concern**: Agent Zero uses a custom license (shows as NOASSERTION). Verify compatibility before adopting any code. COS adopts architectural patterns only, not code.

## Agent Platforms / Operating Systems

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Archon OS | [coleam00/Archon](https://github.com/coleam00/Archon) | ACL v1.2 (custom, restrictive) | Knowledge management MCP server, RAG pipeline, project/task management, agent work orders, web crawling | WATCH -- patterns studied, see evaluation below |

### Archon OS Analysis

**Repository**: [coleam00/Archon](https://github.com/coleam00/Archon)

| Metric | Value |
|--------|-------|
| Stars | 13,844 |
| Forks | 2,383 |
| Language | Python (backend), TypeScript (frontend) |
| License | Archon Community License (ACL) v1.2 -- custom, NOT OSI-approved |
| Last pushed | 2026-02-16 (last commit Nov 2025, activity slowing) |
| Release | v0.1.0 (Oct 2025, only release) |
| Open issues | 154 |
| Contributors | 28 |
| Infra requirement | Supabase (PostgreSQL + PGVector), Docker, OpenAI/Gemini/Ollama |

**What Archon is**: A knowledge management and task management "command center" for AI coding assistants. It functions as an MCP server that provides RAG-powered documentation search, project/task hierarchies, and agent work orders to MCP-compatible editors (Claude Code, Cursor, Windsurf). It is NOT an agent OS or orchestrator -- it is a context/knowledge backend that agents connect to.

**Architecture**: True microservices (5 Docker containers):
- archon-server (FastAPI + SocketIO, port 8181) -- core API, web crawling, document processing
- archon-mcp (port 8051) -- MCP HTTP/SSE wrapper exposing RAG and task tools
- archon-agents (PydanticAI, port 8052) -- RAG agent, document agent (optional profile)
- archon-agent-work-orders (port 8053) -- workflow engine with Claude CLI execution, git worktrees (optional profile)
- archon-frontend (React + Vite, port 3737) -- management UI

**Key capabilities**:
1. Smart web crawling with sitemap detection for building knowledge bases
2. PDF/document processing with intelligent chunking
3. Vector search (PGVector) with semantic embeddings and reranking
4. MCP tools for RAG queries, project/task CRUD, document versioning
5. Agent work orders: workflow engine executing Claude Code CLI in isolated git worktrees
6. Real-time WebSocket updates for collaborative use

**Comparison with Cognitive OS**:

| Dimension | Cognitive OS | Archon OS |
|-----------|-------------|-----------|
| **Core philosophy** | Agent governance OS (rules, hooks, quality gates) | Knowledge/context backend for agents |
| **Agent orchestration** | Deep: sub-agent delegation, escalation, retry loops, trust scoring | Minimal: work orders execute Claude CLI sequentially |
| **Quality gates** | 55+ hooks, adversarial review, trust scores, DoD levels | None -- no quality enforcement on agent output |
| **Memory/persistence** | Engram (SQLite, cross-session, structured topic keys) | Supabase PostgreSQL + PGVector (document-oriented) |
| **Knowledge management** | Engram observations + manual docs | Advanced RAG: web crawling, PDF processing, vector search, reranking |
| **MCP integration** | Consumer of MCP tools (engram, context7, etc.) | Provider of MCP tools (RAG, tasks, projects) |
| **Self-improvement** | Auto-skill generation, error learning, consequence system | None -- user-driven only |
| **Security** | 10+ security layers (aguara, parry, semgrep, content policy, etc.) | Minimal (removed Docker socket CVE, basic health checks) |
| **Cost governance** | Budget tracking, model routing, decomposition, rate limiting | None |
| **UI/Dashboard** | Terminal-based (no UI) | Full React UI for knowledge base, projects, tasks |
| **LLM providers** | Multi-provider via LiteLLM (Anthropic, OpenAI, Gemini, local, OpenRouter) | OpenAI, Gemini, Ollama |
| **Infrastructure** | Docker Compose with 10+ optional services | Docker Compose with 5 services + Supabase (external) |
| **License** | Project-specific | ACL v1.2 (custom, restrictive -- no SaaS without permission) |
| **Maturity** | v0.2.1, actively developed, 55+ rules | v0.1.0 beta, last commit Nov 2025, activity declining |

**What Archon has that COS lacks**:
1. **Web crawling for knowledge bases** -- sitemap-aware crawler that builds searchable documentation. COS has no automated web documentation ingestion.
2. **Visual management UI** -- React dashboard for browsing knowledge, managing projects/tasks. COS is terminal-only.
3. **Document processing pipeline** -- PDF/doc chunking with semantic embeddings. COS relies on manual file reading.
4. **MCP server for RAG** -- exposing project knowledge as MCP tools that any editor can consume. COS consumes MCP but does not expose its own knowledge as MCP.

**What COS has that Archon lacks** (substantially):
Agent governance (55+ hooks), quality gates, trust scoring, adversarial review, cost governance, model routing, self-improvement loops, error learning, security scanning (6+ tools), phase-aware behavior, definition of done, acceptance criteria, blast radius estimation, crash recovery, session concurrency, capability levels, and the entire SDD pipeline.

**License concern**: ACL v1.2 is a custom license, NOT OSI-approved. Key restriction: cannot sell Archon as-a-service or offer as hosted service without maintainer permission. Code can be studied and modified but must retain license notice and link back. This means:
- We CANNOT adopt Archon code directly into COS
- We CAN study architectural patterns and reimplement independently
- We CAN use Archon as a complementary service alongside COS

**Recommendation: WATCH -- selective pattern adoption**

Do NOT integrate Archon as a dependency. Reasons:
1. Custom restrictive license (ACL v1.2) blocks code adoption
2. Requires external Supabase dependency (COS aims for self-contained)
3. Development activity appears to be slowing (last commit Nov 2025)
4. Archon and COS solve fundamentally different problems -- Archon is a knowledge backend, COS is an agent governance OS

**Patterns worth studying** (reimplement independently, do not copy code):
1. **Web crawling for knowledge bases**: sitemap detection + intelligent chunking pattern could inspire a COS skill for building local knowledge bases
2. **MCP server for project knowledge**: Exposing COS knowledge (Engram, task state, rules) as MCP tools would make COS accessible from any MCP client
3. **Agent work orders with git worktrees**: pattern of executing Claude CLI in isolated worktrees for parallel work aligns with our session-concurrency model
4. **Document versioning**: Version-controlled documents with real-time updates is a pattern COS could adopt for its plans/specs

**Potential complementary use**: Archon could run alongside COS as a knowledge backend -- COS handles agent governance while Archon provides RAG-powered documentation search via MCP. However, the Supabase dependency and overlapping task management make this integration complex for minimal gain.

## Sandbox/Isolation Infrastructure

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| E2B | [e2b-dev/E2B](https://github.com/e2b-dev/E2B) | Apache-2.0 | Firecracker microVM sandboxes for agent code execution (SDK: Python/TS, MCP server, egress filtering, custom templates, ~150ms boot) | EVALUATE -- see `.cognitive-os/plans/research/e2b-evaluation.md` |
| E2B Infrastructure | [e2b-dev/infra](https://github.com/e2b-dev/infra) | Apache-2.0 | Self-hostable Terraform + Nomad deployment for E2B (GCP/AWS) | EVALUATE -- requires KVM hardware |
| E2B MCP Server | [e2b-dev/mcp-server](https://github.com/e2b-dev/mcp-server) | Apache-2.0 | MCP server with 15 tools for sandbox lifecycle, code execution, file operations | EVALUATE -- lightest integration path |

## AI Code Review Tools

| Source | URL | License | Components | Status |
|--------|-----|---------|------------|--------|
| Gentleman Guardian Angel (GGA) | [GitHub](https://github.com/tomyaparicio/gentleman-guardian-angel) (upstream: 875 stars) | MIT | Provider-agnostic AI pre-commit hook (Claude, Gemini, Codex, Ollama, LM Studio, GitHub Models), smart caching, PR review mode, 397 tests, pure Bash | EVALUATE -- see evaluation below |

### GGA Analysis

**Repository**: Search GitHub for `gentleman-guardian-angel` (upstream org has 875 stars, 110 forks)

| Metric | Value |
|--------|-------|
| Stars | 875 |
| Forks | 110 |
| Language | Shell (pure Bash 5.0+, zero dependencies) |
| License | MIT |
| Version | v2.8.0 |
| Created | 2025-12-12 |
| Last pushed | 2026-03-16 (actively maintained) |
| Primary author | Alan-TheGentleman (70/76 commits) |
| Contributors | 5 |
| Tests | 397 examples (ShellSpec, unit + integration) |
| CI | ShellCheck linting + ShellSpec + Docker integration with Ollama |
| Open issues | 13 (includes Engram integration proposal) |

**What GGA is**: A provider-agnostic AI-powered code review tool that operates as a git pre-commit hook. It sends staged files to an AI provider (Claude, Gemini, Codex, Ollama, LM Studio, GitHub Models) for review against coding standards defined in an `AGENTS.md` file. Pure Bash, zero runtime dependencies.

**Architecture**:
- `bin/gga` -- main CLI (~1000 lines)
- `lib/providers.sh` -- provider abstraction layer (7 providers)
- `lib/cache.sh` -- SHA-256 file caching with config-aware invalidation
- `lib/pr_mode.sh` -- PR review with auto base branch detection
- `.gga` config file per project, `AGENTS.md` for coding rules

**Key capabilities**:
1. Git pre-commit hook integration with safe coexistence (marker-based blocks)
2. 7 AI providers via clean abstraction: Claude CLI, Gemini CLI, Codex CLI, OpenCode, Ollama (local), LM Studio (local), GitHub Models
3. Smart SHA-256 caching: skips unchanged files, invalidates when rules or config change
4. PR review mode: reviews full PR diffs (not just last commit), with diff-only option
5. Commit message validation hook
6. Strict mode: fails CI on ambiguous AI responses
7. Structured response parsing: STATUS: PASSED/FAILED in first 15 lines
8. Configurable file patterns, exclusions, timeout (default 300s)
9. Homebrew installation via brew tap (see repo README for tap command)

**Pending Engram integration (Issues #51/#52)**: Open PRs for bidirectional Engram integration via HTTP API -- consume historical context before reviews, export structured insights after. Includes SQLite + FTS5 persistence layer, privacy-safe secret redaction, 73 new tests. Not yet merged.

**Comparison with Cognitive OS**:

| Dimension | Cognitive OS | GGA |
|-----------|-------------|-----|
| **Core purpose** | Agent governance OS (rules, hooks, quality gates) | Pre-commit AI code review for human developers |
| **Review scope** | Agent output quality, adversarial review, trust scoring | Source file review against AGENTS.md rules |
| **LLM providers** | Multi-provider via LiteLLM proxy | 7 providers via Bash abstraction (no proxy) |
| **Caching** | No file-level review caching | SHA-256 caching with config-aware invalidation |
| **PR review** | sdd-verify (formal spec verification) | PR diff review with base branch auto-detection |
| **Git integration** | PostToolUse/PreToolUse hooks on Claude Code tools | Standard git pre-commit/commit-msg hooks |
| **Rules system** | 55+ rules, RULES-COMPACT.md, contextual loading | Single AGENTS.md file per project |
| **Testing** | pytest (Python libs), ShellSpec (planned) | ShellSpec (397 tests, unit + integration) |
| **Dependencies** | Python 3, Docker (optional), various CLIs | None (pure Bash 5.0+) |
| **Install** | Self-install via symlinks + settings.json | Homebrew or manual script |

**What GGA has that COS lacks**:
1. **File-level caching with invalidation** -- COS hooks re-run on every tool call without caching results
2. **PR review mode** -- COS has no dedicated PR review flow (sdd-verify reviews against specs, not PR diffs)
3. **Provider-agnostic CLI abstraction** -- clean Bash interface for 7 LLM providers without a proxy
4. **Git hook coexistence** -- marker-based blocks for safe insertion into existing pre-commit hooks
5. **ShellSpec test suite** -- 397 tests for Bash code; COS hooks have no test coverage via ShellSpec
6. **Homebrew distribution** -- one-command install via brew tap

**What COS has that GGA lacks** (substantially): Agent orchestration, sub-agent delegation, trust scoring, adversarial review protocol, 55+ quality gates, SDD pipeline, Engram memory, cost governance, model routing, self-improvement loops, error learning, security scanning (6+ tools), phase-aware behavior, definition of done, capability levels, crash recovery, and session concurrency.

**Recommendation: EVALUATE -- selective pattern adoption**

Do NOT integrate GGA as a dependency. Reasons:
1. COS and GGA solve overlapping but distinct problems -- GGA is for human developer commits, COS is for agent governance
2. COS already has comprehensive review via adversarial-review, trust scoring, sdd-verify
3. GGA's single AGENTS.md approach is simpler than COS's multi-rule system

**Patterns worth adopting** (reimplement independently):
1. **ShellSpec testing for hooks** -- GGA's 397-test suite demonstrates ShellSpec can effectively test Bash hooks. COS has 57 hooks with no shell-level test coverage. Adopting ShellSpec for hook testing would significantly improve COS quality.
2. **File-level caching with invalidation** -- SHA-256 hash of file content + config, skip if unchanged. Could reduce COS hook overhead by caching scan results (semgrep, aguara, content-policy).
3. **PR review mode** -- base branch auto-detection + diff-only review. Could become a COS skill for team PR workflows.
4. **Structured AI response parsing** -- STATUS: PASSED/FAILED pattern ensures deterministic parsing of LLM output. COS Trust Reports could adopt a similar parseable format.
5. **Git hook coexistence pattern** -- marker-based blocks for safe insertion into existing hooks, with migration from legacy formats.

**Potential complementary use**: GGA could run alongside COS as a pre-commit gate for human developer commits, while COS governs agent-generated code. The planned Engram integration in GGA would enable shared memory between the two systems.

**Note on fork**: The URL provided (`tomyaparicio/gentleman-guardian-angel`) is a dead fork with 0 stars and no activity beyond the initial fork on 2026-02-19. The upstream organization repo (875 stars, active development) is the canonical repository.

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
