# Primitive Scope Unknown Triage

This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.

## Summary

```json
{
  "by_bucket": {
    "conflicting-metadata": 4,
    "insufficient-metadata": 234,
    "os-only-semantic-candidate": 1,
    "project-only-semantic-candidate": 2
  },
  "by_declared_scope": {
    "both": 237,
    "os-only": 4
  },
  "by_gap": {
    "conflicting-distribution-evidence": 4,
    "missing-consumer-availability-row": 241,
    "missing-lifecycle-row": 241,
    "no-distribution-evidence": 237
  },
  "by_prefix": {
    "rules": 83,
    "scripts": 158
  },
  "total_unknown": 241
}
```

## Bucket meanings

| Bucket | Meaning | Default action |
|---|---|---|
| `conflicting-metadata` | Durable metadata disagrees. | Reconcile lifecycle/consumer metadata before marker changes. |
| `declared-both-needs-proof-and-metadata` | Marker says `both`, but distribution/proof evidence is absent or incomplete. | Add paired proof and lifecycle/consumer evidence, or demote after semantic review. |
| `declared-both-os-internal-heavy` | Marker says `both`, but content is dominated by SO-internal concepts. | Prioritize manual review for likely stale marker. |
| `missing-scope-marker` | Parser/classifier found no explicit marker and not enough evidence. | Add marker only after semantic review. |
| `project-only-semantic-candidate` | Text suggests downstream-project-only behavior. | Add project-only metadata/proof if confirmed. |
| `both-semantic-candidate` | Text looks repo-agnostic and generic. | Add portability proof and distribution metadata if confirmed. |
| `os-only-semantic-candidate` | Text looks SO-internal. | Add os-only lifecycle/consumer metadata if confirmed. |
| `insufficient-metadata` | No clear deterministic semantic direction. | Needs manual or AI-assisted adjudication. |

## insufficient-metadata (234)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `rules/RULES-COMPACT.md` | both | os=4; generic=8; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | COS Rules Index |
| `rules/adaptive-bypass.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Adaptive Bypass — Smart Orchestration |
| `rules/agent-audit-before-commit.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Audit Before Commit |
| `rules/agent-escalation.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Escalation Protocol |
| `rules/agent-identity.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Identity Protocol |
| `rules/agent-kpis.md` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent KPI Protocol |
| `rules/agent-output-reading.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Output Reading Protocol |
| `rules/agent-security.md` | both | os=1; generic=4; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Agent Security — Least Privilege Protocol |
| `rules/aguara-integration.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Aguara -- AI Agent Security Scanner |
| `rules/ai-provider-identity.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | AI Provider Identity Guard |
| `rules/anti-hallucination.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Anti-Hallucination Rule |
| `rules/assumption-tracking.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Assumption Tracking |
| `rules/audit-trail.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit Trail — Automated Work Tracking |
| `rules/auto-rollback.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Rollback Planning Protocol |
| `rules/auto-skill-generation.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Auto-Skill Generation Protocol |
| `rules/bash-naming.md` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Bash Script Naming — Kebab-Case Required |
| `rules/blast-radius.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Blast Radius Estimation |
| `rules/capability-levels.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Capability Levels — Auto-Disable Components |
| `rules/clarification-gate.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Mandatory Clarification Gate |
| `rules/closed-loop-prompts.md` | both | os=1; generic=6; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Closed-Loop Prompts — Self-Correcting Agent Execution |
| `rules/cognitive-load.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Cognitive Load Monitoring |
| `rules/confidence-gate.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Confidence Gate Protocol |
| `rules/confidentiality-protection.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Confidentiality Protection — IP Leak Prevention |
| `rules/consequence-system.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Consequence System — OKR-Driven Feedback Loop |
| `rules/content-policy.md` | both | os=1; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Content Policy — Automated Enforcement |
| `rules/context-management.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Context Window Management — Proactive Summarization Protocol |
| `rules/context-optimization.md` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Context Optimization Protocol |
| `rules/context7-auto-trigger.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Context7 Auto-Trigger — Library Documentation Lookup |
| `rules/cost-prediction.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Cost Prediction Protocol |
| `rules/crash-recovery.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Crash Recovery Protocol |
| `rules/credential-management.md` | both | os=0; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Credential Management |
| `rules/decision-depth-gate.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Decision Depth Gate |
| `rules/definition-of-done.md` | both | os=1; generic=7; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | enforcement: agent-instruction |
| `rules/doc-sync.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Doc Sync Rule |
| `rules/dry-run.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Dry-Run Preview Protocol |
| `rules/dynamic-tool-creation.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Dynamic Tool Creation -- Mid-Task Tool Generation |
| `rules/e2b-integration.md` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | E2B Sandbox -- Secure Agent Code Execution |
| `rules/engram-api-safety.md` | both | os=2; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Engram API Safety — Never Mutate Production Daemon for Discovery |
| `rules/engram-organization.md` | both | os=1; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Engram Organization — Path Segregation (BMAD v6 Pattern 8) |
| `rules/estimation-calibration.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Estimation Calibration Protocol |
| `rules/hcom-integration.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Hcom -- Cross-Terminal Agent Communication |
| `rules/license-policy.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | License Policy |
| `rules/llm-dispatch.md` | both | os=2; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | LLM Dispatch Policy (ADR-049 Option B) |
| `rules/memory-governance.md` | both | os=2; generic=2; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Memory Governance v2 — Typed Memory Policies |
| `rules/model-compatibility.md` | both | os=1; generic=3; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Model Compatibility — Baseline Expectations |
| `rules/model-directive.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Model Directive Protocol |
| `rules/non-blocking-retry.md` | both | os=1; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Non-Blocking Retry Protocol |
| `rules/observability.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Observability — MLflow Integration |
| `rules/orchestrator-mode.md` | both | os=0; generic=0; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Orchestrator Mode — Subprocess-Based Delegation |
| `rules/parry-integration.md` | both | os=1; generic=1; project=0 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Parry -- Prompt Injection Scanner |
| … | … | … | … | … | 184 more rows in JSON report. |

## conflicting-metadata (4)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `scripts/apply-efficiency-profile.sh` | os-only | os=3; generic=2; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | Apply Efficiency Profile — Delegates hook projection to per-harness settings drivers. |
| `scripts/cos-bootstrap.sh` | os-only | os=3; generic=0; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | ============================================================================= |
| `scripts/generate-project-settings.sh` | os-only | os=2; generic=3; project=0 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | generate-project-settings.sh — Generate harness-aware hook settings for external projects |
| `scripts/set-security-profile.sh` | os-only | os=2; generic=1; project=1 | missing-lifecycle-row, missing-consumer-availability-row, conflicting-distribution-evidence |  | Set Security Profile — Applies the selected security profile to Claude settings |

## project-only-semantic-candidate (2)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `scripts/cos-adapter-compile` | both | os=0; generic=0; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Compile COS primitive contracts into native consumer-project IDE files. |
| `scripts/documentation_truth_audit.py` | both | os=4; generic=1; project=2 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Audit volatile documentation claims against generated truth sources. |

## os-only-semantic-candidate (1)

| Path | Declared | Hints | Gaps | Structure | Summary |
|---|---|---|---|---|---|
| `scripts/cos-governed-edit.sh` | both | os=2; generic=0; project=1 | no-distribution-evidence, missing-lifecycle-row, missing-consumer-availability-row |  | Portable edit guard for harnesses without Edit/Write hook parity. |

