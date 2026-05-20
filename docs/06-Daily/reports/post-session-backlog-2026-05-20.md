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


**Dogfooding wins:** four of the ten commits above
(`16eba828`, `40762666`, `3ce016d2`, `2930a125`) closed structural bugs
in the dispatch/queue/validation primitives themselves — the SO caught
its own gaps. Postmortem at
`docs/06-Daily/reports/dispatch-gate-empty-prompt-ghost-lock-postmortem-2026-05-20.md`.

## Outstanding work, ranked by ROI

| # | Item | Effort | Why it matters | Source |
|---|---|---|---|---|
| 1 | DX Tax 5 items left unchecked in op-stability plan | 2-4h each (=10-20h) | Real implementation: lean-profile semantics, hygiene-vs-blocker, merge-queue lane recording, default-core install boundary, merge-queue default path. Closes Phase 6/7 of `operational-stability-friction-reduction.md`. | `.cognitive-os/plans/architecture/operational-stability-friction-reduction.md` |
| 2 | Maintainer Telemetry Phase 5 — impact measurement | 1 slice | Phase 2 emits skill/provider/primitive rollups. Phase 5 measures whether rollups change operator decisions. | engram topic `maintainer-telemetry-phases` |
| 3 | Governance catch-ledger population policy | 1 slice | ADR-328 adds `.cognitive-os/metrics/governance-catches.jsonl` and `cos status` exposure. Next ROI work is deciding when/how operator-reviewed catch verdicts are recorded so the ratio stops reporting `unknown`. | `docs/02-Decisions/adrs/ADR-328-governance-roi-friction-vs-catch.md` |
| 4 | Op Stability Phase 3 — adaptive profiles resolver | multi-sesión | `lean|standard|strict` profile picker per phase + per surface. | op-stability plan §Phase 3 |
| 5 | Op Stability Phase 7 — distribution boundary metadata | multi-sesión | Every projected primitive has distribution metadata; maintainer/lab off default runtime path. | op-stability plan §Phase 7 |
| 6 | Op Stability Phase 8 — productization threshold | multi-sesión | 6 exit-criteria checkboxes (status accuracy, false-positive trend, merge-queue default, chaos N=10/20/50, etc.). Mostly verified this session — outstanding: hygiene-vs-blocker, merge-queue default path. | op-stability plan §Phase 8 |
| 7 | Wave 5 backlog: ADR-121 phases 3-6, ADR-291 23 endpoints, ADR-325 phases 3-5 | multi-sesión by design | Structural backlog. Each is its own arc. | post-audit-cleanup-roadmap.md |

## Items intentionally NOT prioritized

- **Long-tail dormant manifest hygiene (40 items)** — ratio at 20.3% (below 25% target). Further candidate→state flips are bookkeeping, not strategic pressure. Defer until a re-audit shows the ratio creeping back up.
- **45 KEEP-CANDIDATE wiring slice** — same reasoning. The KEEP decisions are operator-confirmed; wiring is a separate ROI question.

## Operational risks to track

| Risk | Trigger | Mitigation |
|---|---|---|
| Governance catch ledger under-populated | ADR-328 now exposes friction-vs-catch in `cos status`, but the ratio is intentionally `unknown` until reviewed catch rows exist. Without a capture policy, the dashboard can still drift into "metric exists, evidence missing". | Define when operators or hooks append `confirmed_valid_block`, `false_positive_override`, `silent_loss_prevented`, and `high_blast_radius_catch` rows to `.cognitive-os/metrics/governance-catches.jsonl`. |
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

1. **Slice X**: DX Tax item #1 cheapest first — lean-profile semantics
   (self-contained, ~3h, closes a Phase 6 checkbox).
2. **Slice Z**: Maintainer Telemetry Phase 5 — decide whether rollups changed
   operator choices, not just whether rollups exist.
3. **Slice W**: Governance catch-ledger population policy — make ADR-328's
   friction-vs-catch ratio actionable by recording reviewed verdicts.

ADR-038 Wave 4 was the originally proposed Slice Y and is now closed in the
continuation slice. Governance ROI measurement also moved from open risk to
implemented substrate; what remains is evidence population, not the status
surface itself.
