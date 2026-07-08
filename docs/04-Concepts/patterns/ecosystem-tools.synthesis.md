---
type: concept-synthesis
source: docs/04-Concepts/patterns/ecosystem-tools.md
provenance: "Document all external tools integrated into Cognitive OS — configuration, installation, and which hooks use them — so hooks degrade gracefully when a tool is absent."
---

## What it is

Reference catalog of every external tool wired into COS via hooks/skills/MCP, each following the graceful-degradation pattern: if the tool binary is missing, the hook silently exits 0 without blocking.

## Key mechanics

**Adopted/integrated tools** (purpose | hook or skill | install | required?):
- `ccusage` (ADOPT) — reads `~/.claude/projects/*/*.jsonl` for real token/cost analytics; `npx ccusage@latest`; optional; `lib/record_completion.py` reads same JSONL natively for `input_tokens`/`output_tokens`/`cache_*_tokens`.
- `agnix` — lints SKILL.md/rules/agent configs; `hooks/agnix-lint.sh` (PostToolUse Edit\|Write); reconstruction/stabilization = warn, production/maintenance = block (exit 2); findings → `.cognitive-os/metrics/agnix-findings.jsonl`.
- `Pyrefly` (TRIAL) — Python type checker; `scripts/cos-pyrefly-pilot`; advisory only unless `COS_PYREFLY_ENFORCE=1`; first run (2026-05-15, v1.0.0) found 268 non-import errors, too large for blocking yet.
- `semgrep` — SAST; `hooks/semgrep-scan.sh` (PostToolUse Agent); OFF by default, `SEMGREP_ENABLED=true`.
- `parry-guard` — prompt injection scanner; `hooks/parry-scan.sh` (PreToolUse Agent); optional.
- `recall` — conversation transcript search; `skills/recall-search/SKILL.md`; optional.
- `aguara` — 189-rule deterministic security scanner, 14 threat categories; `hooks/aguara-scan.sh` (PreToolUse Agent); registered in paranoid profile; CRITICAL findings block (exit 2), rest advisory; MCP server `mcp-aguara` provides 5 tools.
- `garak` (ADOPT) — "Nmap for LLMs," 179 probes; `skills/vulnerability-scan/SKILL.md`; Apache-2.0.
- `mcp-scan` — scans `.claude/settings*.json` MCP configs for tool poisoning/injection; `hooks/mcp-scan.sh` (SessionStart); always advisory, never blocks.
- `promptfoo` — LLM red-team testing; `skills/red-team/SKILL.md`.
- `hcom` — cross-terminal session communication.
- `claude-hud` (ADOPT) — persistent statusline (context %, tools, subagents, todos, cost, model, branch); native `statusLine` API; context bar correlates with `rules/context-management.md` 50/70/85% thresholds.

**EVALUATE-status tools** (not adopted, patterns only): LlamaFirewall/Meta (multi-layer AI security), AgentGateway/Linux Foundation (MCP/A2A proxy w/ RBAC), OneCLI (credential vault, Phase 2 identity-stack target per `rules/agent-identity.md`), Archon (workflow DAG engine — extract conditional/loop/output-piping patterns into `lib/task_dag.py`, clean-room only), OpenSwarm (deliverable specialist swarm, monitor/harvest only), Agno Suite (production agent platform, bounded adapter lab), EvoSkill (skill-evolution loop, extract stage contract/evidence schema only), Langflow (visual workflow builder, extract patterns only).

**WATCH-status**: Agentic Radar (workflow topology analysis), skill-scanner/Cisco (overlaps Aguara's 189 rules), tero/mantis (garagon HTTP testing/security — `packages/tero-testing/`, `packages/mantis-security/`).

**ASSESS/HOLD**: OpenSage (self-programming ADK, 86 stars, ASSESS/trial-patterns, gotchas: unreleased, broad Docker/Neo4j/LiteLLM surface), TaskingAI (AI-native BaaS, 5377 stars but HOLD — stale upstream since 2024-12, red CI).

**Graceful degradation pattern**: `if ! command -v tool-name &>/dev/null; then exit 0; fi` — ensures COS works without any external tools, CI never breaks on missing optionals.

**Adding a new tool** (6 steps): hook in `hooks/` with degradation pattern → config in `.{tool}.toml`/`cognitive-os.yaml` → integration test in `tests/integration/test_ecosystem_tools.py` → unit test → document here → update RULES-COMPACT.md if it adds an always-active rule.

## Relations & where used

`packages/aguara-security/rules/aguara-integration.md`, `rules/context-management.md`, `packages/ecosystem-tools/rules/{hcom,repomix}-integration.md`. Portable-primitive radar entries (VERSA/dotAIslash, Agent Skills ecosystem, Zed ACP, OpenCode permissions/plugins, Open Agent Passport) tracked as ADR-258/ADR-256 spec references, not runtime deps.

## Status / caveats

Tier-1, scope both. Installation-status check command lists 12 tools to probe: `ccusage agnix semgrep parry-guard aguara mcp-aguara mcp-scan garak promptfoo recall hcom tero mantis`.
