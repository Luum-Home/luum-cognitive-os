# Cognitive OS Security Assessment Plan

## Objective

Assess how protected, safe, and reliable Cognitive OS is when used by coding
agents, using both defender and malicious-operator perspectives.

The first executable primitive for this plan is `/security-red-team`, implemented
by `scripts/security-red-team` and documented in
`docs/09-Quality/security/security-red-team.md`. It produces the local deterministic
inventory/threat/probe/score/backlog report that seeds the deeper phases below.

## Phase 1 — Local attack-surface inventory

Inventory all agentic primitives and runtime tools:

- hooks in `hooks/` and shared libraries in `hooks/_lib/`;
- rules in `rules/`;
- skills in `skills/` and `.codex/skills/`;
- scripts in `scripts/`;
- manifests in `manifests/`;
- metrics/audit appenders in `.cognitive-os/metrics/`;
- provider dispatch code in `lib/`;
- bootstrap/startup paths, dotenv loaders, and env flags.

Deliverable: `docs/09-Quality/security/cognitive-os-attack-surface-inventory.md`.

## Phase 2 — Red-team scenarios

Attack classes to test:

1. Secret exfiltration through stdout/stderr, audit files, metrics, prompts,
   provider request bodies, shell history, subprocess env, and generated docs.
2. Prompt/rule injection against rules, skills, hook outputs, and generated
   session context.
3. Tool allowlist bypasses, path traversal, symlink traversal, command injection,
   shell eval, and unsafe glob expansion.
4. Hook suppression abuse via env flags, safe mode flags, and test skip flags.
5. Provider routing abuse: forced fallback, cost exhaustion, provider spoofing,
   fake metric rows, and model-output trust confusion.
6. Persistence abuse: Engram/session summaries/metrics poisoning and replay.
7. Supply-chain risk: plugin/skill install paths, GitHub tools, package managers,
   shell downloads, and binary execution.
8. Workspace integrity: unreviewed manifest changes, generated config drift,
   direct-main bypasses, destructive git flags, and concurrent writes.
9. Observability integrity: audit truncation, JSONL corruption, redaction gaps,
   and log tampering.
10. Denial of service: huge outputs, recursive hooks, runaway agents, expensive
    provider loops, and container/service startup storms.

Deliverable: `docs/09-Quality/security/cognitive-os-red-team-scenarios.md` plus pytest
fixtures where scenarios are automatable.

## Phase 3 — Control mapping

Map every risk to existing controls:

- blocked path rules;
- hook security profiles;
- runtime env flag manifest;
- credential-safe script manifest;
- safe-jsonl and metrics contracts;
- startup circuit breakers;
- LLM dispatch kill switches;
- test opt-in flags;
- direct-main/destructive-git/concurrent-write bypasses.

Deliverable: `docs/09-Quality/security/cognitive-os-control-matrix.md`.

## Phase 4 — Automated adversarial test suite

Create a security test lane that runs without real secrets:

```bash
python3 -m pytest tests/security/ -q
```

Initial test families:

- fake `.env` leakage probes;
- symlink/path traversal probes;
- manifest integrity tamper probes;
- hook-disable flag inventory/contract probes;
- metrics redaction and JSONL integrity probes;
- provider dispatch spoofing probes;
- skill/rule prompt-injection fixture probes.

## Phase 5 — Internet and ecosystem research

Research current best practices and known failure modes across at least these
source types:

- official docs for Claude Code hooks/skills/MCP and OpenAI/Codex tool use;
- OWASP LLM Top 10 and agent security guidance;
- GitHub repos for OpenClaw, OpenCode, aider, Roo/Cline, Continue, Goose,
  SWE-agent, LangGraph/LangChain agent runtimes, AutoGen, CrewAI, Semantic
  Kernel, Qwen-Agent, Kimi/Moonshot, DeepSeek, MiniMax, and sandbox projects;
- security writeups on prompt injection, tool-use injection, secret leakage,
  MCP risks, package-manager supply chain, and AI coding-agent sandbox escapes;
- posts/issues discussing `.env` leakage, shell tools, and agentic IDE hardening.

Deliverable: `docs/09-Quality/security/cognitive-os-agent-security-research-2026-05.md`
with citations and an actionable backlog.

## Phase 6 — Reliability and trust scoring

Define a security confidence score per primitive:

- isolation strength;
- secret handling;
- auditability;
- tamper resistance;
- least privilege;
- test coverage;
- failure-mode clarity;
- operator ergonomics.

Deliverable: `manifests/security-control-ledger.yaml` and a generated report.
