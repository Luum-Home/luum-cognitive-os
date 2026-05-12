# Cognitive OS Attack Surface Inventory — 2026-05-05

## Scope

Local deterministic inventory of security-relevant Cognitive OS surfaces. This
file does not inspect blocked secret paths such as `.env`, `*.key`, `*.pem`,
`secrets/*`, or `.git/config`.

## Surface counts

| Surface | Files observed | Security relevance |
|---|---:|---|
| `hooks/` | 226 | Runtime lifecycle gates; can block, inject context, audit, or mutate state. |
| `rules/` | 112 | Governance and policy context; susceptible to prompt/rule injection and drift. |
| `skills/` | 94 | User-invocable agentic procedures; can encode tool flows and assumptions. |
| `scripts/` | 356 | Local execution surface; highest shell/process risk. |
| `manifests/` | 40 | Contracts/allowlists/scoring; tamper resistance depends on review and tests. |
| `lib/` | 234 | Provider dispatch, permissions, memory, metrics, orchestration. |
| `tests/red_team/` | 51 | Existing adversarial/portability scenarios. |
| `tests/security/` | 1 | New unified security-red-team runner tests. |
| `docs/09-Quality/security/` | 4 | Security control docs and red-team plans. |

## Security-oriented hooks found

Representative security hooks include:

- `hooks/lethal-trifecta-gate.sh` — private data + untrusted content + external communication gate.
- `hooks/secret-detector.sh` — secret detection hook.
- `hooks/confidentiality-enforcer.sh` — confidentiality policy enforcement.
- `hooks/destructive-rm-blocker.sh` and `hooks/destructive-git-blocker.sh` — destructive action guards.
- `hooks/parry-scan.sh` and `hooks/aguara-scan.sh` — prompt injection/exfiltration scanners.
- `hooks/mcp-scan.sh` — MCP tool poisoning/cross-origin scanner.
- `hooks/semgrep-scan.sh` — opt-in SAST hook.
- `hooks/plan-claim-validator.sh`, `hooks/orchestrator-claim-gate.sh`, `hooks/claim-validator.sh` — false-done/evidence gates.
- `hooks/rate-limiter.sh`, `hooks/rate-limit-precheck.sh` — abuse/cost/DoS controls.
- `hooks/scope-marker-portability-gate.sh` — portability and falsification coverage gate.

## Security/red-team skills found

Core skills already available before this pass:

- `/red-team` — Promptfoo prompt red-team evals.
- `/redteam-harness` — deterministic false-done/evidence red-team scenarios.
- `/pentest-self` — safety mesh self-penetration testing.
- `/security-audit` — config/secrets/hooks/infrastructure audit.
- `/vulnerability-scan` — Garak LLM endpoint probes.
- `/memory-scan` — prompt injection/exfiltration/invisible Unicode scan before memory persistence.
- `/semgrep-scan` — SAST scan.
- `/audit-integrity` — integrity audit for skills/hooks/libs/config.
- `/security-red-team` — newly added unified inventory/threat/probe/score/backlog primitive.

## Runtime flag governance

`manifests/runtime-env-flags.yaml` currently lists 21 public runtime flags across:

- `secret-loading` — `COS_SKIP_DOTENV`, `COS_ALLOW_CREDENTIAL_SAFE_ENV`.
- `hook-suppression` — `DISABLE_HOOK_*`.
- `llm-dispatch` — Qwen/Claude/fallback switches.
- `startup-safe-mode` — startup/session circuit breakers.
- `test-opt-in` — expensive/headless/database test opt-ins.
- `safety-bypass` — concurrent writes, destructive git, direct main.
- `optional-service` — scanners/services such as Semgrep, Aguara, Agent Bus, Bifrost.
- `watchdog-observability` — watchdog and hot-path observability flags.

## Local posture observations

1. `/security-red-team` ran with all required probes passing and score `72/100`.
2. Primitive scores were:
   - `credential-safe-runner`: 81
   - `redteam-harness`: 73
   - `prompt-injection-scanners`: 66
   - `mcp-security-surface`: 68
   - `runtime-env-flag-governance`: 70
3. The repository has strong governance density, but many controls are optional,
   advisory, or dependent on external tools being installed.
4. `.claude/settings.json` now contains explicit `permissions.deny` entries for
   `.env`, `.env.*`, `secrets/**`, key/cert files, and `.git/config`.
5. The current Codex runtime is effectively `danger-full-access`; SO controls are
   operational unless paired with external sandboxing.

## Highest-risk local surfaces

| Surface | Why risky | Existing controls | Gap |
|---|---|---|---|
| Shell scripts | Arbitrary process, network, filesystem side effects. | Hooks, blocked path policy, credential-safe runner, destructive blockers. | No global OS sandbox; many scripts can source env or install packages. |
| MCP servers/tools | Tool poisoning, hidden instructions, credential access. | `mcp-scan.sh`, host CLI bridge contract, docs. | Scanner optional; MCP server credentials and trust-on-first-use need stronger local contracts. |
| Runtime env flags | Can suppress hooks or bypass safety. | `manifests/runtime-env-flags.yaml`, docs. | Active dangerous-flag runtime audit remains a follow-up. |
| Protected config files | Prompt injection can alter hooks, rules, MCP configs, or IDE agent settings. | `hooks/protected-config-write-guard.sh`, `manifests/protected-config-write-policy.yaml`. | Needs broader cross-runtime projection tests beyond Claude settings. |
| Network egress | Prompt injection can turn shell/network access into exfiltration. | `hooks/network-egress-guard.sh`, `manifests/network-egress-policy.yaml`. | This is a command guard, not a packet firewall. |
| MCP trust pins | MCP tool/server definitions can drift or be poisoned. | `scripts/mcp_tofu_audit.py`, `manifests/mcp-trust-pins.yaml`. | Current project has no discovered MCP servers; add pins when servers are introduced. |
| Agent memory/session summaries | Long-lived prompt injection or secret persistence. | `/memory-scan`, Engram rules, session summaries. | Need tests for memory poisoning and secret persistence. |
| Provider dispatch | Cost abuse, fallback spoofing, provider credential leakage. | LLM dispatch rules/runbooks, Qwen smoke, metrics. | Need adversarial tests for fake provider metrics and untrusted model-output trust boundaries. |
