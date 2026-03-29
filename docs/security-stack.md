# Cognitive OS Security Stack

> Last updated: 2026-03-28 | Layers: 8 | Tools: 19 active, 8 optional, 5 planned

The single source of truth for the Cognitive OS security posture. Every defense layer, every tool, every gap.

## Security Posture Summary

| Metric | Value |
|--------|-------|
| Active defense layers | 8 |
| Active tools/hooks (always on) | 19 |
| Optional tools (install to enable) | 8 |
| Planned integrations | 5 |
| MCP-specific defenses | 3 (1 optional, 2 planned) |
| Supply chain protections | 4 |
| Red team / pentest tools | 4 (1 active, 1 optional, 2 planned) |

## Complete Security Stack

### Layer 1: Input Validation (Before Agent Launch)

Prevents malformed, vague, or malicious prompts from reaching agents.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 1.1 | Clarification Gate | Hook | **ACTIVE** | Vague prompts interpreted minimally; score >60 blocks | `hooks/clarification-gate.sh` | Internal |
| 1.2 | Blast Radius Estimation | Hook | **ACTIVE** | High-impact tasks launched without awareness | `hooks/blast-radius.sh` | Internal |
| 1.3 | Dry-Run Preview | Hook | **ACTIVE** | Unintended execution during pipeline preview | `hooks/dry-run-preview.sh` | Internal |
| 1.4 | Prompt Quality Scoring | Hook | **ACTIVE** | Weak prompts missing criteria/context (advisory) | `hooks/prompt-quality.sh` | Internal |
| 1.5 | Aguara Scan | Hook | **OPTIONAL** | Prompt injection, data exfil, supply chain (189 rules, 14 categories) | `hooks/aguara-scan.sh` | Apache-2.0 |
| 1.6 | Parry Guard | Hook | **OPTIONAL** | ML-based prompt injection detection (DeBERTa transformers) | `hooks/parry-scan.sh` (documented) | OSS |

### Layer 2: Permission and Identity

Enforces least-privilege access and maintains a full audit trail for every agent action.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 2.1 | Agent Permissions | Protocol | **ACTIVE** | Unauthorized access; 6 levels (NONE-ADMIN), 5 profiles, TTL max 120min | `rules/agent-security.md` | Internal |
| 2.2 | Agent Identity | Protocol | **ACTIVE** | Untracked actions; WHO/WHAT/WHEN/WHERE/WHY audit trail | `rules/agent-identity.md` | Internal |
| 2.3 | Always-Blocked Paths | Config | **ACTIVE** | Direct access to secrets regardless of permission level | Hardcoded in permissions | Internal |
| 2.4 | Monotonic Attenuation | Protocol | **ACTIVE** | Child agents escalating beyond parent permissions | `rules/agent-security.md` | Internal |
| 2.5 | Credential Management | Protocol | **ACTIVE** | Hardcoded secrets; env-var-only, validated at startup | `rules/credential-management.md` | Internal |

**Always-blocked paths** (no permission level can override):
```
.env, .env.*, *.key, *.pem, *.p12, secrets/*, **/credentials*, **/password*, .git/config
```

### Layer 3: Code Security (After Code Generation)

Scans generated code for vulnerabilities, anti-patterns, and license violations.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 3.1 | Content Policy | Hook | **ACTIVE** | Prohibited terms/patterns in generated files | `hooks/content-policy.sh` | Internal |
| 3.2 | Secret Detector | Hook | **ACTIVE** | Credentials leaked into source code | `hooks/secret-detector.sh` | Internal |
| 3.3 | License Guard | Protocol | **ACTIVE** | AGPL/SSPL/BSL/ELv2/Commons Clause dependencies | `rules/license-policy.md` | Internal |
| 3.4 | Semgrep SAST | Hook | **OPTIONAL** | Security vulnerabilities, coding anti-patterns | `hooks/semgrep-scan.sh` | OSS |
| 3.5 | Semgrep AI Rules | Config | **OPTIONAL** | 58 AI-specific rules (hardcoded keys, injection, MCP, hooks) | Semgrep `ai-best-practices` config | OSS |
| 3.6 | Trail of Bits Skills | Skills | **OPTIONAL** | 62 professional security audit skills (6 categories) | `.claude/plugins/trailofbits-skills/` | CC-BY-SA-4.0 |

### Layer 4: MCP Security

Protects the Model Context Protocol layer from tool poisoning, line-jumping, and configuration attacks.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 4.1 | mcp-aguara | MCP server | **OPTIONAL** | Runtime skill scanning via 5 MCP tools (scan, validate, discover) | MCP server config | MIT |
| 4.2 | MCP-Scan | CLI | **PLANNED** | Tool poisoning, injection in MCP server configurations | CLI hook (to create) | OSS |
| 4.3 | mcp-context-protector | MCP wrapper | **PLANNED** | Line-jumping, config manipulation, prompt injection via MCP | MCP server wrapper | MIT |
| 4.4 | Semgrep MCP Server | MCP server | **PLANNED** | Code vulnerabilities scanned via MCP interface | MCP server config | OSS |

### Layer 5: Supply Chain Defense

Prevents tampering with dependencies, Docker images, and installed packages.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 5.1 | SHA256 Docker Digest Pinning | Config | **ACTIVE** | Docker image tag manipulation (TeamPCP-style attack) | `docker-compose.*.yml` | Internal |
| 5.2 | Git Commit Hash Pinning | Code | **ACTIVE** | Git tag rewriting to inject malicious commits | `cos-lock.yaml` | Internal |
| 5.3 | Per-File Integrity Hashes | Code | **ACTIVE** | Individual file content tampering in packages | `cos audit` / lockfile | Internal |
| 5.4 | Prompt Injection Scanner (cos audit) | Code | **ACTIVE** | SKILL.md files containing "ignore previous instructions" | `cos audit` Gate 3 | Internal |

### Layer 6: Output Validation (After Agent Completion)

Catches hallucinated results, overclaimed confidence, scope creep, and assumption-laden output.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 6.1 | Scope Proportionality | Hook | **ACTIVE** | Small fix expanding into large rewrite | `hooks/scope-proportionality.sh` | Internal |
| 6.2 | Claim Validator | Hook | **ACTIVE** | Fabricated files, hallucinated test results | `hooks/claim-validator.sh` | Internal |
| 6.3 | Assumption Tracker | Hook | **ACTIVE** | Hidden assumptions that may be incorrect (3+ warns) | `hooks/assumption-tracker.sh` | Internal |
| 6.4 | Trust Score Validator | Hook | **ACTIVE** | Missing or incomplete Trust Reports | `hooks/trust-score-validator.sh` | Internal |
| 6.5 | Confidence Gate | Hook | **ACTIVE** | Low-confidence results propagating (blocks <50 in prod) | `hooks/confidence-gate.sh` | Internal |
| 6.6 | Clarification Interceptor | Hook | **ACTIVE** | Mid-task ambiguity causing incorrect assumptions | `hooks/clarification-interceptor.sh` | Internal |
| 6.7 | Cross Verifier | Library | **ACTIVE** | Second model catches first model hallucinations | `lib/cross_verifier.py` (protocol) | Internal |
| 6.8 | Scope Creep Detector | Hook | **ACTIVE** | Edits to files outside approved task scope | `hooks/scope-creep-detector.sh` | Internal |

### Layer 7: Runtime Protection

Prevents resource abuse, cost overruns, and runaway agent behavior during execution.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 7.1 | Rate Limiter | Hook | **ACTIVE** | Token flooding, agent spam (30 calls/min, $5/hr cap) | `hooks/rate-limiter.sh` | Internal |
| 7.2 | Rate Limit Protection | Hook | **ACTIVE** | API rate limit exhaustion (blocks at 95% usage) | `hooks/rate-limit-protection.sh` | Internal |
| 7.3 | Auto-Rollback | Hook | **ACTIVE** | Failed code accumulating after retry exhaustion | `hooks/auto-rollback-trigger.sh` | Internal |
| 7.4 | Circuit Breaker (Auto-Repair) | Protocol | **ACTIVE** | Runaway repair loops (2 consecutive = OPEN, 10/hr cap) | `rules/auto-repair.md` | Internal |
| 7.5 | Resource Governance | Protocol | **ACTIVE** | Budget overruns; model downgrade chain at 80/95/100% | `rules/resource-governance.md` | Internal |
| 7.6 | NeMo Guardrails | Service | **OPTIONAL** | PII detection, content filtering at runtime | Docker container | Apache-2.0 |

### Layer 8: Testing and Red Team

Proactively finds vulnerabilities before attackers do.

| # | Tool | Type | Status | What It Protects Against | Hook/Lib | License |
|---|------|------|--------|--------------------------|----------|---------|
| 8.1 | Pentest Self | Skill | **ACTIVE** | 7 critical test categories (injection, escalation, secrets, flooding, scope, integrity) | `skills/pentest-self/` (protocol) | Internal |
| 8.2 | Garak | Skill | **OPTIONAL** | LLM hallucination, data leakage, prompt injection (179 probes) | `skills/vulnerability-scan/` | Apache-2.0 |
| 8.3 | Promptfoo | CLI | **PLANNED** | Adversarial prompt testing, red teaming, CI/CD integration | red-team skill (to create) | MIT |
| 8.4 | AgentFence | CLI | **PLANNED** | Agent secret leakage, instruction exposure testing | vuln-test skill (to create) | OSS |

## Tool Status Definitions

| Status | Meaning |
|--------|---------|
| **ACTIVE** | Enabled by default, no installation needed. Part of core Cognitive OS. |
| **OPTIONAL** | Available but requires installation. Graceful degradation if missing. |
| **PLANNED** | Evaluated and approved for integration. Not yet implemented. |

## Tool Counts by Status

| Status | Count | Tools |
|--------|-------|-------|
| ACTIVE | 19 | Clarification Gate, Blast Radius, Dry-Run, Prompt Quality, Agent Permissions, Agent Identity, Always-Blocked Paths, Monotonic Attenuation, Credential Management, Content Policy, Secret Detector, License Guard, SHA256 Docker Pins, Commit Hash Pinning, Per-File Integrity, cos audit Gate 3, Scope Proportionality, Claim Validator, Assumption Tracker, Trust Score Validator, Confidence Gate, Clarification Interceptor, Cross Verifier, Scope Creep Detector, Rate Limiter, Rate Limit Protection, Auto-Rollback, Circuit Breaker, Resource Governance, Pentest Self |
| OPTIONAL | 8 | Aguara Scan, Parry Guard, Semgrep SAST, Semgrep AI Rules, Trail of Bits Skills, mcp-aguara, NeMo Guardrails, Garak |
| PLANNED | 5 | MCP-Scan, mcp-context-protector, Semgrep MCP Server, Promptfoo, AgentFence |

## Phase-Aware Behavior

Security enforcement scales with the project phase:

| Phase | Blocking Hooks | Advisory Hooks | Optional Tools |
|-------|---------------|----------------|----------------|
| reconstruction | Clarification Gate, Rate Limiter | Most output validation warns | Same |
| stabilization | + Content Policy blocks | Standard enforcement | Same |
| production | + Confidence Gate blocks <50, Scope Proportionality blocks | All warnings active | Same |
| maintenance | Maximum enforcement, all gates block | All warnings active | Same |

## Gap Analysis

| Gap | Severity | Current Mitigation | Planned Fix | ETA |
|-----|----------|-------------------|-------------|-----|
| No MCP-specific runtime defense | HIGH | Aguara scans prompts pre-launch | MCP-Scan + mcp-context-protector | Next sprint |
| No egress filtering | MEDIUM | Agent permissions restrict file access | Pipelock evaluation | Backlog |
| No AIBOM (AI Bill of Materials) | LOW | Manual tracking via cos-lock.yaml | OWASP AIBOM standard emerging | Backlog |
| No container vulnerability scanning | MEDIUM | SHA256 digest pinning prevents tampering | Trivy evaluation | Backlog |
| No runtime agent network monitoring | LOW | Rate limiting + resource governance | Aegis or Leash evaluation | Backlog |

## Attack Vectors and Defenses

| Attack Vector | Defense Layers | Primary Tool |
|---------------|---------------|-------------|
| Prompt injection | 1.1, 1.5, 1.6, 4.1 | Clarification Gate + Aguara + Parry |
| Credential exfiltration | 2.3, 2.5, 3.2 | Always-blocked paths + Secret Detector |
| Permission escalation | 2.1, 2.4 | 6-level permissions + monotonic attenuation |
| Hallucinated output | 6.2, 6.4, 6.5, 6.7 | Claim Validator + Trust Score + Cross Verifier |
| Supply chain compromise | 5.1, 5.2, 5.3, 5.4 | Digest pinning + commit pinning + integrity hashes |
| Token/cost flooding | 7.1, 7.2, 7.5 | Rate Limiter + Rate Limit Protection + Budget governance |
| Scope creep / rewrite | 6.1, 6.8 | Scope Proportionality + Scope Creep Detector |
| AGPL/copyleft contamination | 3.3 | License Guard blocks AGPL/SSPL/BSL |
| MCP tool poisoning | 4.1, 4.2, 4.3 | mcp-aguara + MCP-Scan (planned) |
| Docker image tampering | 5.1 | SHA256 digest pinning (not tags) |
| Git tag manipulation | 5.2 | Commit hash pinning in cos-lock.yaml |
| Low-confidence propagation | 6.5 | Confidence Gate blocks <50 in production |
| Runaway repair loops | 7.4 | Circuit breaker: 2 consecutive = OPEN |

## Graceful Degradation

Every optional tool follows the same pattern:

```bash
# Check if tool is installed -- skip silently if not
if ! command -v tool-name &>/dev/null; then
  exit 0
fi
```

The Cognitive OS functions with zero optional tools installed. Optional tools are additive defense layers that strengthen the posture but are never required for operation. All 19 active tools are internal with no external dependencies.

## How to Add a New Security Tool

When adding a new security tool to the Cognitive OS:

1. **Classify the layer**: Determine which of the 8 layers the tool belongs to
2. **Add a row** to the appropriate layer table in this document
3. **Set status**: ACTIVE (always on), OPTIONAL (install to enable), or PLANNED (not yet integrated)
4. **Create integration**: Hook, skill, or package following the `packages/ecosystem-tools/` pattern
5. **Add graceful degradation**: System must work identically without the tool installed
6. **Document in ecosystem-tools.md**: Add entry to `packages/ecosystem-tools/rules/ecosystem-tools.md`
7. **Write behavior tests**: Add test cases to `tests/behavior/test_security_documentation.py`
8. **Update summary counts**: Update the counts in the Security Posture Summary table at the top of this document
9. **Update safety-mesh.md**: If the tool is a hook in the pre/post pipeline, add it to `docs/safety-mesh.md`
10. **Run pentest verification**: Execute `/pentest-self` to verify no regressions

## Installation Guide for Optional Tools

### Aguara (Agent Security Scanner)
```bash
go install github.com/garagon/aguara@latest
# Enable: cognitive-os.yaml -> security.aguara.enabled: true
```

### Parry (ML Prompt Injection)
```bash
brew install vaporif/tap/parry-guard
export HF_TOKEN=your_token  # Required for model download
```

### Semgrep (SAST)
```bash
pip install semgrep
export SEMGREP_ENABLED=true
# For AI rules: add p/ai-best-practices to semgrep config
```

### Trail of Bits Skills
```bash
bash scripts/install-tob-skills.sh
```

### Garak (LLM Vulnerability Scanner)
```bash
pip install garak
# See skills/vulnerability-scan/SKILL.md
```

### NeMo Guardrails
```bash
docker compose up -d nemo-guardrails
# Starts automatically via smart_infra when needed
```

### mcp-aguara (MCP Server)
```bash
go install github.com/garagon/mcp-aguara@latest
# Add to .claude/settings.json mcpServers
```

## References

| Document | What It Covers |
|----------|---------------|
| `docs/safety-mesh.md` | Detailed hook behavior for the 12-layer pre/post pipeline mesh |
| `.cognitive-os/plans/research/security-tools-landscape.md` | Full evaluation of 50+ security tools |
| `packages/ecosystem-tools/rules/ecosystem-tools.md` | Integration patterns for external tools |
| `packages/aguara-security/rules/aguara-integration.md` | Aguara scanner configuration and behavior |
| `rules/pentesting-readiness.md` | 7 critical test cases and testing schedule |
| `rules/agent-security.md` | Permission levels, profiles, and blocked paths |
| `rules/supply-chain-defense.md` | Docker/git/package integrity protocols |
| `rules/credential-management.md` | Credential hygiene and validation patterns |
| `rules/content-policy.md` | Prohibited terms and automated enforcement |
| `rules/security-scanning.md` | Semgrep SAST integration details |
| `rules/license-policy.md` | Full license compatibility matrix |
