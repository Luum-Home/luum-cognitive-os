<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Ecosystem Tools — External Tool Integrations

## Purpose

Documents all external tools integrated into Cognitive OS, their configuration, installation, and which hooks use them. All ecosystem tools follow the graceful degradation pattern: if a tool is not installed, the corresponding hook silently exits without blocking.

## Integrated Tools

### ccusage — Claude Code Token & Cost Analytics (ADOPT)

| Property | Value |
|----------|-------|
| Purpose | Reads real token usage from `~/.claude/projects/*/\*.jsonl` and reports daily/monthly/session/5h-block costs with structured JSON output |
| Install | `npx ccusage@latest` (zero install) or `npm install -g ccusage` |
| Required | No (optional, but recommended for accurate cost visibility) |
| Output | Tables, JSON (`--json`), grouped by session/day/month/project |
| License | MIT |
| GitHub | [ryoppippi/ccusage](https://github.com/ryoppippi/ccusage) |
| Version | v18+ (actively maintained, 100+ releases) |
| Scope | `~/.claude/projects/` — same JSONL files Cognitive OS reads natively |

**Usage examples**:
```bash
npx ccusage@latest            # current month summary
npx ccusage@latest session    # per-session breakdown
npx ccusage@latest blocks     # 5-hour billing window view
npx ccusage@latest --json     # structured JSON for scripting
npx ccusage@latest daily --since 2026-04-01
```

**Integration with Cognitive OS**: `lib/record_completion.py` reads the same JSONL files natively to extract real `input_tokens`, `output_tokens`, and `cache_*_tokens` per completion, replacing the previous `len(output)//4` estimate. `ccusage` provides session-level and monthly roll-ups that the COS cost dashboard (`lib/cost_dashboard.py`) can optionally delegate to.

**Why chosen over alternatives**:
- `ccost` (Rust): good but requires cargo install, smaller community
- `claude-usage` (Python): dashboard-only, no JSON output for scripting
- `Claude-Code-Usage-Monitor` (Python): real-time UI only, no JSON output, no CLI integration

### agnix — Agent Configuration Linter

| Property | Value |
|----------|-------|
| Purpose | Lints agent configuration files (SKILL.md, rules, agent definitions) for best practices |
| Config | `.agnix.toml` at project root |
| Hook | `hooks/agnix-lint.sh` (PostToolUse on Edit\|Write) |
| Install | `npm install -g @agent-sh/agnix` or `brew install agent-sh/tap/agnix` |
| Required | No (optional dependency, graceful skip if missing) |
| Scope | `.claude/`, `rules/`, `skills/`, `agents/` files only |

**Phase behavior**:
- reconstruction/stabilization: warnings only (exit 0)
- production/maintenance: errors block writes (exit 2)

**Metrics**: Findings logged to `.cognitive-os/metrics/agnix-findings.jsonl`

### semgrep — Static Application Security Testing

| Property | Value |
|----------|-------|
| Purpose | Scans code changes for security vulnerabilities and anti-patterns |
| Config | `.semgrep/` directory for custom rules (optional) |
| Hook | `hooks/semgrep-scan.sh` (PostToolUse on Agent) |
| Install | `pip install semgrep` or `brew install semgrep` |
| Required | No (OFF by default, enable with `SEMGREP_ENABLED=true`) |
| Scope | Source code files (.go, .ts, .py, .java, etc.) after sdd-apply |

**Metrics**: Findings logged to `.cognitive-os/metrics/semgrep-findings.jsonl`

### parry-guard — Prompt Injection Scanner

| Property | Value |
|----------|-------|
| Purpose | Scans agent prompts for prompt injection attempts |
| Config | `cognitive-os.yaml` under `security.parry` |
| Hook | `hooks/parry-scan.sh` (PreToolUse on Agent) |
| Install | `npm install -g parry-guard` |
| Required | No (optional dependency) |
| Scope | Agent prompts before execution |

### recall — Conversation Search

| Property | Value |
|----------|-------|
| Purpose | Searches past conversation transcripts for context |
| Config | None (reads from Claude conversation history) |
| Skill | `skills/recall-search/SKILL.md` |
| Install | `npm install -g @anthropic/recall` |
| Required | No (optional dependency) |
| Scope | Conversation history search |

### aguara — AI Agent Security Scanner

| Property | Value |
|----------|-------|
| Purpose | Deterministic security scanner for AI agent skills and MCP servers. 189 rules across 14 threat categories (prompt injection, data exfiltration, supply chain attacks). No LLM required. |
| Config | `cognitive-os.yaml` under `security.aguara` |
| Hook | `hooks/aguara-scan.sh` (PreToolUse on Agent) |
| Install | `go install github.com/garagon/aguara@latest` or `bash scripts/install-aguara.sh` |
| Required | No (optional dependency, graceful skip if missing) |
| Registered | Yes — registered in paranoid security profile (PreToolUse on Agent) |
| Scope | Agent prompts before execution |

**Phase behavior**:
- All phases: CRITICAL findings block agent launch (exit 2), all others advisory (exit 0)

**Metrics**: Findings logged to `.cognitive-os/metrics/aguara-findings.jsonl`

**MCP Server**: `mcp-aguara` available as optional MCP server (`go install github.com/garagon/mcp-aguara@latest`). Provides 5 tools: `scan_content`, `check_mcp_config`, `list_rules`, `explain_rule`, `discover_mcp`. See `packages/aguara-security/rules/aguara-integration.md` for registration instructions.

### garak — LLM Vulnerability Scanner (ADOPT)

| Property | Value |
|----------|-------|
| Purpose | "Nmap for LLMs" -- 179 probes for hallucination, data leakage, prompt injection, toxicity, and encoding attacks against LLM endpoints |
| Config | N/A (CLI tool, arguments passed per invocation) |
| Skill | `skills/vulnerability-scan/SKILL.md` |
| Install | `pip install garak` or `bash scripts/install-garak.sh` |
| Required | No (optional dependency) |
| Scope | LLM endpoint vulnerability scanning |
| GitHub | [NVIDIA/garak](https://github.com/NVIDIA/garak) |
| License | Apache-2.0 |
| Status | **ADOPT** -- Skill implemented, install script available |

**Metrics**: Findings logged to `.cognitive-os/metrics/garak-findings.jsonl`

**Package**: `packages/tero-testing/` and `packages/mantis-security/` are companion garagon tools.

### LlamaFirewall (Meta) — AI Security Framework (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Multi-layer AI security framework for detecting risks in chat and agentic operations. Combines prompt injection detection, content safety, and agent behavior monitoring. |
| Config | N/A (evaluation phase) |
| Hook | N/A (not yet implemented) |
| Install | See [meta-llama/PurpleLlama](https://github.com/meta-llama/PurpleLlama) |
| Required | No |
| Scope | Input/output guardrails for LLM operations |
| GitHub | [meta-llama/PurpleLlama](https://github.com/meta-llama/PurpleLlama) |
| License | MIT |
| Status | **EVALUATE** -- Under evaluation, may complement NeMo Guardrails |

**Evaluation Notes**: LlamaFirewall provides multi-layer defense (PromptGuard, CodeShield, Llama Guard) that could complement our NeMo Guardrails for agent-specific scenarios. Key differentiator: agentic operation support with tool call monitoring. Evaluate whether it covers gaps NeMo does not, particularly for agentic tool-use patterns.

### AgentGateway (Linux Foundation) — AI-Native Proxy (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | AI-native proxy for MCP/A2A protocols with RBAC, observability, and policy enforcement |
| Config | N/A (evaluation phase) |
| Hook | N/A (not yet implemented) |
| Install | See [agentgateway/agentgateway](https://github.com/agentgateway/agentgateway) |
| Required | No |
| Scope | Central policy enforcement point for agent protocols |
| GitHub | [agentgateway/agentgateway](https://github.com/agentgateway/agentgateway) |
| License | Apache-2.0 |
| Status | **EVALUATE** -- Compare with existing Bifrost + LiteLLM gateway setup |

**Evaluation Notes**: AgentGateway provides native MCP/A2A protocol support with RBAC, which our current gateway stack (Bifrost + LiteLLM) does not. Key question: does AgentGateway replace or complement our existing gateways? The RBAC layer could unify our `lib/agent_permissions.py` enforcement at the network level. Evaluate after MCP security tooling (MCP-Scan, mcp-context-protector) is in place.

### OneCLI — Agent Credential Vault (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Rust HTTP gateway that injects credentials transparently so agents never hold raw keys. AES-256-GCM encryption, per-agent scoping. |
| Config | N/A (evaluation phase) |
| Hook | N/A (not yet implemented) |
| Install | See [onecli/onecli](https://github.com/onecli/onecli) |
| Required | No |
| Scope | Credential injection for agent operations |
| GitHub | [onecli/onecli](https://github.com/onecli/onecli) |
| License | OSS (Rust) |
| Status | **EVALUATE** -- Phase 2 integration per identity stack roadmap |

**Evaluation Notes**: Already referenced in `rules/agent-identity.md` as a Phase 2 integration target. OneCLI would replace our current `lib/secret_ref.py` with a dedicated credential vault that prevents agents from ever seeing raw keys. Current SecretRef reads from env vars; OneCLI provides proper cryptographic key management with per-agent scoping.

### Archon — AI Agent Workflow Engine (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | YAML-defined DAG workflow engine for AI coding agents with worktree isolation, conditional branching, loop nodes, and multi-platform adapters |
| Config | N/A (evaluation phase — pattern adoption only) |
| Hook | N/A (not yet implemented) |
| Install | See [coleam00/Archon](https://github.com/coleam00/Archon) |
| Required | No |
| Scope | Workflow execution patterns for TaskDAG enhancement |
| GitHub | [coleam00/Archon](https://github.com/coleam00/Archon) |
| License | MIT |
| Status | **EVALUATE** — Adopt patterns (conditional DAG, loops, output piping) via clean-room, not the runtime |

**Evaluation Notes**: Archon excels at workflow execution mechanics (14/27 features) while COS excels at governance (11/27). Language barrier (TypeScript/Bun vs Python) and architectural mismatch (standalone server vs CLI overlay) make direct adoption impractical. Clean-room implementation of conditional execution, loop primitives, and output piping into our `lib/task_dag.py` is the recommended path. Full evaluation at `docs/research/archon-evaluation.md`. Re-evaluate if Archon adds governance features.


### OpenSwarm — Deliverable Specialist Swarm (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Local terminal multi-agent system for non-coding deliverables: research reports, data analysis, slide decks, documents, images, videos, and external-service tasks |
| Config | N/A (evaluation phase — pattern-only reference) |
| Hook | N/A (not implemented) |
| Install | See [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm); do not add to default COS bootstrap |
| Required | No |
| Scope | Specialist-agent roster, artifact delivery UX, and routing-policy reference |
| GitHub | [VRSEN/OpenSwarm](https://github.com/VRSEN/OpenSwarm) |
| License | MIT |
| Status | **EVALUATE** — Monitor and harvest patterns; do not adopt the runtime |

**Evaluation Notes**: OpenSwarm is valuable as a productized example of an orchestrator plus deliverable specialists with explicit `SendMessage` vs `Handoff` routing and concrete output-path discipline. Direct runtime adoption is not recommended: it is a young, broad Agency Swarm application with heavy Python/Node/media dependencies, bootstrap side effects, all-to-all handoffs, and external-action tools that would need COS credential, permission, audit, and rollback wrappers. Deep evaluation: `docs/research/repo-scout/deep/VRSEN__OpenSwarm-2026-05-09.md`; addendum: `docs/reports/external-tools-radar-openswarm-addendum-2026-05-09.md`.

### Agno Suite — Production Agent Platform and Company-Brain Templates (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Agent platform and first-party app templates for production agent services, self-learning data agents, and company-brain context providers |
| Config | N/A (evaluation phase — pattern-only plus possible future adapter lab) |
| Hook | N/A (not implemented) |
| Install | See [agno-agi/agno](https://github.com/agno-agi/agno); do not add to default COS bootstrap |
| Required | No |
| Scope | Runtime packaging, human approval UX, tracing/session concepts, data-agent learning loop, context-provider registry |
| GitHub | [agno-agi/agno](https://github.com/agno-agi/agno), [agno-agi/dash](https://github.com/agno-agi/dash), [agno-agi/scout](https://github.com/agno-agi/scout) |
| License | Apache-2.0 |
| Status | **EVALUATE** — Assess patterns and a bounded adapter lab; do not adopt the runtime by default |

**Evaluation Notes**: Agno is different from the Claw naming cluster: it is a production-agent platform with SDK/runtime/control-plane concepts, while Dash and Scout are first-party templates for self-learning data agents and company-brain context providers. Useful extraction targets are runtime packaging vocabulary, human approval UX, Dash's durable SQL/data learnings, and Scout's provider registry. Direct adoption is not recommended until telemetry, hosted-control-plane, credential, rollback, and ADR-049/ADR-064 governance boundaries are proven. Deep evaluation: `docs/research/repo-scout/deep/agno-agi__agno-suite-2026-05-09.md`; addendum: `docs/reports/external-tools-radar-agno-addendum-2026-05-09.md`.

### EvoSkill — Automated Skill Discovery for Coding Agents (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Benchmark-driven self-improvement loop that analyzes failed agent trajectories, proposes reusable skills or prompt changes, generates skill folders, evaluates on held-out data, and keeps frontier-improving agent programs |
| Config | N/A (evaluation phase — pattern-only plus possible future adapter lab) |
| Hook | N/A (not implemented) |
| Install | See [sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill); do not add to default COS bootstrap |
| Required | No |
| Scope | Skill-evolution loop, generated-skill evidence schema, held-out validation, frontier selection, cross-harness skill projection fixtures |
| GitHub | [sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill) |
| License | Apache-2.0 |
| Status | **EVALUATE** — Trial patterns and a disposable adapter lab; do not adopt the runtime by default |

**Evaluation Notes**: EvoSkill is the strongest current external reference for COS's skill-optimization direction: it turns failed trajectories into reusable skill folders, validates against held-out data, and tracks frontier-improving agent programs. Direct runtime adoption is gated because it mutates git branches/tags, writes `.claude/skills`, can forward provider credentials into Docker or remote runs, and depends on project-owned benchmark quality. Extract the stage contract, evidence schema, projection fixture, and validation discipline first. Deep evaluation: `docs/research/repo-scout/deep/sentient-agi__EvoSkill-2026-05-09.md`; addendum: `docs/reports/external-tools-radar-evoskill-addendum-2026-05-09.md`.

### Langflow — Visual AI Workflow Builder and MCP-Facing Runtime (EVALUATE)

| Property | Value |
|----------|-------|
| Purpose | Visual builder and service runtime for AI-powered workflows, agents, APIs, and MCP-facing tool deployments |
| Config | N/A (evaluation phase — pattern-only plus possible future adapter lab) |
| Hook | N/A (not implemented) |
| Install | See [langflow-ai/langflow](https://github.com/langflow-ai/langflow); do not add to default COS bootstrap |
| Required | No |
| Scope | Visual workflow UX, flow-to-API/MCP packaging, bundle/extension registry, settings taxonomy, security regression fixtures |
| GitHub | [langflow-ai/langflow](https://github.com/langflow-ai/langflow) |
| License | MIT |
| Status | **EVALUATE** — Extract patterns and optionally run a local-only adapter lab; do not adopt the runtime by default |

**Evaluation Notes**: Langflow is a mature Python/TypeScript visual workflow app with FastAPI backend, React flow editor, `lfx` executor, Python SDK, and MCP-facing workflow/tool surfaces. It is valuable for visual graph UX, flow-to-MCP packaging, bundle registries, and security fixtures, but direct runtime adoption would import a large app surface with dynamic code execution, broad credential/env configuration, storage, telemetry, and hosted-control-plane concerns. Keep COS hooks/rules/skills/Engram/SDD/provider routing authoritative. Deep evaluation: `docs/research/repo-scout/deep/langflow-ai__langflow-2026-05-09.md`; addendum: `docs/reports/external-tools-radar-langflow-addendum-2026-05-09.md`.

### Agentic Radar (SPLX AI) — Agent Workflow Analyzer (WATCH)

| Property | Value |
|----------|-------|
| Purpose | Visualizes agent workflows, detects risky tool usage and permission loops via static analysis |
| Config | N/A (watch phase) |
| Hook | N/A |
| Install | See SPLX AI documentation |
| Required | No |
| Scope | Agent workflow topology analysis |
| Status | **WATCH** -- Monitoring for maturity |

**Evaluation Notes**: Agentic Radar provides static analysis of agent workflow graphs that our current tooling does not cover. Could detect circular permission delegation and risky tool usage patterns. Watch for production readiness and evaluate when our agent orchestration becomes more complex.

### skill-scanner (Cisco AI Defense) — Skill Security Scanner (WATCH)

| Property | Value |
|----------|-------|
| Purpose | Scanner for AI agent skills that detects prompt injection, data exfiltration, and malicious code patterns |
| Config | N/A (watch phase) |
| Hook | N/A |
| Install | See Cisco AI Defense documentation |
| Required | No |
| Scope | Skill definition security scanning |
| Status | **WATCH** -- Aguara covers similar space with 189 rules |

**Evaluation Notes**: Significant overlap with Aguara, which already provides 189 deterministic rules for skill scanning. skill-scanner uses ML-based detection which could catch patterns Aguara's deterministic rules miss, but adds complexity. Revisit if Aguara proves insufficient for skill security coverage.

### TaskingAI — AI-native app BaaS with provider routing, RAG, tools, UI (HOLD)

---
repo: TaskingAI/TaskingAI
classification: HOLD
stars: 5377
license: Apache-2.0
ci_health: red
score: 60
one_liner: "AI-native app BaaS with provider routing, RAG, tools, UI; pattern-only while upstream is stale."
last_evaluated: 2026-05-09
last_commit: 2024-12-02
last_release: 2024-06-03
---

| Property | Value |
|----------|-------|
| GitHub | [TaskingAI/TaskingAI](https://github.com/TaskingAI/TaskingAI) |
| Purpose | AI-native application BaaS with provider routing, RAG/data flows, tools/plugins, REST API, Python SDK, and React console |
| Radar posture | **HOLD / pattern-only** |
| Runtime adoption | No default dependency; do not integrate until upstream activity and CI recover |
| Deep dive | `docs/reports/external-tools-radar-taskingai-addendum-2026-05-09.md` |

**Adoption notes**: Study provider YAML catalogs, tool bundle metadata/execution boundaries, and multi-service deployment topology as design references only. Keep COS provider routing and tool governance first-party behind existing adapter boundaries.

**Gotchas**: Upstream is stale by the 12-month repo-scout gate, recent concluded CI runs are red, and workflow files contain hardcoded crypto-like environment values that must not be copied into COS.


### tero (garagon) — HTTP Testing with Chaos (WATCH)

| Property | Value |
|----------|-------|
| Purpose | Deterministic HTTP testing with fault injection, latency simulation, connection drops, and chaos engineering patterns |
| Config | N/A (CLI tool) |
| Hook | N/A |
| Install | `go install github.com/garagon/tero@latest` |
| Required | No |
| Scope | HTTP resilience testing |
| GitHub | [garagon/tero](https://github.com/garagon/tero) |
| License | Apache-2.0 |
| Status | **WATCH** -- COS package at `packages/tero-testing/` |

### mantis (garagon) — HTTP Security Toolkit (WATCH)

| Property | Value |
|----------|-------|
| Purpose | Automated HTTP security scanning with OWASP coverage, header analysis, TLS verification |
| Config | N/A (CLI tool) |
| Hook | N/A |
| Install | `go install github.com/garagon/mantis@latest` |
| Required | No |
| Scope | HTTP endpoint security scanning (DAST) |
| GitHub | [garagon/mantis](https://github.com/garagon/mantis) |
| License | Apache-2.0 |
| Status | **WATCH** -- COS package at `packages/mantis-security/` |

### mcp-scan — MCP Server Configuration Scanner

| Property | Value |
|----------|-------|
| Purpose | Scans MCP server configurations for tool poisoning, injection vulnerabilities, and cross-origin violations |
| Config | `cognitive-os.yaml` under `security.mcp_scan` |
| Hook | `hooks/mcp-scan.sh` (SessionStart) |
| Install | `pip install mcp-scan` or `npx @invariantlabs/mcp-scan` or `bash scripts/install-mcp-scan.sh` |
| Required | No (optional dependency, graceful skip if missing) |
| Scope | `.claude/settings.json` and `.claude/settings.local.json` MCP server definitions |

**Phase behavior**:
- All phases: advisory only (exit 0) -- never blocks session start

**Metrics**: Findings logged to `.cognitive-os/metrics/mcp-scan-findings.jsonl`

### promptfoo — LLM Red Team Testing

| Property | Value |
|----------|-------|
| Purpose | Red team testing for agent prompts -- detects injection, jailbreak, and manipulation vulnerabilities |
| Config | `.promptfoo/config.yaml` at project root |
| Skill | `skills/red-team/SKILL.md` |
| Install | `npm install -g promptfoo` or `npx promptfoo@latest` or `bash scripts/install-promptfoo.sh` |
| Required | No (optional dependency) |
| Scope | Agent preamble and prompt templates |

**Metrics**: Results logged to `.cognitive-os/metrics/red-team-results.jsonl`

### hcom — Cross-Terminal Communication

| Property | Value |
|----------|-------|
| Purpose | Enables communication between concurrent Claude Code sessions |
| Config | `cognitive-os.yaml` under `sessions.hcom` |
| Hook | N/A (used by session management) |
| Install | `npm install -g hcom` |
| Required | No (optional dependency) |
| Scope | Multi-session coordination |

### claude-hud — Real-Time Session HUD

| Property | Value |
|----------|-------|
| Purpose | Displays a persistent statusline below the Claude Code input showing context usage %, active tools, running subagents, todo progress, session cost, model name, and git branch |
| Config | `~/.claude/plugins/claude-hud/config.json` — optional overrides for layout, display toggles, colors |
| Hook | N/A — runs via Claude Code's native `statusLine` API (configured in `~/.claude/settings.json`) |
| Install | Via Claude Code plugin system: `/plugin marketplace add jarrodwatts/claude-hud` then `/plugin install claude-hud` then `/claude-hud:setup` |
| Required | No (optional enhancement, graceful skip if not installed) |
| Scope | All Claude Code sessions globally (user-scoped plugin) |
| GitHub | [jarrodwatts/claude-hud](https://github.com/jarrodwatts/claude-hud) |
| License | MIT |
| Status | **ADOPT** — installed and configured |

**What it shows** (default Essential preset, customizable via `/claude-hud:configure`):

```
[claude-opus-4-6] │ luum-agent-os git:(main*)
Context ████░░░░░░ 38% │ Usage ██░░░░░░░░ 22% (1h 20m / 5h)
◐ Edit: ecosystem-tools.md | ✓ Read ×3 | ✓ Grep ×2
◐ explore [sonnet]: Finding auth code (2m 15s)
```

**Configuration** (active config at `~/.claude/plugins/claude-hud/config.json`):
- `lineLayout: expanded` — multi-line display
- `display.showTools: true` — tool activity line
- `display.showAgents: true` — subagent status line
- `display.showCost: true` — session cost
- `display.showDuration: true` — session duration

**Integration with Cognitive OS**: The context bar directly correlates with `rules/context-management.md` thresholds (50%/70%/85%). Seeing the bar approach yellow/red is an early warning to save state to Engram.

**Manual install path** (if plugin system is unavailable): Clone `https://github.com/jarrodwatts/claude-hud` to `~/.claude/plugins/cache/claude-hud/claude-hud/{version}/`, add `statusLine` config to `~/.claude/settings.json`, then restart Claude Code.

**Metrics**: No separate metrics file — statusline renders natively in the terminal UI.

## Graceful Degradation Pattern

All ecosystem tool hooks follow this pattern:

```bash
# Check if tool is installed — skip silently if not
if ! command -v tool-name &>/dev/null; then
  exit 0
fi
```

This ensures:
1. The Cognitive OS works without any external tools installed
2. Tools are additive enhancements, not requirements
3. CI/CD pipelines do not break due to missing optional tools
4. New team members can onboard without installing every tool upfront

## Adding New Ecosystem Tools

When integrating a new external tool:

1. Create a hook in `hooks/` following the graceful degradation pattern
2. Add configuration (if needed) to `.{tool}.toml` or `cognitive-os.yaml`
3. Add integration tests to `tests/integration/test_ecosystem_tools.py`
4. Add unit tests for hook logic to `tests/unit/test_{tool}_integration.py`
5. Document the tool in this file
6. Update `RULES-COMPACT.md` if the tool adds a new always-active rule

## Installation Status Check

Run the following to check which ecosystem tools are available:

```bash
for tool in ccusage agnix semgrep parry-guard aguara mcp-aguara mcp-scan garak promptfoo recall hcom tero mantis; do
  if command -v "$tool" &>/dev/null; then
    echo "[installed] $tool: $($tool --version 2>/dev/null | head -1)"
  else
    echo "[missing]   $tool"
  fi
done
```

## Contextual Trigger

This rule is loaded when: ecosystem tools, external tools, ccusage, token usage, cost tracking, claude usage, agnix, semgrep, parry, aguara, mcp-scan, promptfoo, garak, recall, hcom, tero, mantis, tool integration.
