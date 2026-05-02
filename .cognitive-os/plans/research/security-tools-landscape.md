# Security Tools Landscape — P1/P2 Integration Status

Research document tracking security tool evaluations and implementation status for Cognitive OS.
Last assessed: 2026-04-10.

---

## Status Matrix — All Security Tools

| Tool | Hook File | Registered in settings.json | In paranoid profile | Config gate | Verdict |
|------|-----------|----------------------------|---------------------|-------------|---------|
| `secret-detector.sh` | ✅ exists | ✅ YES (Edit\|Write) | ✅ yes | none | **ACTIVE** |
| `content-policy.sh` | ✅ exists | ✅ YES (Edit\|Write) | ✅ yes | none | **ACTIVE** |
| `confidentiality-enforcer.sh` | ✅ exists | ✅ YES (Edit\|Write) | ✅ yes | none | **ACTIVE** |
| `aguara-scan.sh` | ✅ exists | ❌ NOT registered | ✅ paranoid PreAgent | `aguara.enabled: false` | **HOOK EXISTS, NOT REGISTERED** |
| `semgrep-scan.sh` | ✅ exists | ❌ NOT registered | ✅ paranoid PostAgent | `SEMGREP_ENABLED=false` | **HOOK EXISTS, NOT REGISTERED** |
| `parry-scan.sh` | ✅ exists | ❌ NOT registered | ❌ missing from profile script | `parry.enabled: false` | **HOOK EXISTS, NOT IN ANY PROFILE** |
| `mcp-scan.sh` | ✅ exists | ❌ NOT registered | ❌ missing from profile script | `mcp_scan.enabled: false` | **HOOK EXISTS, NOT IN ANY PROFILE** |
| `guardrails-validator.sh` | ✅ exists | ❌ NOT registered | ❌ missing from profile script | `GUARDRAILS_ENABLED=false` | **HOOK EXISTS, NOT IN ANY PROFILE** |

### Tools with Skills/Documentation Only (no hook, on-demand)

| Tool | Skill | Install Script | Status |
|------|-------|---------------|--------|
| Garak | `skills/vulnerability-scan/SKILL.md` | `scripts/install-garak.sh` | **ON-DEMAND ONLY** |
| Promptfoo | No skill yet | `scripts/install-promptfoo.sh` | **INSTALL SCRIPT ONLY** |
| tero | `packages/tero-testing/rules/` | manual | **DOCUMENTED, WATCH** |
| mantis | `packages/mantis-security/rules/` | manual | **DOCUMENTED, WATCH** |
| LlamaFirewall | ecosystem-tools.md EVALUATE | none | **EVALUATE** |
| AgentGateway | ecosystem-tools.md EVALUATE | none | **EVALUATE** |
| OneCLI | ecosystem-tools.md EVALUATE | none | **EVALUATE** |

---

## Critical Finding: Security Hooks Are All Unregistered

The current `settings.json` uses a custom intermediate profile (29 hooks) but **none of the
dedicated security scanner hooks are registered**:

- `aguara-scan.sh` — PreToolUse Agent — 189-rule agent prompt scanner
- `semgrep-scan.sh` — PostToolUse Agent — SAST after code changes
- `parry-scan.sh` — PreToolUse Agent — ML prompt injection scanner
- `mcp-scan.sh` — SessionStart — MCP config scanner
- `guardrails-validator.sh` — PostToolUse Agent — PII/jailbreak detector

The only active security hooks are:
- `secret-detector.sh` — credential leak prevention (on every Edit|Write)
- `content-policy.sh` — prohibited term enforcement (on every Edit|Write)
- `confidentiality-enforcer.sh` — IP leak prevention (on every Edit|Write)

Additionally, `parry-scan.sh`, `mcp-scan.sh`, and `guardrails-validator.sh` are **not even
included in the paranoid profile** — there's a gap in `scripts/set-security-profile.sh`.

---

## Implementation Gaps: Described but Unenforced

| Capability | Described In | Enforcement | Gap |
|------------|-------------|-------------|-----|
| Agent prompt scanning (deterministic) | `packages/aguara-security/rules/aguara-integration.md` | ❌ hook not registered | HIGH |
| Agent prompt scanning (ML) | `packages/ecosystem-tools/rules/parry-integration.md` | ❌ hook not registered, not in profile | HIGH |
| SAST on code changes | `rules/security-scanning.md` | ❌ hook not registered | MEDIUM |
| MCP config scanning | `packages/ecosystem-tools/rules/ecosystem-tools.md` | ❌ hook not registered, not in profile | MEDIUM |
| PII/jailbreak detection on output | `hooks/guardrails-validator.sh` | ❌ hook not registered, not in profile | MEDIUM |
| LLM vulnerability probing | `packages/ecosystem-tools/rules/ecosystem-tools.md` | ✅ on-demand via skill | LOW (on-demand OK) |

---

## Quick Wins — Activatable With Minimal Effort

### QW1: Register aguara-scan + semgrep-scan in settings.json (30 min)

Both hooks are fully implemented with graceful degradation (skip if tool not installed).
Just need to add them to `settings.json` PreToolUse and PostToolUse Agent sections.

```json
// In PreToolUse Agent group — add after clarification-gate:
{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/aguara-scan.sh\"" }

// In PostToolUse Agent group — add after completion-gate:
{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/semgrep-scan.sh\"" }
```

Both have `enabled: false` config gates and graceful skip if binary missing — no disruption.

### QW2: Add parry + mcp-scan + guardrails to paranoid profile script (30 min)

`scripts/set-security-profile.sh` paranoid profile is missing three hooks. Add to profile:

```bash
# In paranoid SessionStart — add after crash-recovery:
"mcp-scan.sh"

# In paranoid PreToolUse Agent — add after aguara-scan:
"parry-scan.sh"

# In paranoid PostToolUse Agent — add after semgrep-scan:
"guardrails-validator.sh"
```

### QW3: Add mcp-scan to standard settings.json (SessionStart) (15 min)

mcp-scan runs at SessionStart with graceful degradation. Zero overhead when tool not installed.
Low cost to add to standard profile as well.

### QW4: Install aguara binary to enable the hook (15 min)

```bash
go install github.com/garagon/aguara@latest
# Then set in cognitive-os.yaml:
security.aguara.enabled: true
```

The hook exists and works — just needs the binary installed.

---

## Priority Ranking — Risk Reduction / Effort Ratio

| Priority | Action | Risk Reduction | Effort | Ratio |
|----------|--------|---------------|--------|-------|
| P1 | Register `aguara-scan.sh` in settings.json PreToolUse Agent | HIGH (189-rule prompt scanner) | ~15 min | **CRITICAL** |
| P2 | Register `semgrep-scan.sh` in settings.json PostToolUse Agent | HIGH (SAST on code) | ~15 min | **HIGH** |
| P3 | Add `parry-scan.sh` + `mcp-scan.sh` + `guardrails-validator.sh` to paranoid profile | HIGH (completes security triad) | ~30 min | **HIGH** |
| P4 | Add `mcp-scan.sh` to standard settings.json SessionStart | MEDIUM (MCP config scan) | ~10 min | **HIGH** |
| P5 | Install aguara binary + set `enabled: true` | HIGH (enables P1 to actually fire) | ~15 min | **HIGH** |
| P6 | Create promptfoo SKILL.md for red-team testing | MEDIUM (structured red-team) | ~2 hrs | **MEDIUM** |
| P7 | Evaluate LlamaFirewall vs current stack | MEDIUM (agentic tool-call monitoring) | ~1 day | **LOW** |
| P8 | Evaluate AgentGateway for MCP/A2A RBAC | LOW (infrastructure overlay) | ~2 days | **LOW** |
| P9 | Integrate OneCLI credential vault | LOW (Phase 2 goal) | ~3 days | **LOW** |

---

## Updated Top-10 Status Table

| Tool | Category | License | Status | Implementation Status | Gap |
|------|----------|---------|--------|----------------------|-----|
| `secret-detector.sh` | Credential leak prevention | N/A | ADOPT | **ACTIVE** (always registered) | none |
| `content-policy.sh` | Content enforcement | N/A | ADOPT | **ACTIVE** (always registered) | none |
| Aguara | Agent Security Scanner | Apache-2.0 | ADOPT | **HOOK READY, NOT REGISTERED** | P1: register hook |
| Semgrep | SAST | LGPL-2.1 | ADOPT | **HOOK READY, NOT REGISTERED** | P2: register hook |
| Parry / parry-guard | Prompt Injection | MIT | ADOPT | **HOOK READY, NOT IN PROFILE** | P3: add to profiles |
| mcp-scan | MCP Security Scanner | MIT | ADOPT | **HOOK READY, NOT REGISTERED** | P3/P4: register hook |
| Garak | LLM Vulnerability Scanner | Apache-2.0 | ADOPT | **SKILL ONLY** (on-demand) | acceptable |
| Guardrails AI | PII/Jailbreak Detector | Apache-2.0 | ADOPT | **HOOK READY, NOT IN PROFILE** | P3: add to profiles |
| tero | HTTP Chaos Testing | Apache-2.0 | WATCH | **DOCUMENTED** | no hook needed |
| mantis | HTTP Security Toolkit | Apache-2.0 | WATCH | **DOCUMENTED** | no hook needed |
| LlamaFirewall | AI Security Framework | MIT | EVALUATE | **DOCUMENTED** | evaluation pending |
| AgentGateway | AI-Native Proxy | Apache-2.0 | EVALUATE | **DOCUMENTED** | evaluation pending |
| OneCLI | Agent Credential Vault | OSS | EVALUATE | **DOCUMENTED** | Phase 2 target |

---

## Completed Implementations

| Item | Status | Date |
|------|--------|------|
| `secret-detector.sh` registered in settings.json and all profiles | **DONE** | 2026-04-10 |
| `content-policy.sh` registered in settings.json and all profiles | **DONE** | 2026-04-10 |
| `confidentiality-enforcer.sh` registered in settings.json and all profiles | **DONE** | 2026-04-10 |
| Garak vulnerability scan skill (`skills/vulnerability-scan/SKILL.md`) created | **DONE** | 2026-04-10 |
| Garak install script (`scripts/install-garak.sh`) created | **DONE** | 2026-04-10 |
| Aguara hook (`hooks/aguara-scan.sh`) implemented with graceful degradation | **DONE** | 2026-04-10 |
| Semgrep hook (`hooks/semgrep-scan.sh`) implemented with graceful degradation | **DONE** | 2026-04-10 |

---

## Immediate Next Actions

```
1. [ ] Register aguara-scan.sh in settings.json (PreToolUse Agent)
2. [ ] Register semgrep-scan.sh in settings.json (PostToolUse Agent)
3. [ ] Register mcp-scan.sh in settings.json (SessionStart)
4. [ ] Update set-security-profile.sh to include parry, mcp-scan, guardrails in paranoid
5. [ ] Install aguara binary: go install github.com/garagon/aguara@latest
6. [ ] Set security.aguara.enabled: true in cognitive-os.yaml (or keep config-gated)
```

Steps 1-4 are pure config changes (no code, no dependencies) and take <1 hour total.
Steps 5-6 enable actual scanning but are optional if the graceful degradation pattern is acceptable.

---

## Stack Integration Map (Corrected)

```
Agent Prompt → [MISSING] aguara-scan.sh (PreToolUse) → [BLOCKER if CRITICAL]
               [MISSING] parry-scan.sh (PreToolUse)  → [advisory ML detection]
               clarification-gate.sh (active)
               blast-radius.sh (active)

Code Changes → [MISSING] semgrep-scan.sh (PostToolUse after sdd-apply) → findings log

File Writes  → secret-detector.sh (active, Edit|Write)
               content-policy.sh (active, Edit|Write)
               confidentiality-enforcer.sh (active, Edit|Write)

Session Start → [MISSING] mcp-scan.sh (SessionStart) → MCP config validation

Agent Output → [MISSING] guardrails-validator.sh (PostToolUse Agent) → PII detection
               trust-score-validator.sh (active)
               claim-validator.sh (active)

On-demand    → /vulnerability-scan (garak) → LLM probe report
             → /security-audit → comprehensive security review
```
