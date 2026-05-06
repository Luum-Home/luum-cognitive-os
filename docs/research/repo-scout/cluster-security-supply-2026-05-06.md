---
cluster: security-supply
date: 2026-05-06
phase: shallow
total_repos: 10
pass_to_deep: 4
reject: 4
patterns_only: 1
already_integrated: 1
budget_used: ~12/45
---

# Cluster Scout — security-supply (shallow)

Theme: security scanning, sandboxed execution, supply-chain defense for LLM/agent systems. Aguara already integrated (ADR-013, 8-layer security) — new scanners must show concrete delta.

## Per-Repo Findings

### 1. NVIDIA-NeMo/Guardrails
- **URL**: https://github.com/NVIDIA-NeMo/Guardrails
- **License**: Apache-2.0 (resolved via LICENSE.md SPDX header; gh reports NOASSERTION)
- **Stars**: 6,082
- **Last commit**: 2026-05-05
- **Primary language**: Python
- **Purpose**: Programmable guardrails (Colang DSL) for LLM conversational systems — input/output/topic/jailbreak rails.
- **Verdict**: SKIP — already integrated as a SO skill (`nemo-guardrails` listed in active skills). No new scout work needed; track upstream for new rail types.
- **Rationale**: Existing integration. Phase 2 only if a specific new rail (e.g., new jailbreak pattern) is requested.

### 2. e2b-dev/E2B
- **URL**: https://github.com/e2b-dev/E2B
- **License**: Apache-2.0
- **Stars**: 12,071
- **Last commit**: 2026-05-06
- **Primary language**: Python (SDK; Firecracker microVMs server-side)
- **Purpose**: Open-source secure sandbox runtime for AI-generated code execution (microVM isolation, real-world tools).
- **Verdict**: SKIP — already integrated (ADR `e2b-integration`, [`e2b-integration`] in RULES-COMPACT).
- **Rationale**: Existing integration.

### 3. e2b-dev/infra
- **URL**: https://github.com/e2b-dev/infra
- **License**: Apache-2.0
- **Stars**: 1,081
- **Last commit**: 2026-05-06
- **Primary language**: Go
- **Purpose**: Self-hostable infrastructure (Firecracker orchestrator, API, envd) powering E2B Cloud.
- **Verdict**: PASS-TO-DEEP — distinct from E2B SDK; relevant if SO needs air-gapped/on-prem sandbox plane (ADR-142 air-gapped surface).
- **Rationale**: SO currently consumes E2B as SaaS. For ADR-142 (air-gapped/compliance), self-hostable Firecracker stack is the leading open option; deep dive should evaluate ops complexity vs. testcontainers fallback, GPU support, and license/digest pinning surface.

### 4. meta-llama/PurpleLlama
- **URL**: https://github.com/meta-llama/PurpleLlama
- **License**: Llama 3.2 Community License (NOT OSI; redistribution limits)
- **Stars**: 4,162
- **Last commit**: 2026-05-05
- **Primary language**: Python
- **Purpose**: Cybersec evals (CyberSecEval), Llama Guard, Prompt Guard, CodeShield — LLM safety taxonomy + benchmarks.
- **Verdict**: PATTERNS-ONLY (no code adoption per cluster constraint).
- **Rationale**: License blocks adoption. CyberSecEval taxonomy (MITRE ATT&CK mapping, insecure-code categories) and CodeShield static-analysis trigger ideas inform our redteam-harness/aguara expansions. Phase 2 should produce a clean-room patterns digest, not vendor any code.

### 5. praetorian-inc/augustus
- **URL**: https://github.com/praetorian-inc/augustus
- **License**: Apache-2.0
- **Stars**: 203
- **Last commit**: 2026-05-06
- **Primary language**: Go
- **Purpose**: LLM security testing — 190+ probes for prompt injection / jailbreaks / adversarial attacks across 28 providers; single Go binary.
- **Verdict**: PASS-TO-DEEP — strong delta vs. Aguara (Aguara is rule-based defense, this is offensive probe corpus). Successor-positioned to garak.
- **Rationale**: Single-binary Go fits SO's local-first stance; 190 probes is a meaningful corpus to fold into `redteam-harness`/`pentest-self`. Deep dive: probe taxonomy overlap with Aguara's 189 rules, integration as scheduled CI lane, license-pin via digest.

### 6. pyca/cryptography
- **URL**: https://github.com/pyca/cryptography
- **License**: Apache-2.0 OR BSD-3-Clause (dual)
- **Stars**: 7,581
- **Last commit**: 2026-05-05
- **Primary language**: Python (Rust internals)
- **Purpose**: De facto Python crypto primitives library.
- **Verdict**: SKIP — foundational dep, not a research target. Already a transitive dep across the stack.
- **Rationale**: Not a scout candidate. No deep dive needed unless a specific crypto-policy ADR requires audit.

### 7. semgrep/semgrep
- **URL**: https://github.com/semgrep/semgrep
- **License**: LGPL-2.1 (CLI binary; rules separate)
- **Stars**: 15,026
- **Last commit**: 2026-05-06
- **Primary language**: OCaml
- **Purpose**: Lightweight static analysis with code-pattern rules across many languages.
- **Verdict**: PASS-TO-DEEP — used as external binary (LGPL allows tool consumption); SO already has a `semgrep-scan` skill listed.
- **Rationale**: LGPL-2.1 is acceptable for external-tool invocation (we don't link/embed). Deep dive: confirm the existing `semgrep-scan` skill is wired, evaluate custom-rule pack for SO's Python/Go surface, integrate into pre-commit gate alongside Aguara. No code adoption.

### 8. snyk/agent-scan
- **URL**: https://github.com/snyk/agent-scan
- **License**: Apache-2.0
- **Stars**: 2,347
- **Last commit**: 2026-05-05
- **Primary language**: Python
- **Purpose**: Security scanner specifically for AI agents, MCP servers, and agent skills.
- **Verdict**: PASS-TO-DEEP — direct fit for SO's MCP-heavy + skills surface; clear delta vs. Aguara (which is general-purpose).
- **Rationale**: Targets exactly our threat surface (MCP servers, skills/.claude config). Deep dive: rule overlap with Aguara, false-positive rate on our 200+ skills, CI integration cost, comparison to `mcp-scan` if surfaced later.

### 9. testcontainers/testcontainers-python
- **URL**: https://github.com/testcontainers/testcontainers-python
- **License**: Apache-2.0
- **Stars**: 2,208
- **Last commit**: 2026-04-30
- **Primary language**: Python
- **Purpose**: Pythonic API for ephemeral Docker containers in tests (DBs, brokers, custom images).
- **Verdict**: PASS-TO-DEEP — candidate for sandbox layer below E2B for non-microVM-grade isolation (faster, no SaaS dep).
- **Rationale**: Complements e2b/infra — Docker isolation tier for integration tests + lab-mode flow #1 sandboxing. Deep dive: compare with current ad-hoc `subprocess`/Docker patterns, propose as `sandbox-sample` skill backend.

### 10. vaporif/parry-guard
- **URL**: https://github.com/vaporif/parry-guard
- **License**: MIT
- **Stars**: 37 (low — risk flag)
- **Last commit**: 2026-05-05
- **Primary language**: Rust
- **Purpose**: Prompt-injection scanner for Claude Code; runs DeBERTa/Llama transformers via Candle or ONNX.
- **Verdict**: REJECT (shallow) — already integrated per [`parry-integration`] in RULES-COMPACT. Re-check during a future hardening sprint, not this batch.
- **Rationale**: Existing integration. 37 stars also means thin maintainer base; bus-factor risk to surface in the integration's risk register.

## Phase 2 Candidates

Ranked by expected delta vs. existing SO security stack (Aguara + E2B + NeMo-Guardrails + parry):

1. **snyk/agent-scan** — agents/MCP/skills-specific scanning; cleanest delta; Apache-2.0.
2. **praetorian-inc/augustus** — offensive probe corpus (190+); Go single-binary; Apache-2.0.
3. **e2b-dev/infra** — air-gapped sandbox plane for ADR-142; Apache-2.0; ops-heavy.
4. **testcontainers/testcontainers-python** — Docker isolation tier; Apache-2.0.
5. **semgrep/semgrep** — confirm/extend existing skill; LGPL-2.1 (tool-only).

Patterns-only (no deep code dive): **meta-llama/PurpleLlama** (Llama Community License) — extract CyberSecEval taxonomy + CodeShield trigger ideas via clean-room digest.

Skipped: NeMo-Guardrails, E2B SDK, parry-guard (already integrated); pyca/cryptography (foundational dep, not a research target).
