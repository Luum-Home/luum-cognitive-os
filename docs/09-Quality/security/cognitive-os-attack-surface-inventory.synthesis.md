---
type: quality-synthesis
source: docs/09-Quality/security/cognitive-os-attack-surface-inventory.md
provenance: "Dated (2026-05-05) local deterministic inventory of Cognitive OS's security-relevant surfaces — hooks, rules, skills, scripts, manifests, lib, and red-team tests — with file counts, runtime-flag governance, and a highest-risk surface ranking."
---

## What it is

A point-in-time, locally-generated inventory quantifying the SO's security-relevant surface area by directory, listing the security-oriented hooks and skills that existed at scan time, summarizing runtime-flag governance, and ranking the highest-risk local surfaces with their existing controls and gaps. Explicitly scoped to exclude inspection of blocked-secret paths themselves.

## Key mechanics

- **Surface counts** (files observed): `hooks/` 226, `rules/` 112, `skills/` 94, `scripts/` 356 (flagged as highest shell/process risk), `manifests/` 40, `lib/` 234, `tests/red_team/` 51, `tests/security/` 1 (the newly added unified red-team runner tests), `docs/09-Quality/security/` 4.
- **Representative security-oriented hooks** cited by name: a private-data/untrusted-content/outbound-action gate, a secret-detection hook, a confidentiality-policy enforcer, destructive-action guards (rm and git), adversarial-input/exfiltration scanners, an MCP-integration scanner, an opt-in SAST hook, false-completion/evidence gates (plan, orchestrator, generic claim validators), abuse/cost/DoS controls (rate limiter and precheck), and a portability/falsification coverage gate.
- **Security/red-team skills present before this pass**: `/red-team`, `/redteam-harness`, `/pentest-self`, `/security-audit`, `/vulnerability-scan`, `/memory-scan`, `/semgrep-scan`, `/audit-integrity`, plus `/security-red-team` newly added by this inventory pass as a unified inventory/threat/probe/score/backlog primitive.
- **Runtime flag governance**: `manifests/runtime-env-flags.yaml` lists 21 public runtime flags across 8 categories — secret-loading, hook-suppression, model-dispatch, startup-safe-mode, test-opt-in, safety-bypass, optional-service, and watchdog-observability.
- **Local posture observations**: `/security-red-team` ran with all required probes passing, scoring 72/100 overall, with sub-scores for a credential-safe-runner primitive (81), the red-team harness (73), input-injection scanners (66), MCP security surface (68), and runtime-flag governance (70). Committed settings now carry explicit deny entries for sensitive file classes (env files, secret directories, key/cert files, git config). The runtime is characterized as effectively fully-permissive, meaning SO controls are operational-layer only unless paired with external sandboxing.
- **Highest-risk surfaces table** (8 rows): shell scripts (arbitrary process/network/filesystem side effects; no global sandbox, many scripts can source environment or install packages); MCP integrations (metadata-based poisoning, credential-adjacent access; scanner optional, trust-on-first-use needs strengthening); runtime env flags (can suppress hooks or bypass safety; active dangerous-flag audit is a follow-up); protected config files (adversarial input could alter hooks/rules/MCP configs/agent settings; needs broader cross-runtime testing beyond one harness's settings); network egress (a command guard, not a packet-level firewall); MCP trust pins (drift/poisoning risk; no MCP servers discovered in the current project at scan time, pins to be added if/when introduced); long-lived memory/session summaries (need tests for memory poisoning and secret persistence); provider dispatch (cost abuse, fallback spoofing, provider-credential exposure risk; needs adversarial tests for fake metrics and untrusted model-output trust boundaries).

## Relations & where used

- Companion inventory to `cognitive-os-agent-security-research-2026-05-05.md` (this doc supplies the raw surface counts and posture numbers that research doc's scorecard references) and `credential-safe-runner-red-team-2026-05-05.md` (the credential-safe-runner sub-score of 81 traces to that review).
- References `manifests/runtime-env-flags.yaml`, `hooks/lethal-trifecta-gate.sh`, `hooks/secret-detector.sh`, `hooks/confidentiality-enforcer.sh`, `hooks/destructive-rm-blocker.sh`, `hooks/destructive-git-blocker.sh`, `hooks/parry-scan.sh`, `hooks/aguara-scan.sh`, `hooks/mcp-scan.sh`, `hooks/semgrep-scan.sh`, `hooks/plan-claim-validator.sh`, `hooks/orchestrator-claim-gate.sh`, `hooks/claim-validator.sh`, `hooks/rate-limiter.sh`, `hooks/rate-limit-precheck.sh`, `hooks/scope-marker-portability-gate.sh`.

## Status / caveats

Explicitly dated (2026-05-05) and framed as a local snapshot ("local deterministic inventory") — file counts, the 72/100 score, and per-primitive sub-scores will drift as the codebase changes and should not be read as current live numbers. The doc itself notes no MCP servers were discovered in the scanned project at the time, which may no longer hold.
