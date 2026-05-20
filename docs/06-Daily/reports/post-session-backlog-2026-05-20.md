# Post-Session Backlog — 2026-05-20

> Consolidated view of pending work after the 2026-05-18/20 multi-wave
> cleanup arc. Supersedes the snapshot fragments in:
>
> - `.cognitive-os/plans/roadmaps/post-audit-cleanup-roadmap.md` (8-wave
>   original; several items closed)
> - `docs/06-Daily/reports/parallel-session-backlog-2026-05-18.md` (S1-S30
>   briefs; many redundant or completed)
> - `docs/06-Daily/reports/session-2026-05-18-multi-wave.md` (historical
>   snapshot, not regenerated)
>
> This file is a manual snapshot. Regenerating it automatically is itself
> the next ADR-territory question — see §Open Architectural Question.

## Metrics measured 2026-05-20

| Metric | Value | Target | Status |
|---|---|---|---|
| dormant+aspirational ratio | 20.3% | ≤25% | ✓ below |
| lifecycle candidate footprint | 94/919 (10.2%) | downward trend | ✓ from 137 at session start |
| component classification | REAL 318 / DORMANT 176 / ASPIRATIONAL 69 | — | — |
| lifecycle audit tests | 52/52 pass | all green | ✓ |
| docs-truth claims | tracked in manifests/documentation-truth-claims.yaml | per ADR-277 | — |

## What this session closed

Commits since 2026-05-19 (HEAD: `50ffba60`):

| Commit | Subject | Class |
|---|---|---|
| `50ffba60` | Slice A residual — 10 candidate transitions | lifecycle |
| `0c2f18ba` | ADR-038 Wave 3 — Pydantic TrustReport schema + parser | structural |
| `2930a125` | post-Bash drain tick surfaces ready queued agents | dispatch-fix |
| `6e4f8f71` | eliminate expected-failure debt | audit |
| `a851c8dc` | refresh AI-overlay lifecycle metadata | lifecycle |
| `3ce016d2` | repair Bash JSON-default corruption + wire MAX_PARALLEL env | dispatch-fix |
| `40762666` | collapse ghost validation-capsule detection paths | dispatch-fix |
| `16eba828` | reject empty Agent prompts at enqueue + drain | dispatch-fix |
| `d5805294` | apply Batch A+B+E lifecycle promotions — 43 items | lifecycle |
| `e3029d5d` | mark 9 verified op-stability acceptance items | docs |

Plus earlier in the arc (pre-2026-05-19): telemetry Phase 2 rollups,
ADR-038 Wave 2 input schema validator, hook maturity Phase 2 closure,
session report + parallel backlog.

Continuation after this backlog snapshot:

| Change | Status | Evidence |
|---|---|---|
| ADR-038 Wave 4 hook wiring + grading policy | DONE in local continuation slice | `templates/agent-planning.md`, `lib/prompt_builder.py`, `hooks/trust-score-validator.sh`, `hooks/task-completed.sh`, `cognitive-os.yaml`, `tests/hooks/test_trust_score_validator.py`, `tests/unit/test_prompt_integration.py` |
| Governance ROI friction-vs-catch surface | DONE in local continuation slice | `docs/02-Decisions/adrs/ADR-328-governance-roi-friction-vs-catch.md`, `scripts/cos_governance_roi.py`, `scripts/cos-status.sh`, `tests/unit/test_cos_governance_roi.py`, `tests/behavior/test_cos_status.py` |
| Governance catch-ledger population workflow | DONE in local continuation slice | `scripts/cos_governance_roi.py`, `scripts/cos`, `scripts/hook-timing-wrapper.sh`, `tests/unit/test_cos_governance_roi.py`, `tests/contracts/test_hook_timing_wrapper.py` |
| DX Tax lean-profile semantics | DONE in local continuation slice | `lib/adaptive_profile.py`, `scripts/cos_profile_explain.py`, `tests/unit/test_profile_resolver.py`, `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` |
| Maintainer Telemetry Phase 5 impact measurement | DONE in local continuation slice | `lib/maintainer_impact.py`, `scripts/cos-maintainer-impact`, `tests/unit/test_maintainer_impact.py`, `docs/02-Decisions/adrs/ADR-201-maintainer-agent-telemetry-promotion-loop.md` |


**Dogfooding wins:** four of the ten commits above
(`16eba828`, `40762666`, `3ce016d2`, `2930a125`) closed structural bugs
in the dispatch/queue/validation primitives themselves — the SO caught
its own gaps. Postmortem at
`docs/06-Daily/reports/dispatch-gate-empty-prompt-ghost-lock-postmortem-2026-05-20.md`.

## Outstanding work, ranked by ROI

| # | Item | Effort | Why it matters | Source |
|---|---|---|---|---|
| 1 | DX Tax remaining unchecked items | 2-4h each | Lean-profile semantics is closed. Remaining real implementation is hygiene-vs-blocker, merge-queue lane recording, default-core install boundary, and merge-queue default path. | `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` |
| 2 | Governance phase-policy enforcement adoption | multi-slice | ADR-328 now has the catch ledger, operator prompt workflow, weighted ratio, and `cos governance policy`; next work is wiring individual guards to consult the policy adapter consistently. | `docs/02-Decisions/adrs/ADR-328-governance-roi-friction-vs-catch.md` |
| 3 | Op Stability Phase 3 — adaptive profiles resolver | multi-sesión | `lean|standard|strict` profile picker per phase + per surface. | op-stability plan §Phase 3 |
| 4 | Op Stability Phase 7 — distribution boundary metadata | multi-sesión | Every projected primitive has distribution metadata; maintainer/lab off default runtime path. | op-stability plan §Phase 7 |
| 5 | Op Stability Phase 8 — productization threshold | multi-sesión | 6 exit-criteria checkboxes (status accuracy, false-positive trend, merge-queue default, chaos N=10/20/50, etc.). Mostly verified this session — outstanding: hygiene-vs-blocker, merge-queue default path. | op-stability plan §Phase 8 |
| 6 | Wave 5 backlog: ADR-121 phases 3-6, ADR-291 23 endpoints, ADR-325 phases 3-5 | multi-sesión by design | Structural backlog. Each is its own arc. | post-audit-cleanup-roadmap.md |

## Items intentionally NOT prioritized

- **Long-tail dormant manifest hygiene (40 items)** — ratio at 20.3% (below 25% target). Further candidate→state flips are bookkeeping, not strategic pressure. Defer until a re-audit shows the ratio creeping back up.
- **45 KEEP-CANDIDATE wiring slice** — same reasoning. The KEEP decisions are operator-confirmed; wiring is a separate ROI question.

## Operational risks to track

| Risk | Trigger | Mitigation |
|---|---|---|
| Governance catch ledger evidence still sparse | ADR-328 now has `cos governance catch log`, `cos governance catch pending`, and blocked-hook prompts, but historical rows remain sparse until operators classify real events. | Use the new pending prompt workflow during dogfooding; treat missing evidence as adoption debt, not missing substrate. |
| Per-guard policy adoption incomplete | `cos governance policy` can answer phase-aware block/advisory decisions, but individual guards still need incremental wiring where they currently hard-code posture. | Adopt the policy adapter guard-by-guard, starting with high-friction blocker paths. |
| Backlog state regeneration manual | This doc is a manual snapshot. Within 1-2 sessions it will drift. | See open architectural question below. |
| Trust-report legacy migration debt | Wave 4 resolved the ambiguity: structured malformed reports block, missing reports remain advisory outside production/maintenance, and legacy `TRUST REPORT:` blocks are accepted with a warning plus `format=legacy` metrics. | Track legacy count in `.cognitive-os/metrics/trust-scores.jsonl`; remove fallback only after legacy usage approaches zero. |

## Open architectural question

**Should `cos-session-state` be a runtime primitive?**

Today: pending work lives across `.cognitive-os/plans/`, engram observations,
git log, manifests, audit reports. The session-start projector (ADR-275)
aggregates several of these for read-time projection, but there is no
write-time consolidator that owns "what's the current backlog after the
last session". This document fills that gap by hand.

Candidates:
- Extend the ADR-275 projector with a `--backlog` mode that ranks open work
  by ROI heuristics (effort × strategic-pressure × blast-radius).
- Add a `session-wrapup` skill output that updates a canonical
  `docs/06-Daily/reports/current-backlog.md` on every wrapup.
- Accept manual snapshots as the design and document the cadence
  (e.g. weekly post-session backlog refresh).

Decision deferred to a future session. ADR-031 + ADR-025 + ADR-059 are
the closest existing decisions but none commit to a canonical
"current pending state" primitive.

## Next-session proposal

1. **DX Tax follow-on**: hygiene-vs-blocker semantics, then merge-queue lane/default-path work.
2. **Governance policy adoption**: wire high-friction guards to `cos governance policy` so reconstruction/production posture is enforced consistently.
3. **Telemetry adoption**: use `scripts/cos-maintainer-impact` for real maintainer choices so Phase 5 has evidence, not only instrumentation.

ADR-038 Wave 4, lean-profile semantics, Maintainer Telemetry Phase 5 instrumentation, and ADR-328 catch-ledger population substrate are now closed in continuation slices. Remaining work is adoption/wiring, not the core substrate.
