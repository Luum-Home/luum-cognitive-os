# Primitive Scope Classifier Iteration 7 — Declared `both` with OS-Internal-Heavy Content

## Input

```bash
.venv/bin/python scripts/primitive_scope_unknown_triage.py --project-dir .
```

Target bucket: `declared-both-os-internal-heavy` from the unknown triage report.

## Hypothesis

Rows in this bucket are declared `both`, but their content has strong Cognitive OS internal signals and lacks distribution metadata and paired portability proof. Many are likely stale `both` markers, but some may encode portable behavior behind COS-specific implementation.

## Summary after manual pass

| Category | Rows | Meaning |
|---|---:|---|
| `likely-os-only-marker-stale` | 80 | Current primitive appears to construct, validate, explain, or operate Cognitive OS itself. |
| `possible-both-portable-behavior-needs-proof` | 5 | Behavior is portable in principle, but current hook/script implementation needs adapter/projection proof. |
| `possible-both-portable-principle` | 2 | The principle is repo-agnostic, but the current artifact references COS-specific evidence or enforcement. |
| `possible-both-portable-wrapper` | 2 | Wrapper claims portable harness use but still needs consumer proof and metadata. |
| `possible-project-only` | 1 | Primitive appears to affect downstream projects only. |
| `split-or-os-only` | 2 | Current artifact is OS-specific; a generic extracted primitive could be both. |

## Row-level classification

| Path | Category | Hints | Manual rationale |
|---|---|---|---|
| `hooks/_lib/bypass-resolver.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/dispatch_gate_check.py` | `likely-os-only-marker-stale` | os=2; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/killswitch_check.sh` | `likely-os-only-marker-stale` | os=3; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/primitive-intervention.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/recap_adapter.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/safe-worktree-remove.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/task_panel_adapter.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/_lib/validation-lock.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/adr-detector.sh` | `likely-os-only-marker-stale` | os=3; generic=2; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/agent-bus-monitor.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/agent-output-verifier.sh` | `possible-both-portable-behavior-needs-proof` | os=2; generic=0; project=0 | Verifying claimed files exists is generic agent safety; current hook shape/logging is COS/Claude-specific. |
| `hooks/agent-quota-advisor.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/background-agent-reminder.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/clarification-interceptor.sh` | `possible-both-portable-behavior-needs-proof` | os=2; generic=1; project=0 | Clarification handling is generic agent quality behavior; current Agent-hook implementation is COS/Claude-specific. |
| `hooks/concurrent-write-guard-codex-proxy.sh` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/contextual-rule-loader.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/epic-task-detector.sh` | `possible-both-portable-behavior-needs-proof` | os=2; generic=1; project=0 | Detecting oversized tasks is generic repo-agent governance; current hook implementation needs projection proof. |
| `hooks/notify.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/resource-check.sh` | `possible-both-portable-behavior-needs-proof` | os=3; generic=1; project=0 | Resource budget checks can apply to any repo with agent orchestration; current budget sources are COS-specific. |
| `hooks/subagent-capability-preflight.sh` | `possible-both-portable-behavior-needs-proof` | os=2; generic=0; project=0 | Subagent launch preflight is generic agent safety; current artifact contract is COS-specific. |
| `hooks/task-panel-sync.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `hooks/task-recorder.sh` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `packages/skill-governance/skills/self-improve/SKILL.md` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/agent-communication.md` | `likely-os-only-marker-stale` | os=3; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/agent-customization.md` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/cosd-secure-api.md` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/engram-api-safety.md` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/infra-health.md` | `likely-os-only-marker-stale` | os=3; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/infra-intent.md` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/orchestrator-prompt-compose.md` | `likely-os-only-marker-stale` | os=3; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/queue-advisor.md` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/rate-limiting.md` | `likely-os-only-marker-stale` | os=4; generic=2; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/recommendation-grounding.md` | `possible-both-portable-principle` | os=3; generic=2; project=0 | Generic discipline for grounded recommendations, but current evidence cites COS operational paths. |
| `rules/skill-invocation-mandatory.md` | `likely-os-only-marker-stale` | os=3; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/startup-protocol.md` | `likely-os-only-marker-stale` | os=5; generic=2; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `rules/trust-score.md` | `possible-both-portable-principle` | os=2; generic=1; project=0 | Evidence/uncertainty reporting is repo-agnostic; implementation references COS parser/enforcer. |
| `scripts/backfill_cost_events.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/compose_agent_prompt.py` | `likely-os-only-marker-stale` | os=4; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-adr-implementation-audit.py` | `likely-os-only-marker-stale` | os=4; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-audit-archive` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-claims.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-doctor-concurrency.sh` | `likely-os-only-marker-stale` | os=4; generic=2; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-doctor-preserve.sh` | `likely-os-only-marker-stale` | os=4; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-engram-cloud-enroll` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-events.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-governed-agent.sh` | `possible-both-portable-wrapper` | os=3; generic=1; project=1 | Explicitly a portable launcher guard for harnesses without Agent hook parity; needs consumer proof despite COS internals. |
| `scripts/cos-governed-edit.sh` | `possible-both-portable-wrapper` | os=2; generic=0; project=1 | Explicitly a portable edit guard for harnesses without Edit/Write hook parity; needs consumer proof despite COS internals. |
| `scripts/cos-locks.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-opencode-primitive-adapter-smoke` | `likely-os-only-marker-stale` | os=5; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-portable-ai-consumer-smoke` | `likely-os-only-marker-stale` | os=2; generic=0; project=2 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-portable-ai-real-consumer-smoke` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-root` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-tui` | `likely-os-only-marker-stale` | os=2; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos-validation-capsule.sh` | `likely-os-only-marker-stale` | os=3; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_claim_signature_audit.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_coverage.py` | `likely-os-only-marker-stale` | os=3; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_cross_instance_drill.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_demotion_loop_audit.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_doctrine_proposer.py` | `likely-os-only-marker-stale` | os=3; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_governance_roi.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_manifest_tier_claim_audit.py` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_self_improvement_loop.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/cos_test_quality_audit.py` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/derived_artifact_gate.py` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/lab_first_promotion_gate.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/opencode_primitive_adapter_smoke.py` | `likely-os-only-marker-stale` | os=5; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/orchestrator_claim_gate.py` | `likely-os-only-marker-stale` | os=2; generic=1; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/orphan_commit_scan.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/parity_harness.py` | `likely-os-only-marker-stale` | os=3; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/portable_ai_consumer_impact.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=2 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/portable_ai_consumer_smoke.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=2 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/portable_ai_real_consumer_smoke.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/primitive_authority_audit.py` | `likely-os-only-marker-stale` | os=5; generic=1; project=2 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/primitive_fitness_ledger.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/runtime_hook_reality.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/smoke-agent-quota-advisor.sh` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/so-reaper.sh` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/so-vitals.sh` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/startup-benchmark.sh` | `likely-os-only-marker-stale` | os=3; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/statusline-coverage.sh` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `scripts/verify_plan_claims.py` | `likely-os-only-marker-stale` | os=2; generic=0; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/add-hook/SKILL.md` | `split-or-os-only` | os=2; generic=1; project=2 | Current procedure is for adding hooks to Cognitive OS. Generic hook-authoring could be both, but this body is OS-specific. |
| `skills/add-skill/SKILL.md` | `split-or-os-only` | os=3; generic=2; project=2 | Current procedure is for adding skills to Cognitive OS. Generic skill-authoring could be both, but this body is OS-specific. |
| `skills/cos-status/SKILL.md` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/decision-triage/SKILL.md` | `likely-os-only-marker-stale` | os=4; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/detect-stack/SKILL.md` | `possible-project-only` | os=2; generic=1; project=1 | Scans a project root and writes detected stack for generated project config; SO self-construction likely does not require it. |
| `skills/llm-status/SKILL.md` | `likely-os-only-marker-stale` | os=5; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/peer-card/SKILL.md` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/phoenix-trace-ui/SKILL.md` | `likely-os-only-marker-stale` | os=2; generic=0; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/session-backlog/SKILL.md` | `likely-os-only-marker-stale` | os=2; generic=1; project=2 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/session-manager/SKILL.md` | `likely-os-only-marker-stale` | os=2; generic=1; project=0 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |
| `skills/session-wrapup/SKILL.md` | `likely-os-only-marker-stale` | os=5; generic=2; project=1 | Core value depends on COS/ADR/manifests/hooks/metrics internals and no distribution evidence or paired proof exists. |

## Decision

Do not mass-edit markers from this pass. The bucket is now prioritized as:

1. Candidate marker fixes: `likely-os-only-marker-stale` rows after spot-checking family-level metadata.
2. Candidate extraction/split: `split-or-os-only` rows where a generic reusable procedure may be separated from the COS-specific procedure.
3. Candidate proof additions: possible `both` rows where the behavior is portable but lacks consumer projection proof.
4. Candidate project-only proof: `skills/detect-stack/SKILL.md`.

## Next actions

- Add lifecycle/consumer metadata for rows confirmed `os-only` rather than editing only headers.
- For possible `both` rows, add paired portability/falsification proof before trusting the marker.
- For split candidates, keep current body `os-only` unless/until a generic extracted primitive exists.

