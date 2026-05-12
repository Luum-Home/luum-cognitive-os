# Agent Training Harness Gap Audit — 2026-05-12

## Purpose

Audit the new Agent Training Harness doctrine after documenting the canonical contract in `docs/architecture/agent-training-harness.md`.

The audit checks whether COS can currently claim a complete agent-training harness, where "training" means operational learning over telemetry, memory, evals, and governed updates to agentic primitives — not provider-weight fine-tuning.

## Inputs

- `docs/architecture/agent-training-harness.md`
- `manifests/agent-training-harness.yaml`
- `manifests/primitive-lifecycle.yaml`
- `docs/reports/primitive-harness-coverage-latest.json`
- `docs/reports/primitive-readiness-ledger-hooks-latest.json`
- `docs/reports/primitive-readiness-ledger-skills-latest.json`
- `docs/reports/primitive-readiness-ledger-rules-latest.json`
- `docs/reports/capability-coverage-latest.json`
- `docs/reports/feature-tool-due-diligence-latest.json`

## Findings

| ID | Severity | Finding | Evidence | Required action |
|---|---:|---|---|---|
| ATH-001 | High | The doctrine existed in fragments but had no canonical training contract before this work. | Prior references were spread across `docs/overview.md`, `docs/architecture.md`, `docs/self-improvement-loop.md`, `skills/agent-kpis/SKILL.md`, and eval research docs. | Added `docs/architecture/agent-training-harness.md` and backlinks. |
| ATH-002 | High | Training claims need a machine-readable source of truth. | No existing manifest described trainable surfaces, signal sources, non-goals, or claim policy. | Added `manifests/agent-training-harness.yaml`. |
| ATH-003 | Medium | Future wording can drift toward false provider-weight training claims. | Existing docs use terms such as training, RL, and fine-tuning in several contexts. | Added an audit test that gates operational training claims to the canonical doc or manifest. |
| ATH-004 | Medium | Prioritized self-improvement primitives were not all lifecycle-declared. | `skills/self-improve/SKILL.md`, `skills/agent-kpis/SKILL.md`, and `rules/self-improvement-protocol.md` were missing from `manifests/primitive-lifecycle.yaml`; the three prioritized hooks already had entries. | Added lifecycle metadata for the two skills and one rule; verified hook entries remain present. |
| ATH-005 | Medium | Cross-harness support remains incomplete. | `docs/reports/primitive-harness-coverage-latest.json` reports 869 gaps across 1046 primitives. | Keep claims scoped per harness and do not claim equal runtime enforcement across all projected harnesses. |
| ATH-006 | Medium | Many primitives still lack lifecycle metadata outside the prioritized set. | Readiness ledgers report missing lifecycle metadata for 107 hooks, 99 skills, and 120 rules before this targeted patch. | Treat this as broader primitive-readiness backlog; this patch closes only the requested training-critical set. |
| ATH-007 | Medium | Eval training signals are not yet reproducible enough. | Research docs propose judge isolation and per-eval-run manifests, but no active `manifests/eval-run-schema.yaml` or run manifest emission is present. | Keep eval-run manifest and judge-isolation enforcement as open gaps in `manifests/agent-training-harness.yaml`. |
| ATH-008 | Low | Feature-to-external-tool due diligence remains incomplete for adjacent capabilities. | `docs/reports/feature-tool-due-diligence-latest.json` reports 19 warnings. | Avoid public BUILD claims for warned capabilities until due-diligence records exist. |

## Closure performed in this patch

1. Created the canonical contract: `docs/architecture/agent-training-harness.md`.
2. Created the machine-readable manifest: `manifests/agent-training-harness.yaml`.
3. Added an audit test: `tests/audit/test_agent_training_harness_claims.py`.
4. Added lifecycle metadata for:
   - `skills/self-improve/SKILL.md`
   - `skills/agent-kpis/SKILL.md`
   - `rules/self-improvement-protocol.md`
5. Verified existing lifecycle entries for:
   - `hooks/error-learning.sh`
   - `hooks/session-learning.sh`
   - `hooks/kpi-trigger.sh`

## Residual backlog

The request was to avoid leaving the listed next steps pending. Those are closed by this patch. The following are larger known product gaps and remain explicitly tracked rather than hidden:

- implement `manifests/eval-run-schema.yaml`;
- wire eval skills to emit content-addressed `runs/<run_id>/manifest.json` artifacts;
- enforce SUT != judge by default for eval skills;
- continue lifecycle metadata coverage beyond the training-critical primitives;
- reduce the wider primitive harness coverage gap count.

## Acceptance criteria

1. `docs/architecture/agent-training-harness.md` exists and defines training as operational learning, not provider-weight fine-tuning.
2. `manifests/agent-training-harness.yaml` exists and names non-goals, signal sources, claim policy, validation, and open gaps.
3. `tests/audit/test_agent_training_harness_claims.py` passes.
4. `manifests/primitive-lifecycle.yaml` contains lifecycle entries for the six prioritized primitives.
5. Targeted tests pass:
   - `python3 -m pytest tests/audit/test_agent_training_harness_claims.py -q`
   - `python3 -m pytest tests/contracts/test_primitive_runtime_reality.py -q`
